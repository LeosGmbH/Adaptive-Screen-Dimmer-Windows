import time
import numpy as np
from mss import mss
import win32gui
import win32con
import win32api
import sys
import ctypes
import threading
import tkinter as tk
from tkinter import scrolledtext, ttk
import logging
from io import StringIO
from datetime import datetime

# Parameters
THRESHOLD_START = 25
THRESHOLD_MAX = 100
MAX_OPACITY = 240
CHECK_INTERVAL = 0.05

class LogCapture:
    """Captures log messages and sends them to GUI"""
    def __init__(self, text_widget):
        self.text_widget = text_widget
        self.text_widget.config(state=tk.DISABLED)
    
    def write(self, message):
        if message.strip():
            self.text_widget.config(state=tk.NORMAL)
            timestamp = datetime.now().strftime("%H:%M:%S")
            self.text_widget.insert(tk.END, f"[{timestamp}] {message}\n")
            self.text_widget.see(tk.END)
            self.text_widget.config(state=tk.DISABLED)
    
    def flush(self):
        pass

class AdaptiveDimmer:
    def __init__(self, gui=None):
        self.hwnds = {}
        self.running = True
        self.paused = False
        self.current_opacity = {}
        self.target_opacity = {}
        self.gui = gui
        self.active_monitors = [1]
        self.monitor_lock = threading.Lock()
        self.switching_monitor = False
        
    def log(self, message):
        """Log message to console and GUI if available"""
        print(message)
        if self.gui:
            self.gui.add_log(message)
        
    def measure_brightness(self, monitor_id):
        """Measures the average screen brightness for a specific monitor"""
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
            self.log(f"Error measuring brightness on monitor {monitor_id}: {e}")
            return 0

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
            self.log(f"Error setting opacity: {e}")

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
            
            try:
                with mss() as sct:
                    if monitor_id < len(sct.monitors):
                        monitor_info = sct.monitors[monitor_id]
                    else:
                        self.log(f"⚠️ Monitor {monitor_id} nicht gefunden")
                        return
                    
                    monitor_left = monitor_info['left']
                    monitor_top = monitor_info['top']
                    screen_width = monitor_info['width']
                    screen_height = monitor_info['height']
                    
                    self.log(f"DEBUG create_overlay: Monitor {monitor_id} - left={monitor_left}, top={monitor_top}, width={screen_width}, height={screen_height}")
            except Exception as e:
                self.log(f"Fehler beim Lesen der Monitor-Info: {e}")
                return

            if monitor_id in self.hwnds and self.hwnds[monitor_id]:
                try:
                    win32gui.DestroyWindow(self.hwnds[monitor_id])
                except:
                    pass
                self.hwnds[monitor_id] = None
            
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
            self.log(f"Overlay erstellt für Monitor {monitor_id}: {screen_width}x{screen_height} @ ({monitor_left},{monitor_top})")
            
        except Exception as e:
            self.log(f"ERROR: Overlay konnte nicht erstellt werden: {e}")

    def monitor_loop(self):
        """Main loop for brightness monitoring"""
        last_print = time.time()
        
        try:
            while self.running:
                if self.paused:
                    time.sleep(CHECK_INTERVAL)
                    continue
                
                with self.monitor_lock:
                    if not self.running:
                        break
                    
                    for monitor_id in self.active_monitors:
                        brightness = self.measure_brightness(monitor_id)
                        
                        if brightness > THRESHOLD_MAX:
                            self.target_opacity[monitor_id] = MAX_OPACITY
                        elif brightness > THRESHOLD_START:
                            ratio = (brightness - THRESHOLD_START) / (THRESHOLD_MAX - THRESHOLD_START)
                            self.target_opacity[monitor_id] = ratio * MAX_OPACITY
                        else:
                            self.target_opacity[monitor_id] = 0
                        
                        self.set_overlay_opacity(monitor_id, self.target_opacity[monitor_id])
                
                if time.time() - last_print >= 2.0:
                    for monitor_id in self.active_monitors:
                        brightness = self.measure_brightness(monitor_id)
                        opacity = self.current_opacity.get(monitor_id, 0)
                        status = "🔴 AKTIV" if self.target_opacity.get(monitor_id, 0) > 5 else "⚫ AUS"
                        self.log(f"Monitor {monitor_id}: {status} | Helligkeit: {brightness:.1f} | Abdunkelung: {opacity:.1f}/255")
                    if self.gui:
                        brightness = self.measure_brightness(self.active_monitors[0])
                        opacity = self.current_opacity.get(self.active_monitors[0], 0)
                        self.gui.update_status(f"Helligkeit: {brightness:.1f}", opacity)
                    last_print = time.time()
                
                time.sleep(CHECK_INTERVAL)
        
        except KeyboardInterrupt:
            self.log("\nProgramm wird beendet...")
            self.running = False

    def run(self):
        """Starts the dimmer"""
        self.log("=" * 50)
        self.log("ADAPTIVE SCREEN DIMMING v2 - GUI")
        self.log("=" * 50)
        self.log(f"Abdunkelung ab: {THRESHOLD_START}")
        self.log(f"Maximum bei: {THRESHOLD_MAX}")
        self.log(f"Max. Abdunkelung: {MAX_OPACITY}/255")
        self.log(f"Check Interval: {CHECK_INTERVAL}s")
        self.log(f"Aktive Bildschirme: {self.active_monitors}")
        self.log("")
        
        for monitor_id in self.active_monitors:
            self.create_overlay(monitor_id)

        monitor_thread = threading.Thread(target=self.monitor_loop, daemon=True)
        monitor_thread.start()

        try:
            while self.running:
                win32gui.PumpWaitingMessages()
                time.sleep(0.01)
        except KeyboardInterrupt:
            self.log("\nProgramm wird beendet...")
            self.running = False
            for hwnd in self.hwnds.values():
                if hwnd:
                    win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
        except Exception as e:
            self.log(f"\nFEHLER: {e}")
            self.running = False
        finally:
            monitor_thread.join(timeout=1)
            for monitor_id in list(self.hwnds.keys()):
                if self.hwnds[monitor_id]:
                    try:
                        win32gui.DestroyWindow(self.hwnds[monitor_id])
                    except Exception:
                        pass
            self.log("✓ Overlay geschlossen")


class DimmerGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Adaptive Screen Dimmer")
        self.root.geometry("650x550")
        self.root.resizable(True, True)
        self.root.minsize(500, 400)
        
        self.dimmer = None
        self.dimmer_thread = None
        self.active = False
        
        self.root.configure(bg="#2b2b2b")
        
        title_frame = tk.Frame(self.root, bg="#2b2b2b")
        title_frame.pack(pady=10)
        
        title_label = tk.Label(
            title_frame, 
            text="Adaptive Screen Dimmer", 
            font=("Segoe UI", 14, "bold"),
            bg="#2b2b2b",
            fg="#ffffff"
        )
        title_label.pack()
        
        monitor_frame = tk.LabelFrame(
            self.root, 
            text="Bildschirm Modus",
            bg="#2b2b2b",
            fg="#ffffff",
            font=("Segoe UI", 10)
        )
        monitor_frame.pack(padx=10, pady=5, fill=tk.X)
        
        monitor_label = tk.Label(
            monitor_frame, 
            text="Welcher Modus:",
            bg="#2b2b2b",
            fg="#ffffff"
        )
        monitor_label.pack(side=tk.LEFT, padx=5, pady=5)
        
        self.mode_var = tk.StringVar(value="Nur Monitor 1")
        self.mode_modes = ["Nur Monitor 1", "Nur Monitor 2", "Beide Bildschirme"]
        self.mode_combo = ttk.Combobox(
            monitor_frame,
            textvariable=self.mode_var,
            values=self.mode_modes,
            state="readonly",
            width=30
        )
        self.mode_combo.pack(side=tk.LEFT, padx=5, pady=5)
        self.mode_combo.bind("<<ComboboxSelected>>", self.on_mode_change)
        
        status_frame = tk.LabelFrame(
            self.root,
            text="Status",
            bg="#2b2b2b",
            fg="#ffffff",
            font=("Segoe UI", 10)
        )
        status_frame.pack(padx=10, pady=5, fill=tk.X)
        
        self.status_label = tk.Label(
            status_frame,
            text="🔄 Initialisiert...",
            bg="#2b2b2b",
            fg="#00ff00",
            font=("Segoe UI", 9)
        )
        self.status_label.pack(padx=5, pady=5)
        
        log_frame = tk.LabelFrame(
            self.root,
            text="Logs",
            bg="#2b2b2b",
            fg="#ffffff",
            font=("Segoe UI", 10)
        )
        log_frame.pack(padx=10, pady=5, fill=tk.BOTH, expand=True)
        
        self.log_text = scrolledtext.ScrolledText(
            log_frame,
            height=12,
            width=60,
            bg="#1e1e1e",
            fg="#00ff00",
            font=("Courier New", 8),
            wrap=tk.WORD
        )
        self.log_text.pack(padx=5, pady=5, fill=tk.BOTH, expand=True)
        self.log_text.config(state=tk.DISABLED)
        
        button_frame = tk.Frame(self.root, bg="#2b2b2b")
        button_frame.pack(pady=10, fill=tk.X, padx=10)
        
        self.pause_button = tk.Button(
            button_frame,
            text="⏸ PAUSIEREN",
            command=self.pause_dimmer,
            bg="#ff7700",
            fg="#ffffff",
            font=("Segoe UI", 10, "bold"),
            width=20,
            state=tk.DISABLED,
            cursor="hand2"
        )
        self.pause_button.pack(side=tk.LEFT, padx=5)
        
        self.resume_button = tk.Button(
            button_frame,
            text="▶ FORTSETZEN",
            command=self.resume_dimmer,
            bg="#ff7700",
            fg="#ffffff",
            font=("Segoe UI", 10, "bold"),
            width=20,
            state=tk.DISABLED,
            cursor="hand2"
        )
        self.resume_button.pack(side=tk.LEFT, padx=5)
        
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.after(500, self.auto_start)
        
    def add_log(self, message):
        """Add message to log"""
        self.log_text.config(state=tk.NORMAL)
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
    
    def update_status(self, brightness_text, opacity):
        """Update status label"""
        opacity_pct = (opacity / 255) * 100
        pause_info = " (⏸ PAUSIERT)" if self.dimmer and self.dimmer.paused else ""
        self.status_label.config(text=f"{brightness_text} | Abdunkelung: {opacity_pct:.0f}%{pause_info}")
    
    def on_mode_change(self, event=None):
        """Handle mode selection change"""
        if self.active and self.dimmer:
            mode = self.mode_var.get()
            
            if mode == "Nur Monitor 1":
                new_monitors = [1]
            elif mode == "Nur Monitor 2":
                new_monitors = [2]
            else:
                new_monitors = [1, 2]
            
            old_monitors = self.dimmer.active_monitors
            
            if old_monitors == new_monitors:
                return
            
            self.add_log(f"⚡ Modus gewechselt: {old_monitors} → {new_monitors}")
            
            with self.dimmer.monitor_lock:
                self.dimmer.switching_monitor = True
                
                try:
                    for monitor_id in old_monitors:
                        if monitor_id not in new_monitors and monitor_id in self.dimmer.hwnds:
                            try:
                                if self.dimmer.hwnds[monitor_id]:
                                    win32gui.DestroyWindow(self.dimmer.hwnds[monitor_id])
                                    del self.dimmer.hwnds[monitor_id]
                                    if monitor_id in self.dimmer.current_opacity:
                                        del self.dimmer.current_opacity[monitor_id]
                                    if monitor_id in self.dimmer.target_opacity:
                                        del self.dimmer.target_opacity[monitor_id]
                            except Exception as e:
                                self.add_log(f"Fehler beim Löschen des Overlays für Monitor {monitor_id}: {e}")
                    
                    time.sleep(0.1)
                    
                    for monitor_id in new_monitors:
                        if monitor_id not in old_monitors:
                            try:
                                self.dimmer.create_overlay(monitor_id)
                            except Exception as e:
                                self.add_log(f"Fehler beim Erstellen des Overlays für Monitor {monitor_id}: {e}")
                    
                    self.dimmer.active_monitors = new_monitors
                finally:
                    self.dimmer.switching_monitor = False
    
    def auto_start(self):
        """Auto-start the dimmer on startup"""
        self.add_log("Auto-Start: Abdunkler wird gestartet...")
        mode = self.mode_var.get()
        
        if mode == "Nur Monitor 1":
            active_monitors = [1]
        elif mode == "Nur Monitor 2":
            active_monitors = [2]
        else:
            active_monitors = [1, 2]
        
        self.add_log(f"Starte Abdunkler für Bildschirme: {active_monitors}...")
        self.active = True
        
        self.dimmer = AdaptiveDimmer(gui=self)
        self.dimmer.active_monitors = active_monitors
        
        self.dimmer_thread = threading.Thread(target=self.dimmer.run, daemon=True)
        self.dimmer_thread.start()
        
        self.pause_button.config(state=tk.NORMAL)
        self.resume_button.config(state=tk.DISABLED)
        self.mode_combo.config(state="readonly")
        self.status_label.config(text="🔴 LÄUFT", fg="#00ff00")
        self.add_log("✓ Abdunkler gestartet!")
    
    def pause_dimmer(self):
        """Pause the dimmer"""
        if not self.active or not self.dimmer:
            return
        
        self.dimmer.paused = True
        for monitor_id in self.dimmer.active_monitors:
            self.dimmer.target_opacity[monitor_id] = 0
            self.dimmer.set_overlay_opacity(monitor_id, 0, force_immediate=True)
        self.add_log("⏸ Abdunkler pausiert - Abdunkelung: 0/255")
        
        self.pause_button.config(state=tk.DISABLED)
        self.resume_button.config(state=tk.NORMAL)
        self.status_label.config(text="⏸ PAUSIERT (0%)", fg="#ff7700")
    
    def resume_dimmer(self):
        """Resume the dimmer"""
        if not self.active or not self.dimmer:
            return
        
        self.dimmer.paused = False
        self.add_log("▶ Abdunkler fortgesetzt")
        
        self.pause_button.config(state=tk.NORMAL)
        self.resume_button.config(state=tk.DISABLED)
        self.status_label.config(text="🔴 LÄUFT", fg="#00ff00")
    
    def on_closing(self):
        """Handle window close"""
        if self.active and self.dimmer:
            self.add_log("Beende Abdunkler...")
            self.dimmer.running = False
            for hwnd in self.dimmer.hwnds.values():
                if hwnd:
                    try:
                        win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
                    except:
                        pass
        
        if self.dimmer_thread and self.dimmer_thread.is_alive():
            self.dimmer_thread.join(timeout=2)
        
        self.root.destroy()


def main():
    print("🔍 DEBUG: main() started")
    try:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass
        is_admin = ctypes.windll.shell32.IsUserAnAdmin()
        if not is_admin:
            print("⚠️  WARNUNG: Programm läuft nicht als Administrator")
            print("   Falls Probleme auftreten, mit Rechtsklick -> 'Als Administrator ausführen'\n")
    except:
        pass
    
    print("🔍 DEBUG: Creating DimmerGUI...")
    try:
        gui = DimmerGUI()
        print("🔍 DEBUG: DimmerGUI created successfully")
        print("🔍 DEBUG: Starting mainloop...")
        gui.root.mainloop()
        print("🔍 DEBUG: mainloop ended")
    except Exception as e:
        print(f"❌ ERROR in GUI creation: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n\nCRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        time.sleep(3)
        sys.exit(1)
