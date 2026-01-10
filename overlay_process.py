"""
Standalone Overlay Process
This process creates and manages a single overlay for one monitor
"""
import sys
import time
import win32gui
import win32con
import win32api
from mss import mss

def create_overlay(monitor_id, opacity_file):
    """Create overlay and update opacity from file"""
    try:
        # Get monitor info
        with mss() as sct:
            if monitor_id >= len(sct.monitors):
                print(f"ERROR: Monitor {monitor_id} not found")
                return
            
            monitor_info = sct.monitors[monitor_id]
            monitor_left = monitor_info['left']
            monitor_top = monitor_info['top']
            screen_width = monitor_info['width']
            screen_height = monitor_info['height']
        
        hinst = win32api.GetModuleHandle(None)
        className = f"OverlayProcess_Mon{monitor_id}_{int(time.time())}"
        
        # Window procedure
        def wndProc(hwnd, msg, wp, lp):
            if msg == win32con.WM_PAINT:
                hdc, ps = win32gui.BeginPaint(hwnd)
                brush = win32gui.CreateSolidBrush(0x00000000)
                win32gui.SelectObject(hdc, brush)
                rect = win32gui.GetClientRect(hwnd)
                win32gui.FillRect(hdc, rect, brush)
                win32gui.DeleteObject(brush)
                win32gui.EndPaint(hwnd, ps)
                return 0
            elif msg == win32con.WM_DESTROY:
                win32gui.PostQuitMessage(0)
                return 0
            elif msg == win32con.WM_ERASEBKGND:
                return 1
            elif msg == win32con.WM_CLOSE:
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
            pass
        
        # Create window
        hwnd = win32gui.CreateWindowEx(
            win32con.WS_EX_LAYERED | 
            win32con.WS_EX_TRANSPARENT | 
            win32con.WS_EX_TOPMOST | 
            win32con.WS_EX_NOACTIVATE,
            className,
            f"Overlay Monitor {monitor_id}",
            win32con.WS_POPUP | win32con.WS_VISIBLE,
            monitor_left, monitor_top,
            screen_width, screen_height,
            None, None, hinst, None
        )
        
        if not hwnd:
            print(f"ERROR: Could not create window for monitor {monitor_id}")
            return
        
        # Initialize as transparent
        win32gui.SetLayeredWindowAttributes(hwnd, 0, 0, win32con.LWA_ALPHA)
        win32gui.ShowWindow(hwnd, win32con.SW_SHOWNOACTIVATE)
        win32gui.UpdateWindow(hwnd)
        
        win32gui.SetWindowPos(
            hwnd,
            win32con.HWND_TOPMOST,
            monitor_left, monitor_top,
            screen_width, screen_height,
            win32con.SWP_NOACTIVATE | win32con.SWP_SHOWWINDOW
        )
        
        print(f"Overlay created for monitor {monitor_id}: {screen_width}x{screen_height} @ ({monitor_left},{monitor_top})")
        
        # Message loop with opacity updates
        last_update = time.time()
        current_opacity = 0
        
        while True:
            # Process Windows messages
            if win32gui.PumpWaitingMessages():
                # WM_QUIT received
                break
            
            # Update opacity from file every 50ms for fast response
            if time.time() - last_update >= 0.05:
                try:
                    with open(opacity_file, 'r') as f:
                        target_opacity = int(float(f.read().strip()))
                        target_opacity = max(0, min(255, target_opacity))
                        
                        # Very fast interpolation - reach target in 1-2 frames
                        if abs(current_opacity - target_opacity) > 2:
                            current_opacity = current_opacity + (target_opacity - current_opacity) * 0.8
                        else:
                            current_opacity = target_opacity
                        
                        win32gui.SetLayeredWindowAttributes(hwnd, 0, int(current_opacity), win32con.LWA_ALPHA)
                except FileNotFoundError:
                    pass  # File doesn't exist yet
                except Exception as e:
                    pass  # Ignore read errors
                
                last_update = time.time()
            
            time.sleep(0.01)  # 10ms sleep - very responsive
        
        print(f"Overlay process for monitor {monitor_id} exiting")
        
    except Exception as e:
        print(f"ERROR in overlay process: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: overlay_process.py <monitor_id> <opacity_file>")
        sys.exit(1)
    
    monitor_id = int(sys.argv[1])
    opacity_file = sys.argv[2]
    
    create_overlay(monitor_id, opacity_file)
