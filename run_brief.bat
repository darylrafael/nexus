@echo off
cd /d C:\Users\Lenovo\nexus
call venv\Scripts\activate.bat
set PYTHONUTF8=1
python -c "from scheduler import daily_brief; daily_brief()" >> runs_scheduled.log 2>&1
