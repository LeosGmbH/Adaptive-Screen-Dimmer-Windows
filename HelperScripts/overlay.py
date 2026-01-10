"""
Overlay window management for screen dimming
"""
import time
import traceback
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
        self.overlay_counter = {}  # Track overlay creation counter per monitor
    
    def create_overlay(self, monitor_id):
        """Creates a transparent full-screen overlay for a specific monitor"""
        try:
            # Increment counter for unique class names
            counter = self.overlay_counter.get(monitor_id, 0) + 1
            self.overlay_counter[monitor_id] = counter
            
            hinst = win32api.GetModuleHandle(None)
            # Use counter to make class name unique for each overlay instance
            className = f"AdaptiveDimOverlay_Mon{monitor_id}_v{counter}"
            
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
                    if DEBUG_LOGGING:
                        overlay_manager_ref.logger.log(f"WM_DESTROY for monitor {monitor_id} overlay v{counter}")
                    return 0
                elif msg == win32con.WM_ERASEBKGND:
                    return 1
                elif msg == win32con.WM_CLOSE:
                    if DEBUG_LOGGING:
                        overlay_manager_ref.logger.log(f"WM_CLOSE for monitor {monitor_id} overlay v{counter}")
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
            
            # Always register new class (unique per counter)
            try:
                win32gui.RegisterClass(wndClass)
            except Exception as e:
                # Class might already exist, that's ok
                if DEBUG_LOGGING:
                    self.logger.log(f"Class {className} registration: {e}")
            
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
                # DON'T destroy here - just mark as invalid
                # The window will be cleaned up by Windows when it's ready
                self.logger.log(f"Marking old overlay for monitor {monitor_id} as invalid")
                # Don't call DestroyWindow here - it causes race conditions!
            
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
            
            self.logger.log(f"Overlay erstellt fuer Monitor {monitor_id} (v{counter}): {screen_width}x{screen_height} @ ({monitor_left},{monitor_top})")
            
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
                # Verify window exists using IsWindow
                import ctypes
                if not ctypes.windll.user32.IsWindow(hwnd):
                    self.logger.log(f"Window handle {hwnd} for monitor {monitor_id} is not a valid window")
                    self.hwnds[monitor_id] = None
                    return False
                
                try:
                    # Verify handle is valid by trying to use it
                    win32gui.SetLayeredWindowAttributes(
                        hwnd, 
                        0,
                        int(self.current_opacity[monitor_id]), 
                        win32con.LWA_ALPHA
                    )
                    return True  # Success
                except Exception as e:
                    # Window handle became invalid - mark it as None so it gets recreated
                    self.logger.log(f"Window handle for monitor {monitor_id} invalid, marking for recreation: {e}")
                    self.hwnds[monitor_id] = None
                    return False
            else:
                # No valid handle
                return False
        except Exception as e:
            self.logger.log(f"Error setting opacity for monitor {monitor_id}: {e}")
            return False
    
    def destroy_overlay(self, monitor_id):
        """Destroy overlay for a specific monitor"""
        hwnd = self.hwnds.get(monitor_id)
        
        if hwnd:
            try:
                # Directly destroy the window
                win32gui.DestroyWindow(hwnd)
                self.logger.log(f"Overlay {monitor_id} destroyed")
            except Exception as e:
                # If DestroyWindow fails, window is already gone
                if DEBUG_LOGGING:
                    self.logger.log(f"Overlay {monitor_id} already destroyed: {e}")
            finally:
                # Always remove from dictionaries
                self.hwnds.pop(monitor_id, None)
                self.current_opacity.pop(monitor_id, None)
                self.target_opacity.pop(monitor_id, None)

    def destroy_all_overlays(self):
        """Destroy all overlays"""
        # Get all handles first
        handles_to_destroy = list(self.hwnds.items())
        
        # Clear dictionaries first
        self.hwnds.clear()
        self.current_opacity.clear()
        self.target_opacity.clear()
        
        # Then destroy windows
        for monitor_id, hwnd in handles_to_destroy:
            if hwnd:
                try:
                    win32gui.DestroyWindow(hwnd)
                except Exception:
                    # Window already closed - this is fine during shutdown
                    pass
