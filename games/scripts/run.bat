@echo off
setlocal
set CHROME=D:\app\Chrome\chrome.exe
cd /d "%~dp0.."

if not exist "dist\index.html" (
  if exist "output\index.html" (
    set PAGE=%cd%\output\index.html
  ) else (
    echo [ERROR] no dist\index.html — run scripts\build.bat first
    exit /b 1
  )
) else (
  set PAGE=%cd%\dist\index.html
)

if exist "%CHROME%" (
  start "" "%CHROME%" "%PAGE%"
) else (
  start "" "%PAGE%"
)
exit /b 0
