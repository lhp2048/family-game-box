@echo off
setlocal
set PYTHON=C:\Program Files\Python\Python312\python.exe
cd /d "%~dp0.."
"%PYTHON%" solve_24.py --min 0 --max 24 --out output
exit /b %ERRORLEVEL%
