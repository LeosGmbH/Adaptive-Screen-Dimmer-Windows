"""
Core dimmer logic and monitoring loop
"""
import time
import threading
import win32gui
import traceback
from .config import THRESHOLD_START, THRESHOLD_MAX, MAX_OPACITY, CHECK_INTERVAL
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
    
    def log(self, message):
        """Console log"""
        self.logger.log(message)
    
    def write_shutdown_log(self, message):
        """Write shutdown debug log"""
        self.logger.write_shutdown_log(message)
    
    def create_overlay(self, monitor_id):
        """Create overlay for monitor"""
        self.overlay_manager.create_overlay(monitor_id)
    
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
        try:
            while self.running:
                if self.paused:
                    time.sleep(CHECK_INTERVAL)
                    continue
                
                # Avoid race while switching monitor overlays
                if self.switching_monitor:
                    self.log("DEBUG monitor_loop: switching_monitor active - waiting 50ms")
                    time.sleep(0.05)
                    continue
                
                with self.monitor_lock:
                    if not self.running:
                        break
                    
                    self.log(f"DEBUG monitor_loop: active_monitors={self.active_monitors}")
                    log_entries = []
                    
                    for monitor_id in self.active_monitors:
                        # Measure brightness
                        measured = self.measure_brightness(monitor_id)
                        
                        # Calculate raw estimate
                        alpha_before = self.current_opacity.get(monitor_id, 0)
                        raw_estimate = self.brightness_measurer.calculate_raw_estimate(measured, alpha_before)
                        
                        # Calculate target opacity
                        strength = max(0.0, min(1.0, self.gui.dim_strength.get() / 100.0)) if self.gui else 1.0
                        self.target_opacity[monitor_id] = self.calculate_target_opacity(raw_estimate, strength)
                        
                        # Apply opacity
                        self.set_overlay_opacity(monitor_id, self.target_opacity[monitor_id])
                        
                        # Calculate dimmed brightness for logging
                        current_alpha = self.current_opacity.get(monitor_id, 0)
                        dimmed_brightness = self.brightness_measurer.calculate_dimmed_brightness(raw_estimate, current_alpha)
                        
                        # Send to GUI
                        if self.gui:
                            self.gui.push_brightness(monitor_id, raw_estimate, dimmed_brightness)
                        
                        log_entries.append((monitor_id, raw_estimate, current_alpha, dimmed_brightness))
                    
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
