@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

set "PYTHONPATH=%~dp0src"
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
set "PYTHONDONTWRITEBYTECODE=1"

echo Running pre-upload cleanup...
python -m trpg_orchestrator.cli pre-upload-clean
if errorlevel 1 (
    echo.
    echo [ERROR] Pre-upload cleanup found blocked runtime or private paths.
    pause
    exit /b 1
)

echo.
echo Validating repository encoding...
python -m trpg_orchestrator.cli validate-encoding
if errorlevel 1 (
    echo.
    echo [ERROR] Encoding validation failed.
    pause
    exit /b 1
)

echo.
echo Git status:
git status --short

echo.
echo Pre-upload cleanup complete.
pause
