"""
Overlay window management for screen dimming
"""
import win32gui
import win32con
import win32api
from mss import mss


class OverlayManager:
    """Manages transparent overlay windows for dimming"""
    
    def __init__(self, logger):
        self.hwnds = {}
        self.current_opacity = {}
        self.target_opacity = {}
        self.logger = logger
        self.switching_monitor = False
    
    def create_overlay(self, monitor_id):
        """Creates a transparent full-screen overlay for a specific monitor"""
        try:
            hinst = win32api.GetModuleHandle(None)
            className = f"AdaptiveDimOverlay_Mon{monitor_id}"
            
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
                    if not self.switching_monitor:
                        if monitor_id in self.hwnds:
                            del self.hwnds[monitor_id]
                    return 0
                elif msg == win32con.WM_ERASEBKGND:
                    return 1
                elif msg == win32con.WM_CLOSE:
                    if not self.switching_monitor and monitor_id in self.hwnds:
                        del self.hwnds[monitor_id]
                    win32gui.DestroyWindow(hwnd)
                    return 0
                return win32gui.DefWindowProc(hwnd, msg, wp, lp)
            
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
            
            # Get monitor information
            try:
                with mss() as sct:
                    if monitor_id < len(sct.monitors):
                        monitor_info = sct.monitors[monitor_id]
                    else:
                        self.logger.log(f"WARNING: Monitor {monitor_id} nicht gefunden")
                        return
                    
                    monitor_left = monitor_info['left']
                    monitor_top = monitor_info['top']
                    screen_width = monitor_info['width']
                    screen_height = monitor_info['height']
                    
                    self.logger.log(f"DEBUG create_overlay: Monitor {monitor_id} - left={monitor_left}, top={monitor_top}, width={screen_width}, height={screen_height}")
            except Exception as e:
                self.logger.log(f"Fehler beim Lesen der Monitor-Info: {e}")
                return

            # Destroy existing overlay if present
            if monitor_id in self.hwnds and self.hwnds[monitor_id]:
                try:
                    win32gui.DestroyWindow(self.hwnds[monitor_id])
                except:
                    pass
                self.hwnds[monitor_id] = None
            
            # Create window
            hwnd = win32gui.CreateWindowEx(
                win32con.WS_EX_LAYERED | 
                win32con.WS_EX_TRANSPARENT | 
                win32con.WS_EX_TOPMOST | 
                win32con.WS_EX_NOACTIVATE,
                className,
                "",
                win32con.WS_POPUP | win32con.WS_VISIBLE,
                monitor_left - 1, monitor_top - 1,
                screen_width + 2, screen_height + 2,
                None, None, hinst, None
            )
            
            if not hwnd:
                raise Exception("Fenster konnte nicht erstellt werden")
            
            self.hwnds[monitor_id] = hwnd
            self.current_opacity[monitor_id] = 0
            self.target_opacity[monitor_id] = 0
            
            win32gui.SetLayeredWindowAttributes(hwnd, 0, 0, win32con.LWA_ALPHA)
            win32gui.ShowWindow(hwnd, win32con.SW_SHOWNOACTIVATE)
            win32gui.UpdateWindow(hwnd)
            
            win32gui.SetWindowPos(
                hwnd,
                win32con.HWND_TOPMOST,
                monitor_left - 1, monitor_top - 1,
                screen_width + 2, screen_height + 2,
                win32con.SWP_NOACTIVATE | win32con.SWP_SHOWWINDOW
            )
            
            win32gui.MoveWindow(hwnd, monitor_left - 1, monitor_top - 1, screen_width + 2, screen_height + 2, True)
            self.logger.log(f"Overlay erstellt fuer Monitor {monitor_id}: {screen_width}x{screen_height} @ ({monitor_left},{monitor_top})")
            
        except Exception as e:
            self.logger.log(f"ERROR: Overlay konnte nicht erstellt werden: {e}")
    
    def set_overlay_opacity(self, monitor_id, opacity, force_immediate=False):
        """Sets the overlay transparency for a specific monitor"""
        try:
            opacity = max(0, min(255, int(opacity)))
            
            if force_immediate:
                self.current_opacity[monitor_id] = opacity
            elif abs(self.current_opacity.get(monitor_id, 0) - opacity) > 1:
                self.current_opacity[monitor_id] = self.current_opacity.get(monitor_id, 0) + (opacity - self.current_opacity.get(monitor_id, 0)) * 0.3
            else:
                self.current_opacity[monitor_id] = opacity
            
            if monitor_id in self.hwnds and self.hwnds[monitor_id]:
                win32gui.SetLayeredWindowAttributes(
                    self.hwnds[monitor_id], 
                    0,
                    int(self.current_opacity[monitor_id]), 
                    win32con.LWA_ALPHA
                )
        except Exception as e:
            self.logger.log(f"Error setting opacity: {e}")
    
    def destroy_overlay(self, monitor_id):
        """Destroy overlay for a specific monitor"""
        if monitor_id in self.hwnds and self.hwnds[monitor_id]:
            try:
                win32gui.DestroyWindow(self.hwnds[monitor_id])
            except Exception as e:
                self.logger.log(f"Error destroying overlay {monitor_id}: {e}")
            finally:
                self.hwnds.pop(monitor_id, None)
                self.current_opacity.pop(monitor_id, None)
                self.target_opacity.pop(monitor_id, None)
    
    def destroy_all_overlays(self):
        """Destroy all overlays"""
        for monitor_id in list(self.hwnds.keys()):
            if self.hwnds[monitor_id]:
                try:
                    win32gui.DestroyWindow(self.hwnds[monitor_id])
                except Exception as ex:
                    self.logger.write_shutdown_log(f"Error destroying overlay {monitor_id}: {ex}")
