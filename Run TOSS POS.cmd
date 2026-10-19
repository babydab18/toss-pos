@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\pythonw.exe" (
 echo Local Python environment missing. See LOCAL-IPAD.md.
 pause
 exit /b 1
)
start "" ".venv\Scripts\pythonw.exe" "scripts\run_local.py"
