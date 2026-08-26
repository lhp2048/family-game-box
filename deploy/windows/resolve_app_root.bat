@echo off
rem Sets APP_ROOT to directory containing app\main.py
cd /d "%~dp0.."
if exist "app\main.py" (
  set "APP_ROOT=%CD%"
) else (
  cd ..
  if not exist "app\main.py" (
    echo ERROR: app\main.py not found
    exit /b 1
  )
  set "APP_ROOT=%CD%"
)
exit /b 0
