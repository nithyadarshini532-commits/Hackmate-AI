@echo off
title HackMate AI Launcher
echo ===================================================
echo Starting HackMate AI...
echo App will open in your browser at http://localhost:8501
echo ===================================================
call "C:\Users\Admin\.gemini\antigravity\scratch\hackmate-ai\.venv\Scripts\activate.bat"
streamlit run app.py
pause
