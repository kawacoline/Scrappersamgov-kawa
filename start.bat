@echo off
title ScrapperGov - Running
echo.
echo  ============================================
echo   ScrapperGov - SAM.gov Contract Finder
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

echo  Starting server at http://localhost:5000
echo  Press Ctrl+C to stop.
echo.

python server.py

pause
