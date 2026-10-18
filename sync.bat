@echo off
REM SmartDrive - save all changes to GitHub (double-click, or run: sync.bat "what changed")
cd /d "%~dp0"
set "MSG=%~1"
if "%MSG%"=="" set /p "MSG=Describe your changes (Enter for default): "
if "%MSG%"=="" set "MSG=Update SmartDrive"
git add -A
git commit -m "%MSG%"
git push
pause
