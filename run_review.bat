@echo off
cd /d C:\Users\Lenovo\nexus
call venv\Scripts\activate.bat
set PYTHONUTF8=1
python -c "from scheduler import evening_review; evening_review()" >> runs_scheduled.log 2>&1
