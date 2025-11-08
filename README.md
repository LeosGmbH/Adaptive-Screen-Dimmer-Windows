# Adaptive-Screen-Dimmer-Windows-

![Demo](https://via.placeholder.com/600x400?text=Screen+Dimmer+Demo)

Automatically dims your screen when it detects bright content to prevent eye strain and flash blindness.

## Features
- 🛡️ **Eye Protection**: Reduces eye strain from bright screens
- ⚙️ **Auto-Adjusting**: Dynamically adjusts dimming based on screen brightness
- ⏱️ **Fast Response**: Checks screen brightness every 50ms
- 🔧 **Customizable**: Adjust sensitivity and dimming strength

## Installation
1. Clone this repository
2. Install requirements:
   ```
   pip install mss numpy pywin32
   ```
3. Run the application:
   ```
   adaptive_dimmer_START.bat
   ```

## Configuration
Modify these parameters in `adaptive_dimmer.py`:
```python
# Dimming starts at this brightness (0-255)
THRESHOLD_START = 40

# Maximum dimming at this brightness
THRESHOLD_MAX = 130

# Maximum darkness (0-255, higher = darker)
MAX_OPACITY = 200

# How often to check brightness (seconds)
CHECK_INTERVAL = 0.05
```

## Uploading to GitHub
1. Create a new repository on GitHub (without a README or .gitignore)
2. Run the following commands in the project directory:
   ```
   git init
   git add .
   git commit -m "Initial commit"
   git branch -M main
   git remote add origin <your-repository-url>
   git push -u origin main
   ```

## Why Use This?
Tired of being flashed by bright white screens while watching videos or browsing? This script automatically dims your screen when it gets too bright, protecting your eyes from strain.

## How It Works
1. Measures average screen brightness
2. Calculates needed dimming based on your thresholds
3. Creates a transparent overlay that darkens the screen
4. Adjusts in real-time as content changes

## Requirements
- Windows 7+
- Python 3.6+
- Primary monitor resolution: 1920x1080 (modify code for other resolutions)

> **Note**: For best results, run as Administrator
