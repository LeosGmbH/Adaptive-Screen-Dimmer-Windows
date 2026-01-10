# Helper Scripts - Adaptive Screen Dimmer

This directory contains the modularized components of the Adaptive Screen Dimmer application.

## Module Overview

### `config.py`
**Purpose**: Centralized configuration and constants

**Contains**:
- Brightness thresholds (`THRESHOLD_START`, `THRESHOLD_MAX`)
- Opacity settings (`MAX_OPACITY`)
- Timing constants (`CHECK_INTERVAL`)
- GUI settings (window geometry, chart settings)
- Theme colors and chart color pairs

**When to modify**: When changing application constants, thresholds, or theme colors

---

### `logger.py`
**Purpose**: Logging functionality

**Contains**:
- `Logger` class for console and file logging
- Brightness data logging to CSV
- Shutdown debug logging

**Key methods**:
- `open_log_file()` - Opens brightness log file
- `log(message)` - Console logging
- `write_shutdown_log(message)` - Debug shutdown logging
- `log_brightness_data(entries)` - Log brightness to file

---

### `brightness.py`
**Purpose**: Brightness measurement and calculations

**Contains**:
- `BrightnessMeasurer` class
- Screen capture and brightness calculation
- Raw brightness estimation (compensating for overlay)
- Dimmed brightness calculation

**Key methods**:
- `measure_brightness(monitor_id)` - Capture and measure brightness
- `calculate_raw_estimate(measured, opacity)` - Calculate raw brightness
- `calculate_dimmed_brightness(raw, opacity)` - Calculate dimmed value

---

### `overlay.py`
**Purpose**: Win32 overlay window management

**Contains**:
- `OverlayManager` class
- Transparent fullscreen overlay creation
- Opacity control
- Multi-monitor support

**Key methods**:
- `create_overlay(monitor_id)` - Create transparent overlay window
- `set_overlay_opacity(monitor_id, opacity)` - Set overlay transparency
- `destroy_overlay(monitor_id)` - Remove overlay
- `destroy_all_overlays()` - Cleanup all overlays

---

### `dimmer.py`
**Purpose**: Core dimmer logic and monitoring

**Contains**:
- `AdaptiveDimmer` class
- Main monitoring loop
- Brightness-to-opacity calculation
- Thread management

**Key methods**:
- `monitor_loop()` - Main monitoring thread
- `calculate_target_opacity(brightness, strength)` - Calculate opacity from brightness
- `run()` - Start dimmer (creates overlays, starts monitoring)

**Dependencies**: Uses `logger`, `brightness`, and `overlay` modules

---

### `gui_components.py`
**Purpose**: Reusable GUI components

**Contains**:
- `ChartManager` class - Live brightness chart display
- `MonitorSelector` class - Monitor selection checkboxes

**ChartManager methods**:
- `sync_monitors(monitors)` - Update chart for active monitors
- `push_brightness(monitor_id, raw, dimmed)` - Add brightness data point
- `redraw()` - Update chart display

**MonitorSelector methods**:
- `refresh()` - Detect and create monitor checkboxes
- `get_selected()` - Get list of selected monitors
- `set_selected(monitor_ids)` - Set which monitors are selected

---

### `gui.py`
**Purpose**: Main GUI window and event handling

**Contains**:
- `DimmerGUI` class
- UI layout and widgets
- Event handlers (pause, resume, monitor toggle)
- Integration of all components

**Key methods**:
- `_build_ui()` - Create GUI layout
- `on_monitor_toggle()` - Handle monitor selection changes
- `pause_dimmer()` / `resume_dimmer()` - Control dimmer state
- `on_closing()` - Clean shutdown

**Dependencies**: Uses all other modules

---

## Data Flow

```
main (adaptive_dimmer.py)
  ??> DimmerGUI (gui.py)
       ??> MonitorSelector (gui_components.py) - User selects monitors
       ??> ChartManager (gui_components.py) - Displays brightness data
       ??> AdaptiveDimmer (dimmer.py)
            ??> Logger (logger.py) - Logs data
            ??> BrightnessMeasurer (brightness.py) - Measures brightness
            ??> OverlayManager (overlay.py) - Controls screen overlays
```

## Adding New Features

1. **New configuration constant**: Add to `config.py`
2. **New brightness calculation**: Add to `brightness.py`
3. **New logging feature**: Add to `logger.py`
4. **New GUI widget**: Add to `gui_components.py`
5. **New overlay behavior**: Modify `overlay.py`
6. **New dimming logic**: Modify `dimmer.py`
7. **New user interaction**: Modify `gui.py`

## Testing Checklist

When modifying any module, test:
- [ ] Application starts without errors
- [ ] Monitors are detected correctly
- [ ] Overlays create and position correctly
- [ ] Brightness measurement works
- [ ] Chart updates properly
- [ ] Pause/Resume functions
- [ ] Monitor toggle works
- [ ] Clean shutdown (check `shutdown_log.txt`)
