@echo off
cd /d "%~dp0"
echo Installing required packages...
py -m pip install -r requirements.txt
if errorlevel 1 (
  echo.
  echo Installation failed. Check that Python is installed and added to PATH.
  pause
  exit /b 1
)
echo.
echo Starting Attendance Manager Pro...
py main.py
if errorlevel 1 pause
