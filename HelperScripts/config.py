"""
Constants and Configuration for Adaptive Screen Dimmer
"""

# Brightness thresholds
THRESHOLD_START = 80    # Dimming begins above this brightness (relative bright)
THRESHOLD_MAX = 200     # Maximum dimming reached at this brightness (very bright / white)

# Opacity settings
MAX_OPACITY = 240

# Timing
CHECK_INTERVAL = 0.05  # 50ms - fast real-time adaptation

# Debug settings
DEBUG_LOGGING = False  # Set to True for verbose logging

# GUI settings
WINDOW_GEOMETRY = "750x600"
MIN_WINDOW_SIZE = (500, 400)
MAX_CHART_POINTS = 120  # ~6s of data at 0.05s interval

# Colors for chart lines (raw, dimmed)
LINE_COLOR_PAIRS = [
    ("#f87171", "#b91c1c"),  # red
    ("#60a5fa", "#1d4ed8"),  # blue
    ("#34d399", "#047857"),  # green
    ("#c084fc", "#7e22ce"),  # purple
    ("#fbbf24", "#b45309"),  # amber
]

# Theme colors
THEME_BG = "#2b2b2b"
THEME_FG = "#ffffff"
THEME_CHART_BG = "#1b1b1b"
THEME_GRID = "#333333"
THEME_TEXT = "#cccccc"
THEME_BUTTON = "#ff7700"
