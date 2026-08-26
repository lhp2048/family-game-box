@echo off
setlocal
set CHROME=D:\app\Chrome\chrome.exe
cd /d "%~dp0.."

set PAGE=%cd%\dist\web\games\24points\play.html
if not exist "%PAGE%" set PAGE=%cd%\web\games\24points\play.html
if not exist "%PAGE%" set PAGE=%cd%\output\play.html
if not exist "%PAGE%" (
  echo [ERROR] play.html missing — run scripts\build.bat first
  exit /b 1
)

if exist "%CHROME%" (
  start "" "%CHROME%" "%PAGE%"
) else (
  start "" "%PAGE%"
)
exit /b 0
