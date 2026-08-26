@echo off

setlocal EnableExtensions

set "SCRIPT_DIR=%~dp0"

set "ROOT=%SCRIPT_DIR%.."

set "DIST=%ROOT%\dist"

set "PORTAL_SCRIPTS=%ROOT%\..\family_smart_center_web\scripts"



set "PYTHON=C:\Program Files\Python\Python312\python.exe"

if not exist "%PYTHON%" set "PYTHON=C:\Python310\python.exe"

if exist "%ROOT%\.venv\Scripts\python.exe" set "PYTHON=%ROOT%\.venv\Scripts\python.exe"



cd /d "%ROOT%"



if not exist "output\solutions.txt" (

  echo [ERROR] missing output\solutions.txt - run scripts\update_data.bat first

  exit /b 1

)



if not exist "%PYTHON%" (

  echo [ERROR] Python not found

  exit /b 1

)



if exist "%DIST%" rmdir /s /q "%DIST%"

mkdir "%DIST%\web\games\24points"

mkdir "%DIST%\web\games\schulte"

mkdir "%DIST%\app"

mkdir "%DIST%\scripts\lib"

mkdir "%DIST%\logs"



"%PYTHON%" "games\24points\generate_library.py"

if errorlevel 1 exit /b 1



"%PYTHON%" "games\24points\generate_play.py"

if errorlevel 1 exit /b 1



for %%G in (stroop cancel simon spot_diff maze sudoku) do (

  "%PYTHON%" "games\%%G\generate.py"

  if errorlevel 1 exit /b 1

)



if not exist "web\games\schulte" mkdir "web\games\schulte"

"%PYTHON%" "games\schulte\build_page.py"

if errorlevel 1 exit /b 1



copy /Y "web\index.html" "dist\web\index.html" >nul

if errorlevel 1 exit /b 1

copy /Y "web\leaderboard.html" "dist\web\leaderboard.html" >nul

if not exist "dist\web\js" mkdir "dist\web\js"

xcopy /Y "web\js\*" "dist\web\js\" >nul 2>nul

xcopy /E /I /Y "web\games" "dist\web\games\" >nul

if errorlevel 1 exit /b 1



xcopy /E /I /Y "app" "dist\app\" >nul

if errorlevel 1 exit /b 1

for /d /r "%DIST%\app" %%D in (__pycache__) do @if exist "%%D" rmdir /s /q "%%D" 2>nul



copy /Y "requirements.txt" "%DIST%\requirements.txt" >nul

copy /Y "family-product.json" "%DIST%\family-product.json" >nul



if exist "%ROOT%\deploy\INSTALL.txt" (

  copy /Y "%ROOT%\deploy\INSTALL.txt" "%DIST%\INSTALL.txt" >nul



  for %%F in (service install) do (

    if exist "%ROOT%\deploy\%%F.bat" copy /Y "%ROOT%\deploy\%%F.bat" "%DIST%\%%F.bat" >nul

    if exist "%ROOT%\deploy\%%F.sh" copy /Y "%ROOT%\deploy\%%F.sh" "%DIST%\%%F.sh" >nul

  )



  if exist "%ROOT%\deploy\windows\" copy /Y "%ROOT%\deploy\windows\*.bat" "%DIST%\scripts\" >nul 2>nul

  if exist "%ROOT%\deploy\linux\" copy /Y "%ROOT%\deploy\linux\*.sh" "%DIST%\scripts\" >nul 2>nul

  if exist "%ROOT%\deploy\mac\" copy /Y "%ROOT%\deploy\mac\*.sh" "%DIST%\scripts\" >nul 2>nul

  if exist "%ROOT%\deploy\lib\" copy /Y "%ROOT%\deploy\lib\*.sh" "%DIST%\scripts\lib\" >nul 2>nul



  if exist "%PORTAL_SCRIPTS%\normalize_shell.py" (

    "%PYTHON%" "%PORTAL_SCRIPTS%\normalize_shell.py" "%ROOT%\deploy" "%DIST%"

  )

  if exist "%PORTAL_SCRIPTS%\validate_manifest.py" (

    "%PYTHON%" "%PORTAL_SCRIPTS%\validate_manifest.py" "%ROOT%\family-product.json" --dist "%DIST%"

    if errorlevel 1 exit /b 1

  )

)



echo.

echo Build OK: %DIST%

echo   dist\web\index.html

echo   dist\web\games\24points\play.html

echo   dist\web\games\stroop\index.html

echo   dist\app\main.py

endlocal

exit /b 0

