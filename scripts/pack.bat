@echo off
setlocal EnableExtensions
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%.."
set "ROOT=%CD%"
set "DIST=%ROOT%\dist"
set "OUT_DIR=%ROOT%\dist_out"
for %%I in ("%ROOT%\..\family_smart_center_web\scripts") do set "PORTAL_SCRIPTS=%%~fI"

if not exist "%DIST%\app\main.py" (
  echo ERROR: run scripts\build.bat first
  exit /b 1
)

set "PYTHON=python"
if exist "%ROOT%\.venv\Scripts\python.exe" set "PYTHON=%ROOT%\.venv\Scripts\python.exe"
if exist "C:\Program Files\Python\Python312\python.exe" set "PYTHON=C:\Program Files\Python\Python312\python.exe"
if exist "C:\Python310\python.exe" set "PYTHON=C:\Python310\python.exe"

"%PYTHON%" "%PORTAL_SCRIPTS%\bump_manifest_version.py" --manifest "%ROOT%\family-product.json" --dist "%DIST%"
"%PYTHON%" "%PORTAL_SCRIPTS%\validate_manifest.py" "%ROOT%\family-product.json" --dist "%DIST%"
if errorlevel 1 exit /b 1

rem Avoid for /f with quoted full python path (CMD syntax error on Windows)
set "ZIP_NAME=family_game_box.zip"
set "ZIP_NAME_TMP=%TEMP%\family_game_box_zipname_%RANDOM%.txt"
"%PYTHON%" "%PORTAL_SCRIPTS%\read_manifest_field.py" "%ROOT%\family-product.json" zipNameHint family_game_box.zip > "%ZIP_NAME_TMP%"
if not errorlevel 1 (
  set /p ZIP_NAME=<"%ZIP_NAME_TMP%"
)
del /f /q "%ZIP_NAME_TMP%" >nul 2>nul

set "ZIP_FILE=%OUT_DIR%\%ZIP_NAME%"
if not exist "%OUT_DIR%" mkdir "%OUT_DIR%"
if exist "%ZIP_FILE%" del /f /q "%ZIP_FILE%"

"%PYTHON%" "%PORTAL_SCRIPTS%\make_zip.py" "%DIST%" "%ZIP_FILE%"
"%PYTHON%" "%PORTAL_SCRIPTS%\write_package_info.py" --manifest "%ROOT%\family-product.json" --zip "%ZIP_FILE%" --dist "%DIST%" --out-dir "%OUT_DIR%"

echo Packed: %ZIP_FILE%
endlocal
