@echo off
cd /d "%~dp0"
where python >nul 2>nul
if errorlevel 1 (
  echo Python is not installed. Install it from https://www.python.org/downloads/ ^(tick "Add python.exe to PATH"^), then run this file again.
  pause
  exit /b 1
)
python -m pip install --upgrade pip
python -m pip install PyQt6
if errorlevel 1 (
  echo Dependency install failed.
  pause
  exit /b 1
)
start "" pythonw "%~dp0livewallpaper.py"
echo Live Wallpaper started. Look for the blue icon in the system tray.
timeout /t 4 >nul
