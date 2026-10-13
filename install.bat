@echo off
setlocal

echo ==========================================
echo   DataChat Copilot - Gemini Setup
echo ==========================================
echo.

if not exist venv (
    echo Creating Python virtual environment...
    py -m venv venv
    if errorlevel 1 (
        echo.
        echo ERROR: Could not create the virtual environment.
        echo Make sure Python is installed correctly.
        pause
        exit /b 1
    )
)

echo.
echo Activating virtual environment...
call venv\Scripts\activate.bat

echo.
echo Installing project dependencies...
python -m pip install -r requirements.txt

if errorlevel 1 (
    echo.
    echo ==========================================
    echo ERROR: Dependency installation failed.
    echo ==========================================
    pause
    exit /b 1
)

echo.
echo ==========================================
echo   INSTALLATION SUCCESSFUL
echo ==========================================
echo.
echo Next steps:
echo 1. Add your Gemini API key to .env
echo 2. Run run.bat
echo.
pause