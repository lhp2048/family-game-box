@echo off
setlocal EnableExtensions
call "%~dp0resolve_app_root.bat"
if errorlevel 1 exit /b 1

set "PY_BOOTSTRAP="
for %%P in (python3.12 python3.11 python3.10 python3 py -3.12) do (
  where %%P >nul 2>&1
  if not errorlevel 1 (
    for /f "delims=" %%V in ('%%P -c "import sys; print(sys.version_info >= (3,10))" 2^>nul') do (
      if "%%V"=="True" set "PY_BOOTSTRAP=%%P"
    )
  )
  if defined PY_BOOTSTRAP goto :have_py
)
echo ERROR: Python 3.10+ required
exit /b 1

:have_py
if exist "%APP_ROOT%\.venv\Scripts\python.exe" (
  "%APP_ROOT%\.venv\Scripts\python.exe" -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>&1
  if errorlevel 1 rmdir /s /q "%APP_ROOT%\.venv"
)
if not exist "%APP_ROOT%\.venv\Scripts\python.exe" (
  %PY_BOOTSTRAP% -m venv "%APP_ROOT%\.venv"
)
set "PY=%APP_ROOT%\.venv\Scripts\python.exe"
"%PY%" -m pip install -U pip -q
"%PY%" -m pip install -r "%APP_ROOT%\requirements.txt" -q
"%PY%" -c "import uvicorn; from app.main import app" >nul 2>&1
if errorlevel 1 exit /b 1
if not exist "%APP_ROOT%\logs" mkdir "%APP_ROOT%\logs"
if not exist "%APP_ROOT%\.env" if exist "%APP_ROOT%\.env.example" copy /Y "%APP_ROOT%\.env.example" "%APP_ROOT%\.env" >nul
exit /b 0
