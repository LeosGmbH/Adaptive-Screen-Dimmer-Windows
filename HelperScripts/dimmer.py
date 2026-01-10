"""
Core dimmer logic and monitoring loop
"""
import time
import threading
import traceback
from .config import THRESHOLD_START, THRESHOLD_MAX, MAX_OPACITY, CHECK_INTERVAL, DEBUG_LOGGING
from .brightness import BrightnessMeasurer
from .process_overlay import ProcessOverlayManager
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
        self.overlay_manager = ProcessOverlayManager(self.logger)
        self.brightness_measurer = BrightnessMeasurer()
        
        # Expose overlay manager attributes for backward compatibility
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
        return self.overlay_manager.create_overlay(monitor_id)
    
    def set_overlay_opacity(self, monitor_id, opacity, force_immediate=False):
        """Set overlay opacity"""
        return self.overlay_manager.set_overlay_opacity(monitor_id, opacity, force_immediate)
    
    def measure_brightness(self, monitor_id):
        """Measure brightness for monitor"""
        return self.brightness_measurer.measure_brightness(monitor_id)
    
    def calculate_target_opacity(self, raw_estimate, strength):
        """Calculate target opacity based on brightness and strength"""
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
                        # Check if overlay process is running
                        if not self.overlay_manager.is_overlay_running(monitor_id):
                            if DEBUG_LOGGING:
                                self.log(f"DEBUG: Monitor {monitor_id} overlay not running, skipping")
                            continue
                        
                        try:
                            # Measure brightness
                            measured = self.measure_brightness(monitor_id)
                            raw_estimate = max(0, min(255, measured))
                            
                            # Calculate target opacity
                            strength = max(0.0, min(1.0, self.gui.dim_strength.get() / 100.0)) if self.gui else 1.0
                            new_target = self.calculate_target_opacity(raw_estimate, strength)
                            
                            # Store and apply target
                            self.target_opacity[monitor_id] = new_target
                            success = self.set_overlay_opacity(monitor_id, new_target)
                            
                            if not success and DEBUG_LOGGING:
                                self.log(f"Monitor {monitor_id}: Failed to set opacity")
                            
                            # Get current opacity for display
                            current_alpha = self.current_opacity.get(monitor_id, 0)
                            dimmed_brightness = raw_estimate * (1 - current_alpha / 255.0)
                            
                            # Send to GUI
                            if self.gui:
                                self.gui.push_brightness(monitor_id, raw_estimate, dimmed_brightness)
                            
                            log_entries.append((monitor_id, raw_estimate, current_alpha, dimmed_brightness))
                            console_log_entries.append((monitor_id, measured, raw_estimate, current_alpha, new_target))
                        
                        except Exception as e:
                            self.log(f"ERROR processing monitor {monitor_id}: {e}")
                            traceback.print_exc()
                    
                    # Console log every 2 seconds
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
        self.log("ADAPTIVE SCREEN DIMMING v2 - PROCESS MODE")
        self.log("=" * 50)
        self.log(f"Abdunkelung ab: {THRESHOLD_START}")
        self.log(f"Maximum bei: {THRESHOLD_MAX}")
        self.log(f"Max. Abdunkelung: {MAX_OPACITY}/255")
        self.log(f"Check Interval: {CHECK_INTERVAL}s")
        self.log(f"Aktive Bildschirme: {self.active_monitors}")
        self.log("")
        
        # Create overlay processes
        for monitor_id in self.active_monitors:
            self.create_overlay(monitor_id)

        # Start monitoring thread
        monitor_thread = threading.Thread(target=self.monitor_loop, daemon=True)
        monitor_thread.start()

        try:
            # Just wait - no window message pumping needed
            monitor_thread.join()
        except KeyboardInterrupt:
            self.write_shutdown_log("KeyboardInterrupt received")
            self.log("\nProgramm wird beendet...")
            self.running = False
        finally:
            self.write_shutdown_log("run() finally block - destroying overlays")
            self.overlay_manager.destroy_all_overlays()
            self.log("? Overlay processes terminated")
            self.write_shutdown_log("=== AdaptiveDimmer.run() ENDED CLEANLY ===")
