@echo off
setlocal

cd /d "%~dp0"

if not exist ".venv\Scripts\pythonw.exe" (
    echo Virtual environment not found.
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

start "" ".venv\Scripts\pythonw.exe" "%~dp0prompt_optimizer.py"
