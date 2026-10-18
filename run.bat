@echo off
REM SmartDrive - one-click start for Windows (double-click this file)
cd /d "%~dp0"
python -m pip install -q -r requirements.txt
python server.py
pause
