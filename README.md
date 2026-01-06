# Adaptive-Screen-Dimmer-Windows

Automatically dims your screen when it detects bright content to prevent eye strain and flash blindness.

## Features
- 🛡️ **Eye Protection**: Reduces eye strain from bright screens
- 🖥️ **GUI Interface**: Benutzerfreundliches Kontrollpanel (Englisch/Deutsch)
- 📊 **Live Logs**: View brightness and dimming levels in real-time
- 🖲️ **Multi-Monitor Support**: Choose which monitor to dim
- ⚙️ **Auto-Adjusting**: Dynamically adjusts dimming based on screen brightness
- ⏱️ **Fast Response**: Checks screen brightness every 50ms
- 🔧 **Customizable**: Adjust sensitivity and dimming strength

## Installation
1. Clone this repository or download the .py and .bat File
2. Install requirements:
   ```
   pip install mss numpy pywin32
   ```
3. Run the application:
   ```
   adaptive_dimmer_START.bat
   ```

## Usage
1. **Start Program**: Double-click `adaptive_dimmer_START.bat`
2. **GUI Window Opens**: A control panel appears with:
   - **Bildschirm Auswahl**: Select which monitor to dim (for multi-monitor setups)
   - **Status**: Current brightness and dimming level
   - **Logs**: Real-time log output from the dimmer
   - **START Button**: Begin automatic dimming
   - **STOP Button**: Stop dimming and hide overlay

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

## Why Use This?
Tired of being flashed by bright screens while watching videos or browsing? This script automatically dims your screen when it gets too bright, protecting your eyes from strain.

## How It Works
1. GUI opens with control panel
2. Select target monitor
3. Press START to begin monitoring
4. Measures average screen brightness every 50ms
5. Calculates needed dimming based on your thresholds
6. Creates a transparent overlay that darkens the screen
7. Adjusts in real-time as content changes
8. Logs all activity in the GUI window

## Requirements
- Windows 7+
- Python 3.6+



## 🤝 Contributing

Contributions are welcome! Please open an issue or submit a pull request for any improvements.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
