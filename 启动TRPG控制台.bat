@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

set "PYTHONPATH=%~dp0src"
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
set "TRPG_CHATGPT_AUTOMATION=browser_harness"
set "TRPG_BROWSER_USER_DATA_DIR=%~dp0.browser-profile"
set "TRPG_BROWSER_CHANNEL=chrome"
set "TRPG_WEB_HOST=127.0.0.1"
set "TRPG_WEB_PORT=8787"

echo Starting TRPG Orchestrator Web Console...
echo http://127.0.0.1:8787/

set "PYTHON_CMD="
where py >nul 2>nul
if not errorlevel 1 (
    py -3 --version >nul 2>nul
    if not errorlevel 1 set "PYTHON_CMD=py -3"
)

if not defined PYTHON_CMD (
    python --version >nul 2>nul
    if not errorlevel 1 set "PYTHON_CMD=python"
)

if not defined PYTHON_CMD (
    echo.
    echo ERROR: Python 3.11+ was not found.
    echo The Windows python app execution alias is not enough to run this project.
    echo Install Python from https://www.python.org/downloads/windows/ and enable "Add python.exe to PATH".
    echo Then run:
    echo   python -m pip install -e .
    echo.
    pause
    exit /b 1
)

%PYTHON_CMD% -m trpg_orchestrator.web_server

pause
