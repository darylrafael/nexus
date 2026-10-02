@echo off
cd /d "%~dp0"
git pull --no-edit -X ours origin main >nul 2>&1
call "%~dp0venv\Scripts\activate.bat"
set PYTHONUTF8=1
python -c "from scheduler import daily_brief; daily_brief()" >> runs_scheduled.log 2>&1
