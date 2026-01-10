"""
Main GUI window for Adaptive Screen Dimmer
"""
import time
import threading
import tkinter as tk
from tkinter import ttk
import traceback
import win32gui
import win32con
from .config import WINDOW_GEOMETRY, MIN_WINDOW_SIZE, THEME_BG, THEME_FG, THEME_BUTTON, DEBUG_LOGGING
from .dimmer import AdaptiveDimmer
from .gui_components import ChartManager, MonitorSelector


class DimmerGUI:
    """Main GUI window"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Adaptive Screen Dimmer")
        self.root.geometry(WINDOW_GEOMETRY)
        self.root.resizable(True, True)
        self.root.minsize(*MIN_WINDOW_SIZE)
        self.root.report_callback_exception = self._handle_tk_exception
        self.root.configure(bg=THEME_BG)
        
        # State
        self.dimmer = None
        self.dimmer_thread = None
        self.active = False
        self.dim_strength = tk.DoubleVar(value=100.0)
        
        # Build UI
        self._build_ui()
        
        # Setup callbacks
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.after(500, self.auto_start)
        self.root.after(200, self._redraw_chart_callback)
        self.root.after(50, self._force_layout)
        self.root.after(20, self.on_dim_strength_change)
    
    def _build_ui(self):
        """Build the user interface"""
        # Title
        title_frame = tk.Frame(self.root, bg=THEME_BG)
        title_frame.pack(pady=6)
        
        tk.Label(
            title_frame,
            text="Adaptive Screen Dimmer",
            font=("Segoe UI", 14, "bold"),
            bg=THEME_BG,
            fg=THEME_FG
        ).pack()
        
        # Controls
        control_frame = tk.Frame(self.root, bg=THEME_BG)
        control_frame.pack(padx=10, pady=4, fill=tk.X)
        
        monitor_frame = tk.LabelFrame(
            control_frame,
            text="Settings",
            bg=THEME_BG,
            fg=THEME_FG,
            font=("Segoe UI", 10)
        )
        monitor_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        # Monitor selection
        list_frame = tk.Frame(monitor_frame, bg=THEME_BG)
        list_frame.pack(side=tk.LEFT, padx=6, pady=4, fill=tk.BOTH, expand=True)
        
        tk.Label(
            list_frame,
            text="Monitore dimmen:",
            bg=THEME_BG,
            fg=THEME_FG,
            font=("Segoe UI", 10, "bold")
        ).pack(anchor="w")
        
        monitor_container = tk.Frame(list_frame, bg=THEME_BG)
        monitor_container.pack(fill=tk.BOTH, expand=True, anchor="nw")
        
        self.monitor_selector = MonitorSelector(monitor_container, self.on_monitor_toggle)
        
        # Dim strength slider
        slider_frame = tk.Frame(monitor_frame, bg=THEME_BG)
        slider_frame.pack(side=tk.LEFT, padx=8, pady=4, fill=tk.Y)
        
        tk.Label(
            slider_frame,
            text="Dim strength",
            bg=THEME_BG,
            fg=THEME_FG,
            font=("Segoe UI", 9)
        ).pack(anchor="w")
        
        self.dim_scale = ttk.Scale(
            slider_frame,
            from_=0,
            to=100,
            orient="horizontal",
            variable=self.dim_strength,
            command=self.on_dim_strength_change,
            length=140
        )
        self.dim_scale.pack(fill=tk.X, expand=True, pady=(0, 2))
        
        self.dim_value_label = tk.Label(
            slider_frame,
            text="100%",
            bg=THEME_BG,
            fg=THEME_FG,
            font=("Segoe UI", 9)
        )
        self.dim_value_label.pack(anchor="w")
        
        # Action buttons
        action_frame = tk.Frame(monitor_frame, bg=THEME_BG)
        action_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=5, pady=2)
        
        self.pause_button = tk.Button(
            action_frame,
            text="PAUSIEREN",
            command=self.pause_dimmer,
            bg=THEME_BUTTON,
            fg=THEME_FG,
            font=("Segoe UI", 10, "bold"),
            width=15,
            state=tk.DISABLED,
            cursor="hand2"
        )
        self.pause_button.pack(side=tk.LEFT, padx=5, pady=5)
        
        self.resume_button = tk.Button(
            action_frame,
            text="FORTSETZEN",
            command=self.resume_dimmer,
            bg=THEME_BUTTON,
            fg=THEME_FG,
            font=("Segoe UI", 10, "bold"),
            width=15,
            state=tk.DISABLED,
            cursor="hand2"
        )
        self.resume_button.pack(side=tk.LEFT, padx=5, pady=5)
        
        # Chart
        chart_frame = tk.LabelFrame(
            self.root,
            text="Brightness (live)",
            bg=THEME_BG,
            fg=THEME_FG,
            font=("Segoe UI", 10)
        )
        chart_frame.pack(padx=10, pady=5, fill=tk.BOTH, expand=True)
        
        self.chart_manager = ChartManager(chart_frame)
        
        # Initialize monitors
        detected = self.monitor_selector.refresh()
        self.chart_manager.sync_monitors(detected)
    
    def add_log(self, message):
        """Console log"""
        print(message)
    
    def push_brightness(self, monitor_id, raw_value, dimmed_value):
        """Push brightness data to chart"""
        self.chart_manager.push_brightness(monitor_id, raw_value, dimmed_value)
    
    def on_dim_strength_change(self, event=None):
        """Update label when dim strength slider moves"""
        try:
            val = float(self.dim_strength.get())
            self.dim_value_label.config(text=f"{val:.0f}%")
        except Exception:
            pass
    
    def _handle_tk_exception(self, exc, val, tb):
        """Handle tkinter callback errors"""
        self.add_log(f"Tkinter ERROR: {val}")
        traceback.print_exception(exc, val, tb)
    
    def on_monitor_toggle(self):
        """Handle monitor checkbox toggle"""
        selected = self.monitor_selector.get_selected()
        
        # Allow empty selection
        self.monitor_selector.selected_monitors = selected
        
        if not self.dimmer or not self.active:
            return
        
        self.add_log(f"Monitor-Toggle: {self.dimmer.active_monitors} -> {selected}")
        
        # Simple and clean: just kill and restart processes
        current_monitors = set(self.dimmer.active_monitors)
        target_monitors = set(selected)
        
        # Stop overlays for monitors that are being disabled
        to_remove = current_monitors - target_monitors
        for mid in to_remove:
            self.add_log(f"Stoppe Overlay fuer Monitor {mid}")
            self.dimmer.overlay_manager.destroy_overlay(mid)
        
        # Start overlays for newly enabled monitors
        to_add = target_monitors - current_monitors
        for mid in to_add:
            self.add_log(f"Starte Overlay fuer Monitor {mid}")
            self.dimmer.overlay_manager.create_overlay(mid)
        
        # Update active monitors list
        self.dimmer.active_monitors = list(selected)
        
        # Update chart
        self.chart_manager.sync_monitors(selected)
        
        if selected:
            self.add_log(f"Monitor-Toggle COMPLETE: {selected}")
        else:
            self.add_log("Monitor-Toggle COMPLETE: Alle Monitore deaktiviert")
    
    def _redraw_chart_callback(self):
        """Periodic chart redraw callback"""
        self.chart_manager.redraw()
        self.root.after(200, self._redraw_chart_callback)
    
    def _force_layout(self):
        """Force initial layout"""
        try:
            self.root.update_idletasks()
            self.chart_manager.canvas.draw_idle()
        except Exception:
            pass
    
    def auto_start(self):
        """Auto-start the dimmer on startup"""
        self.add_log("Auto-Start: Abdunkler wird gestartet...")
        active_monitors = self.monitor_selector.get_selected()
        if not active_monitors:
            active_monitors = [1]
        
        self.add_log(f"Starte Abdunkler fuer Bildschirme: {active_monitors}...")
        self.active = True
        
        self.dimmer = AdaptiveDimmer(gui=self)
        self.dimmer.active_monitors = active_monitors
        self.chart_manager.sync_monitors(active_monitors)
        
        self.dimmer_thread = threading.Thread(target=self.dimmer.run, daemon=True)
        self.dimmer_thread.start()
        
        self.pause_button.config(state=tk.NORMAL)
        self.resume_button.config(state=tk.DISABLED)
        self.add_log("Abdunkler gestartet!")
    
    def pause_dimmer(self):
        """Pause the dimmer"""
        if not self.active or not self.dimmer:
            return
        
        self.dimmer.paused = True
        for monitor_id in self.dimmer.active_monitors:
            self.dimmer.target_opacity[monitor_id] = 0
            self.dimmer.set_overlay_opacity(monitor_id, 0, force_immediate=True)
        
        self.add_log("Abdunkler pausiert - Abdunkelung: 0/255")
        self.pause_button.config(state=tk.DISABLED)
        self.resume_button.config(state=tk.NORMAL)
    
    def resume_dimmer(self):
        """Resume the dimmer"""
        if not self.active or not self.dimmer:
            return
        
        self.dimmer.paused = False
        self.add_log("Abdunkler fortgesetzt")
        self.pause_button.config(state=tk.NORMAL)
        self.resume_button.config(state=tk.DISABLED)
    
    def on_closing(self):
        """Handle window close"""
        if DEBUG_LOGGING:
            self.add_log("DEBUG on_closing: start shutdown")
        
        if self.active and self.dimmer:
            self.add_log("Beende Abdunkler...")
            self.dimmer.write_shutdown_log("GUI on_closing() called - stopping dimmer")
            self.dimmer.running = False
            
            # Don't try to destroy windows manually - let the dimmer thread handle it
            self.dimmer.write_shutdown_log("Stopping dimmer, overlays will be cleaned up by run() thread")
            self.dimmer.logger.close_log_file()
        
        if self.dimmer_thread and self.dimmer_thread.is_alive():
            self.add_log("Warte auf Dimmer-Thread...")
            if self.dimmer:
                self.dimmer.write_shutdown_log("Waiting for dimmer thread to join")
            self.dimmer_thread.join(timeout=2)
            if self.dimmer:
                self.dimmer.write_shutdown_log("Dimmer thread joined")
        
        if self.dimmer:
            self.dimmer.write_shutdown_log("=== GUI SHUTDOWN COMPLETE ===")
        
        if DEBUG_LOGGING:
            self.add_log("DEBUG on_closing: destroy root")
        self.root.destroy()
        if DEBUG_LOGGING:
            self.add_log("DEBUG on_closing: shutdown complete")
