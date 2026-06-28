@echo off
REM Steam Manifest Key Spoofer - Windows Launcher

set SCRIPT_DIR=%~dp0
set REPO_ROOT=%SCRIPT_DIR%..

where python >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python 3 is required
    pause
    exit /b 1
)

pip install rich pyfiglet >nul 2>&1

cd /d "%SCRIPT_DIR%"
python tui.py %*
pause
