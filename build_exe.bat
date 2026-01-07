@echo off
setlocal

REM Create venv if missing
if not exist .venv (
  py -3 -m venv .venv
)

call .venv\Scripts\activate.bat

python -m pip install --upgrade pip
pip install -r requirements.txt
pip install pyinstaller

REM Build onefile GUI exe
python -m PyInstaller --noconfirm --clean --onefile --noconsole --name AdaptiveScreenDimmer ^
  --hidden-import=tkinter --hidden-import=tkinter.ttk ^
  adaptive_dimmer.py

if exist dist\AdaptiveScreenDimmer.exe (
  echo Build successful: dist\AdaptiveScreenDimmer.exe
) else (
  echo Build failed.
  exit /b 1
)

endlocal