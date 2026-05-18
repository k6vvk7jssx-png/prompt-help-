@echo off
setlocal

cd /d "%~dp0"

set "PYTHON_CMD="

if exist ".venv\Scripts\python.exe" (
    "%~dp0.venv\Scripts\python.exe" --version >nul 2>nul
    if not errorlevel 1 (
        set "PYTHON_CMD=%~dp0.venv\Scripts\python.exe"
    )
)

if "%PYTHON_CMD%"=="" if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" (
    set "PYTHON_CMD=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
)

if "%PYTHON_CMD%"=="" if exist "%LOCALAPPDATA%\Programs\Python\Python314\python.exe" (
    set "PYTHON_CMD=%LOCALAPPDATA%\Programs\Python\Python314\python.exe"
)

if "%PYTHON_CMD%"=="" (
    echo Python was not found.
    echo Run setup.bat first or reinstall Python with PATH enabled.
    pause
    exit /b 1
)

if not exist ".env" (
    echo .env file not found.
    echo Run setup.bat first, then add your DeepSeek API key to .env.
    pause
    exit /b 1
)

"%PYTHON_CMD%" prompt_optimizer.py
pause
