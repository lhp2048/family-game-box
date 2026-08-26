@echo off
setlocal EnableExtensions
call "%~dp0resolve_app_root.bat"
if errorlevel 1 exit /b 1
set "TASK_NAME=FamilyGameBox"
set "START_SCRIPT=%APP_ROOT%\scripts\run_service.bat"
if not exist "%START_SCRIPT%" set "START_SCRIPT=%~dp0run_service.bat"
if not defined PORT set "PORT=18029"

if /i "%~1"=="--uninstall" goto :uninstall
if /i "%~1"=="--status" goto :status

if not exist "%APP_ROOT%\app\main.py" (
  echo ERROR: app\main.py not found
  exit /b 1
)
call "%~dp0setup_venv.bat"
if errorlevel 1 exit /b 1
cd /d "%APP_ROOT%"
"%APP_ROOT%\.venv\Scripts\python.exe" -c "import re;from pathlib import Path;p=Path('.env');t=p.read_text(encoding='utf-8') if p.is_file() else '';t=re.sub(r'(?m)^\s*PORT\s*=.*','PORT=%PORT%',t,count=1) if re.search(r'(?m)^\s*PORT\s*=',t) else (t.rstrip()+'\n' if t else '')+'PORT=%PORT%\n';p.write_text(t,encoding='utf-8');print('PORT=%PORT%')"
call "%~dp0stop_service_win.bat"
schtasks /Create /TN "%TASK_NAME%" /TR "\"%START_SCRIPT%\"" /SC ONLOGON /RL LIMITED /F
call "%~dp0run_service.bat"
timeout /t 3 /nobreak >nul
echo Installed: %TASK_NAME%
echo Local: http://127.0.0.1:%PORT%/
echo Health: http://127.0.0.1:%PORT%/api/v1/health
exit /b 0

:status
schtasks /Query /TN "%TASK_NAME%" >nul 2>&1 && schtasks /Query /TN "%TASK_NAME%" /FO LIST || echo Task not installed
netstat -ano | findstr ":%PORT%" | findstr "LISTENING"
exit /b 0

:uninstall
schtasks /Delete /TN "%TASK_NAME%" /F >nul 2>&1
call "%~dp0stop_service_win.bat"
echo Uninstalled: %TASK_NAME%
exit /b 0
