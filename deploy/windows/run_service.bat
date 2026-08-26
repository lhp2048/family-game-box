@echo off
setlocal EnableExtensions
call "%~dp0resolve_app_root.bat"
if errorlevel 1 exit /b 1
if not defined PORT set "PORT=18029"
set "PY=%APP_ROOT%\.venv\Scripts\python.exe"
if not exist "%PY%" exit /b 1
cd /d "%APP_ROOT%"
start "" /B "%PY%" -m uvicorn app.main:app --host 0.0.0.0 --port %PORT%
exit /b 0
