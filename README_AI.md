# Adaptive Screen Dimmer — AI Cheat Sheet
Pure Windows/Tkinter app that overlays transparent black windows to dim monitors based on live screen brightness (captured via `mss`). Designed for my own fast parsing and reasoning.

## Core scripts
- `adaptive_dimmer.py`: Main app (GUI + dimmer engine).
- `adaptive_dimmer_START.bat`: Launch helper; prefers built EXE, else runs Python venv.
- `build_exe.bat`: Builds one-file GUI EXE via PyInstaller (creates venv if absent).
- `requirements.txt`: Minimal deps (`mss`, `numpy`, `pywin32`).

## Runtime pipeline (happy path)
1) `main()` -> `DimmerGUI()` -> Tk window + controls -> auto-start after 500 ms.
2) `auto_start()` constructs `AdaptiveDimmer`, sets active monitors (mode combo), starts thread running `AdaptiveDimmer.run()`.
3) `AdaptiveDimmer.run()` builds overlays per active monitor (`create_overlay`), then starts `monitor_loop`.
4) `monitor_loop` (every `CHECK_INTERVAL`=0.05s):
   - `measure_brightness(monitor_id)` grabs screen via `mss`, computes mean luminance.
   - Maps brightness to `target_opacity` using `THRESHOLD_START`/`THRESHOLD_MAX` → caps at `MAX_OPACITY`.
   - `set_overlay_opacity` eases `current_opacity` toward target and calls `SetLayeredWindowAttributes`.
   - Logs status every ~2s; GUI status label updated when present.
5) GUI buttons call `pause_dimmer` / `resume_dimmer`; mode combo triggers `on_mode_change` (recreates overlays, updates active monitor list).
6) On close, threads stop, overlays destroyed.

## Parameters (tune in code)
- `THRESHOLD_START=25`, `THRESHOLD_MAX=100`, `MAX_OPACITY=240 (0-255 alpha)`, `CHECK_INTERVAL=0.05s`.

## Classes & key methods
- `LogCapture(text_widget)` @ `adaptive_dimmer.py`: wraps log stream into Tk text.
  - `write(msg)`: append with timestamp to GUI.
  - `flush()`: no-op.
- `AdaptiveDimmer(gui=None)` @ `adaptive_dimmer.py`: brightness → overlay controller.
  - `log(msg)`: print + GUI log passthrough.
  - `measure_brightness(monitor_id)`: screenshot via `mss`, return mean luminance (float).
  - `set_overlay_opacity(monitor_id, opacity, force_immediate=False)`: ease/cap opacity; apply to layered window.
  - `create_overlay(monitor_id)`: register window class, create full-screen transparent, topmost, click-through overlay for monitor.
  - `monitor_loop()`: main loop (reads brightness, updates targets, logs).
  - `run()`: init overlays, start monitor thread, pump Windows messages; teardown on exit.
- `DimmerGUI` @ `adaptive_dimmer.py`: Tk UI wrapper.
  - `add_log`, `update_status`: append log / refresh status label.
  - `on_mode_change`: swap active monitors; recreate overlays.
  - `auto_start`: kick off dimmer thread with selected monitors.
  - `pause_dimmer` / `resume_dimmer`: toggle `paused`, set opacity to 0 when paused.
  - `on_closing`: stop dimmer, destroy overlays, close Tk.
- `main()`: DPI aware, admin warning, instantiates GUI, enters Tk loop.

## Build & run (for me)
- Build EXE: `./build_exe.bat` → `dist/AdaptiveScreenDimmer.exe`.
- Run existing EXE if built: `./adaptive_dimmer_START.bat`; else runs `.venv\Scripts\pythonw.exe adaptive_dimmer.py`.
- Direct Python: `pip install -r requirements.txt` then `pythonw adaptive_dimmer.py`.

## Failure/edge notes
- `mss` monitor indexing: uses 1-based; falls back to monitor 1 if index invalid.
- Overlay recreate path uses `switching_monitor` guard to avoid deleting while switching.
- Admin rights recommended for reliable topmost overlays; non-admin allowed but warns.
