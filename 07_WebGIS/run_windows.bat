@echo off
cd /d "%~dp0"
if not exist .venv (py -m venv .venv)
call .venv\Scripts\activate.bat
python -m pip install -r requirements.txt || (pause & exit /b 1)
python run_webgis.py
pause
