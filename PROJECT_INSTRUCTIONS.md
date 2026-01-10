# Project Instructions - Adaptive Screen Dimmer

## Development Workflow

### Testing After Code Changes
After making any code changes, always follow these steps:

1. **Activate Virtual Environment**
   ```powershell
   .venv\Scripts\Activate.ps1
   ```

2. **Run the Application**
   ```powershell
   py adaptive_dimmer.py
   ```

3. **Verify**
   - Check if the code compiles without errors
   - Verify the application doesn't crash
   - Test the functionality you modified

### Important Notes
- Always test before considering a task complete
- Watch for both compilation errors and runtime crashes
- Check console output for error messages
- Verify GUI loads and functions correctly

### Project Structure
- **Main entry point**: `adaptive_dimmer.py` (starts the application)
- **Helper modules**: `HelperScripts/` directory
  - `config.py` - Configuration constants and theme settings
  - `logger.py` - Logging utilities (console & file logging)
  - `brightness.py` - Brightness measurement utilities
  - `overlay.py` - Overlay window management
  - `dimmer.py` - Core dimmer logic and monitoring loop
  - `gui_components.py` - Chart and monitor selector components
  - `gui.py` - Main GUI window class
- **Python environment**: `.venv`
- **Log output**: `dimmer_log.txt` (brightness data), `shutdown_log.txt` (shutdown debug log)

### Module Responsibilities
- **config.py**: All constants (thresholds, colors, timings)
- **logger.py**: All logging functionality
- **brightness.py**: Brightness measurement and calculations
- **overlay.py**: Win32 overlay window creation and management
- **dimmer.py**: Main dimmer logic, monitoring loop, opacity calculations
- **gui_components.py**: Reusable GUI components (ChartManager, MonitorSelector)
- **gui.py**: Main window, event handlers, UI layout

### Common Testing Scenarios
- Monitor detection and overlay creation
- Brightness measurement and dimming logic
- GUI controls (pause/resume, monitor selection, dim strength)
- Multi-monitor support
- Chart/graph updates

### Encoding Note
- All Python files must use UTF-8 encoding
- Avoid German umlauts in code to prevent encoding issues
