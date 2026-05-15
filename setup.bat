@echo off
setlocal

cd /d "%~dp0"

set "PYTHON_CMD="

where python >nul 2>nul
if not errorlevel 1 (
    set "PYTHON_CMD=python"
)

if "%PYTHON_CMD%"=="" if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" (
    set "PYTHON_CMD=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
)

if "%PYTHON_CMD%"=="" if exist "%LOCALAPPDATA%\Programs\Python\Python314\python.exe" (
    set "PYTHON_CMD=%LOCALAPPDATA%\Programs\Python\Python314\python.exe"
)

if "%PYTHON_CMD%"=="" (
    echo Python was not found.
    echo Install Python 3.11 or newer from https://www.python.org/downloads/windows/
    echo During install, enable "Add python.exe to PATH".
    pause
    exit /b 1
)

if not exist ".venv" (
    "%PYTHON_CMD%" -m venv .venv
    if errorlevel 1 (
        echo Failed to create virtual environment.
        pause
        exit /b 1
    )
)

call ".venv\Scripts\activate.bat"
python -m pip install --upgrade pip
pip install -r requirements.txt
if errorlevel 1 (
    echo Failed to install dependencies.
    pause
    exit /b 1
)

if not exist ".env" (
    copy ".env.example" ".env" >nul
    echo Created .env from .env.example.
    echo Open .env and add your DEEPSEEK_API_KEY before running the app.
) else (
    echo .env already exists.
)

echo.
echo Setup complete.
echo Edit .env, add your DeepSeek API key, then run run.bat.
pause
