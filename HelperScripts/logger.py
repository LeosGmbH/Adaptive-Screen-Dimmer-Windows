"""
Logging utilities for Adaptive Screen Dimmer
"""
import os
from datetime import datetime


class Logger:
    """Handles console and file logging"""
    
    def __init__(self):
        self.log_path = os.path.join(os.getcwd(), "dimmer_log.txt")
        self.shutdown_log_path = os.path.join(os.getcwd(), "shutdown_log.txt")
        self.log_file = None
        
    def open_log_file(self):
        """Open the brightness log file"""
        try:
            self.log_file = open(self.log_path, "w", encoding="utf-8")
            self.log_file.write("timestamp,monitor,raw_brightness,opacity,dimmed_brightness\n")
            self.log_file.flush()
        except Exception as e:
            self.log(f"WARNING: Konnte Log-Datei nicht oeffnen: {e}")
    
    def close_log_file(self):
        """Close the brightness log file"""
        if self.log_file:
            try:
                self.log_file.close()
            except:
                pass
    
    def log(self, message):
        """Console log"""
        print(message)
    
    def write_shutdown_log(self, message):
        """Write shutdown debug log to verify clean exit"""
        try:
            with open(self.shutdown_log_path, "a", encoding="utf-8") as f:
                timestamp = datetime.now().isoformat(timespec="milliseconds")
                f.write(f"[{timestamp}] {message}\n")
                f.flush()
            self.log(f"SHUTDOWN LOG: {message}")
        except Exception as e:
            self.log(f"WARNING: Konnte Shutdown-Log nicht schreiben: {e}")
    
    def log_brightness_data(self, log_entries):
        """Log brightness data to file"""
        if not self.log_file:
            return
        try:
            ts = datetime.now().isoformat(timespec="milliseconds")
            for mid, raw_v, alpha_v, dim_v in log_entries:
                self.log_file.write(f"{ts},{mid},{raw_v:.3f},{alpha_v:.1f},{dim_v:.3f}\n")
            self.log_file.flush()
        except Exception:
            pass
