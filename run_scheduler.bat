@echo off
title Nexus Scheduler
cd /d C:\Users\Lenovo\nexus

echo [%date% %time%] Nexus scheduler starting... >> scheduler.log 2>&1
call venv\Scripts\activate.bat
python scheduler.py >> scheduler.log 2>&1
echo [%date% %time%] Nexus scheduler exited. >> scheduler.log 2>&1
