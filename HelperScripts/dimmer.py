"""
Core dimmer logic and monitoring loop
"""
import time
import threading
import win32gui
import traceback
from .config import THRESHOLD_START, THRESHOLD_MAX, MAX_OPACITY, CHECK_INTERVAL, DEBUG_LOGGING
from .brightness import BrightnessMeasurer
from .overlay import OverlayManager
from .logger import Logger


class AdaptiveDimmer:
    """Main dimmer class that monitors and adjusts screen brightness"""
    
    def __init__(self, gui=None):
        self.gui = gui
        self.running = True
        self.paused = False
        self.active_monitors = []
        self.monitor_lock = threading.Lock()
        
        # Initialize components
        self.logger = Logger()
        self.logger.open_log_file()
        self.overlay_manager = OverlayManager(self.logger)
        self.brightness_measurer = BrightnessMeasurer()
        
        # Expose overlay manager attributes for backward compatibility
        self.hwnds = self.overlay_manager.hwnds
        self.current_opacity = self.overlay_manager.current_opacity
        self.target_opacity = self.overlay_manager.target_opacity
        self.switching_monitor = False
        
        # Track overlay creation time to avoid feedback loop
        self.overlay_creation_time = {}
    
    def log(self, message):
        """Console log"""
        self.logger.log(message)
    
    def write_shutdown_log(self, message):
        """Write shutdown debug log"""
        self.logger.write_shutdown_log(message)
    
    def create_overlay(self, monitor_id):
        """Create overlay for monitor"""
        self.overlay_manager.create_overlay(monitor_id)
        # Track when this overlay was created
        self.overlay_creation_time[monitor_id] = time.time()
    
    def set_overlay_opacity(self, monitor_id, opacity, force_immediate=False):
        """Set overlay opacity"""
        self.overlay_manager.set_overlay_opacity(monitor_id, opacity, force_immediate)
    
    def measure_brightness(self, monitor_id, hide_overlay=False):
        """Measure brightness for monitor"""
        return self.brightness_measurer.measure_brightness(monitor_id)
    
    def calculate_target_opacity(self, raw_estimate, strength):
        """
        Calculate target opacity based on brightness and strength
        
        Args:
            raw_estimate: Raw brightness estimate
            strength: Dim strength factor (0.0 - 1.0)
            
        Returns:
            int: Target opacity value (0-255)
        """
        if raw_estimate > THRESHOLD_MAX:
            return MAX_OPACITY * strength
        elif raw_estimate > THRESHOLD_START:
            ratio = (raw_estimate - THRESHOLD_START) / (THRESHOLD_MAX - THRESHOLD_START)
            return ratio * MAX_OPACITY * strength
        else:
            return 0
    
    def monitor_loop(self):
        """Main loop for brightness monitoring"""
        last_log_time = time.time()
        last_console_log_time = time.time()
        
        try:
            while self.running:
                if self.paused:
                    time.sleep(CHECK_INTERVAL)
                    continue
                
                # Avoid race while switching monitor overlays
                if self.switching_monitor:
                    if DEBUG_LOGGING:
                        self.log("DEBUG monitor_loop: switching_monitor active - waiting")
                    time.sleep(0.1)
                    continue
                
                with self.monitor_lock:
                    if not self.running:
                        break
                    
                    # Create safe copy of active monitors
                    active_monitors_copy = list(self.active_monitors)
                    
                    if DEBUG_LOGGING:
                        self.log(f"DEBUG monitor_loop: active_monitors={active_monitors_copy}")
                    log_entries = []
                    console_log_entries = []
                    
                    for monitor_id in active_monitors_copy:
                        # Skip if monitor overlay doesn't exist or is invalid
                        hwnd = self.hwnds.get(monitor_id)
                        if not hwnd:
                            if DEBUG_LOGGING:
                                self.log(f"DEBUG: Skipping monitor {monitor_id} - no valid hwnd")
                            continue
                        
                        try:
                            # Measure brightness (raw screen capture)
                            measured = self.measure_brightness(monitor_id)
                            
                            # Use measured brightness directly - NO COMPENSATION
                            # This prevents feedback loops and instability
                            raw_estimate = measured
                            
                            # Clamp to reasonable range
                            raw_estimate = max(0, min(255, raw_estimate))
                            
                            # Calculate target opacity based on measured brightness
                            strength = max(0.0, min(1.0, self.gui.dim_strength.get() / 100.0)) if self.gui else 1.0
                            new_target = self.calculate_target_opacity(raw_estimate, strength)
                            
                            # Store new target
                            self.target_opacity[monitor_id] = new_target
                            
                            # Apply opacity with smooth interpolation
                            self.set_overlay_opacity(monitor_id, new_target)
                            
                            # Get current opacity for display
                            current_alpha = self.current_opacity.get(monitor_id, 0)
                            
                            # Calculate dimmed brightness for display
                            dimmed_brightness = raw_estimate * (1 - current_alpha / 255.0)
                            
                            # Send to GUI
                            if self.gui:
                                self.gui.push_brightness(monitor_id, raw_estimate, dimmed_brightness)
                            
                            log_entries.append((monitor_id, raw_estimate, current_alpha, dimmed_brightness))
                            console_log_entries.append((monitor_id, measured, raw_estimate, current_alpha, new_target))
                        except Exception as e:
                            self.log(f"ERROR processing monitor {monitor_id}: {e}")
                            traceback.print_exc()
                    
                    # Console log every 2 seconds for debugging
                    if time.time() - last_console_log_time >= 2.0:
                        for mid, meas, raw, curr_a, targ_a in console_log_entries:
                            self.log(f"Mon{mid}: Meas={meas:.1f} Raw={raw:.1f} CurrAlpha={curr_a:.1f} TargetAlpha={targ_a:.1f}")
                        last_console_log_time = time.time()
                    
                    # Log to file every second
                    if time.time() - last_log_time >= 1.0:
                        self.logger.log_brightness_data(log_entries)
                        last_log_time = time.time()
                
                time.sleep(CHECK_INTERVAL)
        
        except KeyboardInterrupt:
            self.log("\nProgramm wird beendet...")
            self.running = False
        except Exception as e:
            self.log(f"ERROR monitor_loop: {e}")
            traceback.print_exc()
            self.running = False
    
    def run(self):
        """Starts the dimmer"""
        self.write_shutdown_log("=== AdaptiveDimmer.run() STARTED ===")
        self.log("=" * 50)
        self.log("ADAPTIVE SCREEN DIMMING v2 - GUI")
        self.log("=" * 50)
        self.log(f"Abdunkelung ab: {THRESHOLD_START}")
        self.log(f"Maximum bei: {THRESHOLD_MAX}")
        self.log(f"Max. Abdunkelung: {MAX_OPACITY}/255")
        self.log(f"Check Interval: {CHECK_INTERVAL}s")
        self.log(f"Aktive Bildschirme: {self.active_monitors}")
        self.log("")
        
        # Create overlays
        for monitor_id in self.active_monitors:
            self.create_overlay(monitor_id)

        # Start monitoring thread
        monitor_thread = threading.Thread(target=self.monitor_loop, daemon=True)
        monitor_thread.start()

        try:
            while self.running:
                win32gui.PumpWaitingMessages()
                time.sleep(0.01)
        except KeyboardInterrupt:
            self.write_shutdown_log("KeyboardInterrupt received")
            self.log("\nProgramm wird beendet...")
            self.running = False
            for hwnd in self.hwnds.values():
                if hwnd:
                    win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
        except Exception as e:
            self.write_shutdown_log(f"Exception in run loop: {e}")
            self.log(f"\nFEHLER: {e}")
            traceback.print_exc()
            self.running = False
        finally:
            self.write_shutdown_log("run() finally block - joining monitor thread")
            monitor_thread.join(timeout=1)
            self.write_shutdown_log("run() finally block - destroying overlays")
            self.overlay_manager.destroy_all_overlays()
            self.log("? Overlay geschlossen")
            self.write_shutdown_log("=== AdaptiveDimmer.run() ENDED CLEANLY ===")
