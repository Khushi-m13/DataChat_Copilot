@echo off
cd /d "%~dp0"
if not exist venv\Scripts\activate.bat (
  echo Setup not done yet. Double-click install.bat first.
  pause
  exit /b 1
)
call venv\Scripts\activate.bat
if exist .env echo Loading Gemini API key from .env
echo Starting DataChat Copilot...
streamlit run app.py
pause
