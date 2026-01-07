# Adaptive Screen Dimmer (Windows)

Automatically dims your screen when content gets too bright to reduce eye strain and flash blindness. Includes a simple GUI and multi‑monitor support.

## Features
- 🛡️ Eye protection: Smooth overlay dimming based on brightness
- 🖥️ GUI: Simple dark UI with logs and status
- 🖲️ Multi‑monitor: Monitor 1, Monitor 2, or both
- ⚙️ Auto‑adjust: Continuously adapts between thresholds
- ⏱️ Fast: Checks brightness every ~50ms
- ⏸ Pause/Resume: Quick control without closing the app

## Quick Start
You can run either the locally built EXE or the Python script. We do not ship prebuilt binaries.

### Option A: Build EXE locally
1. Ensure Python 3.10+ is installed.
2. Build the EXE:
   ```powershell
   ./build_exe.bat
   ```
3. Start the executable: [dist/AdaptiveScreenDimmer.exe](dist/AdaptiveScreenDimmer.exe)
   - Tip: Right‑click → “Run as administrator” can improve overlay reliability.

### Option B: Python
1. Install requirements:
   ```powershell
   pip install -r requirements.txt
   ```
2. Start via batch:
   ```powershell
   .\adaptive_dimmer_START.bat
   ```
   or directly:
   ```powershell
   pythonw adaptive_dimmer.py
   ```

## Building the EXE
This project uses PyInstaller to create a one‑file GUI executable. We do not provide prebuilt EXE files; build it locally on your machine.

```powershell
./build_exe.bat
```

The build output is placed in [dist/AdaptiveScreenDimmer.exe](dist/AdaptiveScreenDimmer.exe). After building, you can copy this EXE anywhere; it runs without needing Python installed.

### Notes on repository contents
- Do not commit build artifacts like `dist/` or `build/` – they are ignored via [.gitignore](.gitignore).
- If you need to share the EXE, build locally and distribute it outside the repository (e.g., attach to a release).

## Usage
- On launch, the app auto‑starts and begins monitoring.
- Select mode: “Nur Monitor 1”, “Nur Monitor 2”, or “Beide Bildschirme”.
- Use “⏸ Pausieren” / “▶ Fortsetzen” to control dimming.
- Status shows current brightness and dimming percentage; logs display detailed activity.

## Configuration
Adjust parameters in [adaptive_dimmer.py](adaptive_dimmer.py):
```python
THRESHOLD_START = 25   # Dimming begins above this brightness
THRESHOLD_MAX = 100    # Maximum dimming reached above this brightness
MAX_OPACITY = 240      # 0–255 alpha (higher = darker)
CHECK_INTERVAL = 0.05  # Seconds between brightness checks
```

## Requirements
- Windows 10/11 recommended (Windows 7+ may work)
- For Python mode: Python 3.10+ recommended

## Notes & Tips
- Administrator mode may be required for reliable top‑most overlays in some setups.
- If overlays do not appear on a monitor, switch the mode and back again.
- Multi‑monitor coordinates are read via `mss`; unusual DPI/arrangements may need admin.

## Contributing
PRs and issues are welcome.

## License
MIT License — see [LICENSE](LICENSE).
