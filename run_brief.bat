@echo off
cd /d "%~dp0"
if exist "%~dp0venv\Scripts\activate.bat" call "%~dp0venv\Scripts\activate.bat"
set PYTHONUTF8=1
python -m nexus brief >> runs_scheduled.log 2>&1
