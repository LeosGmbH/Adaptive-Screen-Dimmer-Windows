import time
import numpy as np
from mss import mss
import win32gui
import win32con
import win32api
import sys
import ctypes
import threading

# Parameters
THRESHOLD_START = 25   # Dimming starts at this brightness
THRESHOLD_MAX = 100    # Maximum dimming is reached at this brightness (tuned to your ~98 max)
MAX_OPACITY = 240      # 0–255 (higher = darker)
CHECK_INTERVAL = 0.05  # Faster reaction

class AdaptiveDimmer:
    def __init__(self):
        self.hwnd = None
        self.running = True
        self.current_opacity = 0
        self.target_opacity = 0
        self.screen_width = 0
        self.screen_height = 0
        self.monitor_left = 0
        self.monitor_top = 0
        
    def measure_brightness(self):
        """Measures the average screen brightness"""
        try:
            with mss() as sct:
                monitor = sct.monitors[1]
                img = np.array(sct.grab(monitor))
                gray = np.mean(img[:, :, :3], axis=2)
                brightness = np.mean(gray)
                return brightness
        except Exception as e:
            print(f"Error measuring: {e}")
            return 0

    def set_overlay_opacity(self, opacity):
        """Sets the overlay transparency with smoothing"""
        try:
            opacity = max(0, min(255, int(opacity)))
            
            # Smooth transitions (prevents flickering)
            if abs(self.current_opacity - opacity) > 1:
                self.current_opacity += (opacity - self.current_opacity) * 0.3
            else:
                self.current_opacity = opacity
            
            win32gui.SetLayeredWindowAttributes(
                self.hwnd, 
                0,  # Color key (not used)
                int(self.current_opacity), 
                win32con.LWA_ALPHA
            )
        except Exception as e:
            print(f"Error setting opacity: {e}")

    def create_overlay(self):
        """Creates a transparent full-screen overlay"""
        try:
            hinst = win32api.GetModuleHandle(None)
            className = "AdaptiveDimOverlay_v2"
            
            # Window procedure
            def wndProc(hwnd, msg, wp, lp):
                if msg == win32con.WM_PAINT:
                    hdc, ps = win32gui.BeginPaint(hwnd)
                    # Black rectangle over entire screen
                    brush = win32gui.CreateSolidBrush(0x00000000)
                    win32gui.SelectObject(hdc, brush)
                    rect = win32gui.GetClientRect(hwnd)
                    win32gui.FillRect(hdc, rect, brush)
                    win32gui.DeleteObject(brush)
                    win32gui.EndPaint(hwnd, ps)
                    return 0
                elif msg == win32con.WM_DESTROY:
                    self.running = False
                    win32gui.PostQuitMessage(0)
                    return 0
                elif msg == win32con.WM_ERASEBKGND:
                    return 1  # Prevents flickering
                elif msg == win32con.WM_CLOSE:
                    self.running = False
                    win32gui.DestroyWindow(hwnd)
                    return 0
                return win32gui.DefWindowProc(hwnd, msg, wp, lp)
            
            # Register window class
            wndClass = win32gui.WNDCLASS()
            wndClass.lpfnWndProc = wndProc
            wndClass.hInstance = hinst
            wndClass.lpszClassName = className
            wndClass.hCursor = win32gui.LoadCursor(0, win32con.IDC_ARROW)
            wndClass.hbrBackground = win32gui.GetStockObject(win32con.BLACK_BRUSH)
            
            try:
                win32gui.RegisterClass(wndClass)
            except:
                pass  # Class already registered
            
            # Get primary monitor bounds (respects DPI scaling)
            monitor = win32api.MonitorFromPoint((0, 0))
            info = win32api.GetMonitorInfo(monitor)
            left, top, right, bottom = info["Monitor"]
            self.monitor_left = left
            self.monitor_top = top
            self.screen_width = right - left
            self.screen_height = bottom - top

            print(f"  DEBUG: Using size: {self.screen_width}x{self.screen_height} at ({self.monitor_left},{self.monitor_top})")
            
            # Create window - FORCE FULLSCREEN
            self.hwnd = win32gui.CreateWindowEx(
                win32con.WS_EX_LAYERED | 
                win32con.WS_EX_TRANSPARENT | 
                win32con.WS_EX_TOPMOST | 
                win32con.WS_EX_NOACTIVATE,
                className,
                "",
                win32con.WS_POPUP | win32con.WS_VISIBLE,
                self.monitor_left - 1, self.monitor_top - 1,  # Slightly negative for safety
                self.screen_width + 2, self.screen_height + 2,  # Slightly larger to cover edges
                None, None, hinst, None
            )
            
            if not self.hwnd:
                raise Exception("Window could not be created")
            
            # Initially invisible (opacity = 0)
            win32gui.SetLayeredWindowAttributes(self.hwnd, 0, 0, win32con.LWA_ALPHA)
            
            # Show window
            win32gui.ShowWindow(self.hwnd, win32con.SW_SHOWNOACTIVATE)
            win32gui.UpdateWindow(self.hwnd)
            
            # BRUTAL: Force size with multiple methods
            win32gui.SetWindowPos(
                self.hwnd,
                win32con.HWND_TOPMOST,
                self.monitor_left - 1, self.monitor_top - 1,
                self.screen_width + 2, self.screen_height + 2,
                win32con.SWP_NOACTIVATE | win32con.SWP_SHOWWINDOW
            )
            
            # Again with MoveWindow
            win32gui.MoveWindow(self.hwnd, self.monitor_left - 1, self.monitor_top - 1, self.screen_width + 2, self.screen_height + 2, True)
            
            # Check what actually happened
            rect = win32gui.GetWindowRect(self.hwnd)
            actual_width = rect[2] - rect[0]
            actual_height = rect[3] - rect[1]
            
            print(f"✓ Overlay created (HWND: {self.hwnd})")
            print(f"  Target size: {self.screen_width}x{self.screen_height}")
            print(f"  Window size: {actual_width}x{actual_height}")
            print(f"  Position: ({rect[0]}, {rect[1]})")
            
            if actual_width < self.screen_width or actual_height < self.screen_height:
                print(f"  ⚠️  WARNING: Window is too small!")
            
        except Exception as e:
            print(f"ERROR creating overlay: {e}")
            sys.exit(1)

    def monitor_loop(self):
        """Main loop for brightness monitoring"""
        frame_count = 0
        last_print = time.time()
        
        try:
            while self.running:
                brightness = self.measure_brightness()
                
                # Dynamic opacity between THRESHOLD_START and THRESHOLD_MAX
                if brightness > THRESHOLD_MAX:
                    # Above maximum: Full dimming
                    self.target_opacity = MAX_OPACITY
                elif brightness > THRESHOLD_START:
                    # Between start and max: Linear interpolation
                    ratio = (brightness - THRESHOLD_START) / (THRESHOLD_MAX - THRESHOLD_START)
                    self.target_opacity = ratio * MAX_OPACITY
                else:
                    # Below start: No dimming
                    self.target_opacity = 0
                
                self.set_overlay_opacity(self.target_opacity)
                
                # Debug output every 2 seconds
                frame_count += 1
                if time.time() - last_print >= 2.0:
                    status = "🔴 ACTIVE" if self.target_opacity > 5 else "⚫ INACTIVE"
                    print(f"{status} | Brightness: {brightness:.1f} | Dimming: {self.current_opacity:.1f}/255")
                    last_print = time.time()
                
                time.sleep(CHECK_INTERVAL)
        
        except KeyboardInterrupt:
            print("\n\n✓ Program is terminating...")
            self.running = False

    def run(self):
        """Starts the dimmer"""
        print("=" * 50)
        print("ADAPTIVE SCREEN DIMMING v2")
        print("=" * 50)
        print(f"Dimming starts at: {THRESHOLD_START}")
        print(f"Maximum reached at: {THRESHOLD_MAX}")
        print(f"Max. dimming: {MAX_OPACITY}/255")
        print(f"Check interval: {CHECK_INTERVAL}s")
        print("\nPress CTRL+C to exit\n")
        
        self.create_overlay()

        # Run monitor loop in a background thread so the window message pump stays responsive
        monitor_thread = threading.Thread(target=self.monitor_loop, daemon=True)
        monitor_thread.start()

        try:
            # Lightweight message pump to keep the overlay responsive
            while self.running:
                win32gui.PumpWaitingMessages()
                time.sleep(0.01)
        except KeyboardInterrupt:
            print("\n\n✓ Program is terminating...")
            self.running = False
            if self.hwnd:
                win32gui.PostMessage(self.hwnd, win32con.WM_CLOSE, 0, 0)
        except Exception as e:
            print(f"\n\nERROR: {e}")
            self.running = False
        finally:
            monitor_thread.join(timeout=1)
            if self.hwnd:
                try:
                    win32gui.DestroyWindow(self.hwnd)
                except Exception:
                    pass
            print("✓ Overlay closed")
            sys.exit(0)

def main():
    # Check admin rights
    try:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass
        is_admin = ctypes.windll.shell32.IsUserAnAdmin()
        if not is_admin:
            print("⚠️  WARNING: Program is not running as administrator")
            print("   If problems, right-click -> 'Run as administrator'\n")
    except:
        pass
    
    dimmer = AdaptiveDimmer()
    dimmer.run()

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n\nCRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        time.sleep(3)  # Wait 3 seconds, then auto-close
        sys.exit(1)