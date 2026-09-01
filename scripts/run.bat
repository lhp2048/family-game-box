@echo off
setlocal EnableExtensions
set "ROOT=%~dp0.."
set "PYTHON=C:\Program Files\Python\Python312\python.exe"
set "CHROME=D:\app\Chrome\chrome.exe"
cd /d "%ROOT%"

if not exist "%PYTHON%" set "PYTHON=C:\Python310\python.exe"
if exist "%ROOT%\.venv\Scripts\python.exe" set "PYTHON=%ROOT%\.venv\Scripts\python.exe"

if not exist "%PYTHON%" (
  echo [ERROR] Python not found. Expected localdevs.txt path or C:\Python310\python.exe
  exit /b 1
)

echo Family Game Box
echo Root: %CD%
echo URL:  http://127.0.0.1:18029/game-box/
echo Health: http://127.0.0.1:18029/api/v1/health
echo Press Ctrl+C to stop
echo.

if exist "%CHROME%" (
  start "" "%CHROME%" "http://127.0.0.1:18029/game-box/"
) else (
  start "" "http://127.0.0.1:18029/game-box/"
)

"%PYTHON%" -m uvicorn app.main:app --host 0.0.0.0 --port 18029
exit /b %ERRORLEVEL%
