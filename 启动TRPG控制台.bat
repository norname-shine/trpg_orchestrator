@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

set "PYTHONPATH=%~dp0src"
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
set "TRPG_CHATGPT_AUTOMATION=playwright"
set "TRPG_BROWSER_USER_DATA_DIR=%~dp0.browser-profile"
set "TRPG_BROWSER_CHANNEL=chrome"
set "TRPG_WEB_HOST=127.0.0.1"
set "TRPG_WEB_PORT=8787"

echo Starting TRPG Orchestrator Web Console...
echo http://127.0.0.1:8787/
python -m trpg_orchestrator.web_server

pause
