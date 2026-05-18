@echo off
setlocal

cd /d "%~dp0"

set "PYTHONW_CMD="

if exist ".venv\Scripts\pythonw.exe" (
    "%~dp0.venv\Scripts\pythonw.exe" --version >nul 2>nul
    if not errorlevel 1 (
        set "PYTHONW_CMD=%~dp0.venv\Scripts\pythonw.exe"
    )
)

if "%PYTHONW_CMD%"=="" if exist "%LOCALAPPDATA%\Programs\Python\Python312\pythonw.exe" (
    set "PYTHONW_CMD=%LOCALAPPDATA%\Programs\Python\Python312\pythonw.exe"
)

if "%PYTHONW_CMD%"=="" if exist "%LOCALAPPDATA%\Programs\Python\Python314\pythonw.exe" (
    set "PYTHONW_CMD=%LOCALAPPDATA%\Programs\Python\Python314\pythonw.exe"
)

if "%PYTHONW_CMD%"=="" (
    echo Valid virtual environment not found.
    echo Run setup.bat first.
    pause
    exit /b 1
)

if not exist ".env" (
    echo .env file not found.
    echo Run setup.bat first, then add your DeepSeek API key to .env.
    pause
    exit /b 1
)

start "" "%PYTHONW_CMD%" "%~dp0prompt_optimizer.py"
