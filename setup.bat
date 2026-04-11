@echo off
title ScrapperGov - Setup
echo.
echo  ============================================
echo   ScrapperGov - Environment Setup
echo  ============================================
echo.

:: Check for Python
python --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo  [ERROR] Python is not installed or not in PATH.
    echo  Please install Python 3.10+ from https://python.org
    echo.
    pause
    exit /b 1
)

echo  [1/3] Creating virtual environment...
if exist ".venv" (
    echo        .venv already exists, skipping creation.
) else (
    python -m venv .venv
    if %ERRORLEVEL% neq 0 (
        echo  [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
    echo        Done.
)

echo  [2/3] Activating virtual environment...
call .venv\Scripts\activate.bat
if %ERRORLEVEL% neq 0 (
    echo  [ERROR] Failed to activate virtual environment.
    pause
    exit /b 1
)
echo        Done.

echo  [3/3] Installing dependencies...
pip install -r requirements.txt --quiet
if %ERRORLEVEL% neq 0 (
    echo  [ERROR] Failed to install dependencies.
    pause
    exit /b 1
)
echo        Done.

echo.
echo  ============================================
echo   Setup Complete!
echo  ============================================
echo.
echo  NEXT STEPS:
echo    1. Get your SAM.gov API key:
echo       - Log in to https://sam.gov
echo       - Go to Account Details
echo       - Generate a Public API Key
echo.
echo    2. Open .env and replace DEMO_KEY with your key
echo.
echo    3. Run start.bat to launch the app
echo.
pause
