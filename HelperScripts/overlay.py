"""
Overlay window management for screen dimming
"""
import time
import win32gui
import win32con
import win32api
from mss import mss
from .config import DEBUG_LOGGING


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
            
            # Store reference to self for wndProc closure
            overlay_manager_ref = self
            
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
                    # Clean up when window is destroyed
                    return 0
                elif msg == win32con.WM_ERASEBKGND:
                    return 1
                elif msg == win32con.WM_CLOSE:
                    # Just destroy the window, don't modify the dict
                    # The dict will be cleaned up by destroy_overlay
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
                    
                    if DEBUG_LOGGING:
                        self.logger.log(f"DEBUG create_overlay: Monitor {monitor_id} - left={monitor_left}, top={monitor_top}, width={screen_width}, height={screen_height}")
            except Exception as e:
                self.logger.log(f"Fehler beim Lesen der Monitor-Info: {e}")
                return

            # Destroy existing overlay if present and handle is valid
            old_hwnd = self.hwnds.get(monitor_id)
            if old_hwnd:
                try:
                    # Try to destroy - if it fails, it's already gone
                    win32gui.PostMessage(old_hwnd, win32con.WM_CLOSE, 0, 0)
                    time.sleep(0.1)
                except:
                    pass
            
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
            
            # Store the new handle
            self.hwnds[monitor_id] = hwnd
            # IMPORTANT: Reset opacity to 0 when creating new overlay
            # This prevents using old opacity values from previous overlay
            self.current_opacity[monitor_id] = 0
            self.target_opacity[monitor_id] = 0
            
            # Initialize window attributes
            win32gui.SetLayeredWindowAttributes(hwnd, 0, 0, win32con.LWA_ALPHA)
            win32gui.ShowWindow(hwnd, win32con.SW_SHOWNOACTIVATE)
            win32gui.UpdateWindow(hwnd)
            
            # Set topmost and position
            win32gui.SetWindowPos(
                hwnd,
                win32con.HWND_TOPMOST,
                monitor_left - 1, monitor_top - 1,
                screen_width + 2, screen_height + 2,
                win32con.SWP_NOACTIVATE | win32con.SWP_SHOWWINDOW
            )
            
            win32gui.MoveWindow(hwnd, monitor_left - 1, monitor_top - 1, screen_width + 2, screen_height + 2, True)
            
            # Small delay to ensure window is fully created
            time.sleep(0.05)
            
            self.logger.log(f"Overlay erstellt fuer Monitor {monitor_id}: {screen_width}x{screen_height} @ ({monitor_left},{monitor_top})")
            
        except Exception as e:
            self.logger.log(f"ERROR: Overlay konnte nicht erstellt werden: {e}")
            # Remove from dict if creation failed
            self.hwnds.pop(monitor_id, None)
            self.current_opacity.pop(monitor_id, None)
            self.target_opacity.pop(monitor_id, None)
    
    def set_overlay_opacity(self, monitor_id, opacity, force_immediate=False):
        """Sets the overlay transparency for a specific monitor"""
        try:
            opacity = max(0, min(255, int(opacity)))
            
            if force_immediate:
                self.current_opacity[monitor_id] = opacity
            else:
                # Slower, smoother interpolation to reduce flicker
                current = self.current_opacity.get(monitor_id, 0)
                diff = opacity - current
                
                # Use slower interpolation factor to reduce flicker
                if abs(diff) > 1:
                    # Interpolate with factor 0.15 (slower than before 0.3)
                    self.current_opacity[monitor_id] = current + (diff * 0.15)
                else:
                    self.current_opacity[monitor_id] = opacity
            
            # Check if window handle still exists and is valid
            hwnd = self.hwnds.get(monitor_id)
            if hwnd:
                try:
                    win32gui.SetLayeredWindowAttributes(
                        hwnd, 
                        0,
                        int(self.current_opacity[monitor_id]), 
                        win32con.LWA_ALPHA
                    )
                except Exception as e:
                    # Window handle became invalid - log but don't remove from dict
                    # It will be recreated on next toggle if needed
                    if DEBUG_LOGGING:
                        self.logger.log(f"Window handle for monitor {monitor_id} invalid: {e}")
        except Exception as e:
            if DEBUG_LOGGING:
                self.logger.log(f"Error setting opacity for monitor {monitor_id}: {e}")
    
    def destroy_overlay(self, monitor_id):
        """Destroy overlay for a specific monitor"""
        hwnd = self.hwnds.get(monitor_id)
        
        if hwnd:
            # Remove from dictionaries first to prevent further access
            self.hwnds.pop(monitor_id, None)
            self.current_opacity.pop(monitor_id, None)
            self.target_opacity.pop(monitor_id, None)
            
            # Try to post close message
            try:
                win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
                self.logger.log(f"Overlay {monitor_id} close message sent")
            except Exception as e:
                # If PostMessage fails, window is already gone
                if DEBUG_LOGGING:
                    self.logger.log(f"Overlay {monitor_id} already closed: {e}")

    def destroy_all_overlays(self):
        """Destroy all overlays"""
        # Get all handles first
        handles_to_destroy = list(self.hwnds.items())
        
        # Clear dictionaries first
        self.hwnds.clear()
        self.current_opacity.clear()
        self.target_opacity.clear()
        
        # Then send close messages
        for monitor_id, hwnd in handles_to_destroy:
            if hwnd:
                try:
                    win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
                except Exception:
                    # Window already closed - this is fine during shutdown
                    pass
