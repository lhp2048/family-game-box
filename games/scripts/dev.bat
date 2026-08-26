@echo off
setlocal
set PYTHON=C:\Program Files\Python\Python312\python.exe
set CHROME=D:\app\Chrome\chrome.exe
cd /d "%~dp0.."

call "%~dp0build.bat"
if errorlevel 1 exit /b 1

if exist "%CHROME%" (
  start "" "%CHROME%" "%cd%\dist\index.html"
) else (
  start "" "%cd%\dist\index.html"
)
exit /b 0
