@echo off
title Nexus Scheduler
cd /d "%~dp0"

echo [%date% %time%] Nexus scheduler starting... >> scheduler.log 2>&1
if exist "%~dp0venv\Scripts\activate.bat" call "%~dp0venv\Scripts\activate.bat"
python -m nexus serve >> scheduler.log 2>&1
echo [%date% %time%] Nexus scheduler exited. >> scheduler.log 2>&1
