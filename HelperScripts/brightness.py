"""
Brightness measurement utilities
"""
import numpy as np
from mss import mss


class BrightnessMeasurer:
    """Measures screen brightness for monitors"""
    
    @staticmethod
    def measure_brightness(monitor_id):
        """
        Measures the average screen brightness for a specific monitor
        
        Args:
            monitor_id: Monitor index (1-based)
            
        Returns:
            float: Average brightness value
        """
        try:
            with mss() as sct:
                if monitor_id < len(sct.monitors):
                    monitor = sct.monitors[monitor_id]
                else:
                    monitor = sct.monitors[1]
                
                img = np.array(sct.grab(monitor))
                gray = np.mean(img[:, :, :3], axis=2)
                brightness = np.mean(gray)
                return brightness
        except Exception as e:
            print(f"Error measuring brightness on monitor {monitor_id}: {e}")
            return 0
    
    @staticmethod
    def calculate_raw_estimate(measured_brightness, current_opacity):
        """
        Calculate raw brightness estimate compensating for overlay opacity
        
        Args:
            measured_brightness: Measured brightness value
            current_opacity: Current overlay opacity (0-255)
            
        Returns:
            float: Estimated raw brightness
        """
        attenuation = max(0.05, 1 - current_opacity / 255.0)
        return measured_brightness / attenuation
    
    @staticmethod
    def calculate_dimmed_brightness(raw_estimate, current_opacity):
        """
        Calculate dimmed brightness value
        
        Args:
            raw_estimate: Raw brightness estimate
            current_opacity: Current overlay opacity (0-255)
            
        Returns:
            float: Dimmed brightness value
        """
        return raw_estimate * (1 - current_opacity / 255.0)
