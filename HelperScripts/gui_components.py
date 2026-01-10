"""
GUI components and widgets for Adaptive Screen Dimmer
"""
import tkinter as tk
from tkinter import ttk
from collections import deque
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from mss import mss
from .config import (
    WINDOW_GEOMETRY, MIN_WINDOW_SIZE, MAX_CHART_POINTS,
    LINE_COLOR_PAIRS, THEME_BG, THEME_FG, THEME_CHART_BG,
    THEME_GRID, THEME_TEXT, THEME_BUTTON
)


class ChartManager:
    """Manages the brightness chart display"""
    
    def __init__(self, parent_frame, max_points=MAX_CHART_POINTS):
        self.max_points = max_points
        self.brightness_raw = {}
        self.brightness_dimmed = {}
        self.lines_raw = {}
        self.lines_dimmed = {}
        self.chart_dirty = False
        self.line_pairs = LINE_COLOR_PAIRS
        
        # Create figure
        self.fig = Figure(figsize=(6, 3.2), dpi=100, facecolor=THEME_CHART_BG, layout="constrained")
        self.ax = self.fig.add_subplot(111)
        self.ax.set_facecolor(THEME_CHART_BG)
        self.ax.grid(color=THEME_GRID, alpha=0.5)
        self.ax.set_ylim(0, 200)
        self.ax.set_xlim(0, self.max_points)
        self.ax.set_xlabel("Samples (~0.05s)", color=THEME_TEXT)
        self.ax.set_ylabel("Brightness", color=THEME_TEXT)
        self.ax.tick_params(colors=THEME_TEXT)
        
        # Create canvas
        self.canvas = FigureCanvasTkAgg(self.fig, master=parent_frame)
        self.canvas_widget = self.canvas.get_tk_widget()
        self.canvas_widget.configure(bg=THEME_CHART_BG, highlightthickness=0)
        self.canvas_widget.pack(padx=5, pady=5, fill=tk.BOTH, expand=True)
    
    def sync_monitors(self, monitors):
        """Ensure buffers/lines exist for active monitors"""
        # Remove stale
        for mid in list(self.brightness_raw.keys()):
            if mid not in monitors:
                self.brightness_raw.pop(mid, None)
                self.brightness_dimmed.pop(mid, None)
                line_r = self.lines_raw.pop(mid, None)
                line_d = self.lines_dimmed.pop(mid, None)
                if line_r:
                    line_r.remove()
                if line_d:
                    line_d.remove()
        
        # Add new
        for idx, mid in enumerate(monitors):
            if mid not in self.brightness_raw:
                self.brightness_raw[mid] = deque(maxlen=self.max_points)
                self.brightness_dimmed[mid] = deque(maxlen=self.max_points)
                raw_color, dim_color = self.line_pairs[idx % len(self.line_pairs)]
                (line_raw,) = self.ax.plot([], [], color=raw_color, linewidth=1.6, label=f"Mon {mid} raw")
                (line_dim,) = self.ax.plot([], [], color=dim_color, linewidth=1.6, linestyle="--", label=f"Mon {mid} dim")
                self.lines_raw[mid] = line_raw
                self.lines_dimmed[mid] = line_dim
        
        # Update legend
        if self.lines_raw or self.lines_dimmed:
            legend = self.ax.legend(facecolor=THEME_CHART_BG, edgecolor="#444444", labelcolor=THEME_TEXT)
            for text in legend.get_texts():
                text.set_color(THEME_TEXT)
        
        self.chart_dirty = True
    def push_brightness(self, monitor_id, raw_value, dimmed_value):
        """Append brightness samples for monitor"""
        if monitor_id not in self.brightness_raw:
            return
        self.brightness_raw[monitor_id].append(float(raw_value))
        self.brightness_dimmed[monitor_id].append(float(dimmed_value))
        self.chart_dirty = True
    
    def redraw(self):
        """Redraw the chart with current data"""
        if not self.chart_dirty:
            return False
        
        max_y = 200
        for mid in list(self.brightness_raw.keys()):
            buf_r = self.brightness_raw.get(mid, [])
            buf_d = self.brightness_dimmed.get(mid, [])
            line_r = self.lines_raw.get(mid)
            line_d = self.lines_dimmed.get(mid)
            
            if line_r is not None:
                if buf_r:
                    x = list(range(len(buf_r)))
                    y = list(buf_r)
                    line_r.set_data(x, y)
                    max_y = max(max_y, min(200, max(y)) + 5)
                else:
                    line_r.set_data([], [])
            
            if line_d is not None:
                if buf_d:
                    x = list(range(len(buf_d)))
                    y = list(buf_d)
                    line_d.set_data(x, y)
                    max_y = max(max_y, min(200, max(y)) + 5)
                else:
                    line_d.set_data([], [])
        
        self.ax.set_xlim(0, self.max_points)
        self.ax.set_ylim(0, min(200, max_y))
        self.canvas.draw_idle()
        self.chart_dirty = False
        return True


class MonitorSelector:
    """Manages monitor selection checkboxes"""
    
    def __init__(self, parent_frame, on_toggle_callback):
        self.parent_frame = parent_frame
        self.on_toggle_callback = on_toggle_callback
        self.monitor_checks = {}
        self.monitor_vars = {}
        self.selected_monitors = []
    
    def refresh(self):
        """Enumerate monitors and rebuild checkbox list"""
        # Clear existing
        for child in self.parent_frame.winfo_children():
            child.destroy()
        self.monitor_checks.clear()
        self.monitor_vars.clear()
        
        # Detect monitors
        try:
            with mss() as sct:
                monitors = sct.monitors
        except Exception as e:
            print(f"Fehler beim Lesen der Monitore: {e}")
            monitors = [{}]
        
        # monitors[0] is all monitors; we start from index 1
        detected = list(range(1, len(monitors)))
        if not detected:
            detected = [1]
        
        # Create checkboxes
        for mid in detected:
            var = tk.BooleanVar(value=True)
            chk = tk.Checkbutton(
                self.parent_frame,
                text=f"Monitor {mid}",
                variable=var,
                onvalue=True,
                offvalue=False,
                command=self.on_toggle_callback,
                bg=THEME_BG,
                fg=THEME_FG,
                selectcolor="#333333",
                activebackground=THEME_BG,
                activeforeground=THEME_FG,
                font=("Segoe UI", 9)
            )
            chk.pack(anchor="w")
            self.monitor_vars[mid] = var
            self.monitor_checks[mid] = chk
        
        self.selected_monitors = detected
        return detected
    
    def get_selected(self):
        """Return list of selected monitor IDs"""
        return [mid for mid, var in self.monitor_vars.items() if var.get()]
    
    def set_selected(self, monitor_ids):
        """Set which monitors are selected"""
        for mid, var in self.monitor_vars.items():
            var.set(mid in monitor_ids)
        self.selected_monitors = monitor_ids
