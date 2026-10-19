@echo off
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\setup_windows.ps1"
if errorlevel 1 (
 echo.
 echo Setup did not finish. Read the error above, then run setup again.
)
pause
