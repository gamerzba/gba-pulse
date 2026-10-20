@echo off
setlocal
cd /d "%~dp0"

echo ==============================================
echo   G.ba Pulse - Windows build
echo ==============================================

if not exist ".venv\Scripts\python.exe" (
  py -3 -m venv .venv
  if errorlevel 1 goto :error
)

call ".venv\Scripts\activate.bat"
python -m pip install --upgrade pip
if errorlevel 1 goto :error
python -m pip install -r requirements.txt
if errorlevel 1 goto :error

python -m PyInstaller --noconfirm --clean --windowed --name GbaPulse --icon "assets\gba_pulse_mark.ico" --add-data "assets;assets" --collect-all PySide6.QtWebEngineCore --collect-all PySide6.QtWebEngineWidgets --hidden-import PySide6.QtSvg main.py
if errorlevel 1 goto :error

echo.
echo Build finished. EXE should be at dist\GbaPulse\GbaPulse.exe
pause
exit /b 0

:error
echo.
echo Build failed. Read the error above.
pause
exit /b 1
