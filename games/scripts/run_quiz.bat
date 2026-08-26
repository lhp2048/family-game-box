@echo off
setlocal
set CHROME=D:\app\Chrome\chrome.exe
cd /d "%~dp0.."

set PAGE=%cd%\dist\quiz.html
if not exist "%PAGE%" set PAGE=%cd%\output\quiz.html
if not exist "%PAGE%" (
  echo [ERROR] quiz.html missing — run scripts\build.bat first
  exit /b 1
)

if exist "%CHROME%" (
  start "" "%CHROME%" "%PAGE%"
) else (
  start "" "%PAGE%"
)
exit /b 0
