@echo off
title ScrapperGov - Auto Updating Server
echo.
echo  ============================================
echo   ScrapperGov - SAM.gov Contract Finder
echo   (Auto-Updater Enabled)
echo  ============================================
echo.

:: Check venv exists
if not exist ".venv\Scripts\activate.bat" (
    echo  [ERROR] Virtual environment not found.
    echo  Please run setup.bat first.
    echo.
    pause
    exit /b 1
)

:: Activate venv
call .venv\Scripts\activate.bat

:: Check .env
if not exist ".env" (
    echo  [WARNING] .env file not found. Creating default...
    echo SAM_API_KEY=DEMO_KEY> .env
    echo  Please edit .env and add your SAM.gov API key.
    echo.
)

:loop
echo  Checking for updates...
git pull

echo  Installing/Updating dependencies...
pip install -r requirements.txt --quiet

echo.
echo  Starting server at http://localhost:5000
echo  Press Ctrl+C to stop.
echo.

python server.py

:: Check the exit code of python server.py
if %errorlevel% equ 42 (
    echo.
    echo  ============================================
    echo   [UPDATE DETECTED] Restarting server...
    echo  ============================================
    echo.
    timeout /t 3 /nobreak >nul
    goto loop
)

echo.
echo  Server stopped.
pause
