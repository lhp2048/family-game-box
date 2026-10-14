@echo off
REM Pack a single game zip. Usage: scripts\pack_game.bat simon
setlocal
set ROOT=%~dp0..
set SLUG=%~1
if "%SLUG%"=="" (
  echo Usage: %~nx0 ^<game-slug^>
  exit /b 1
)
bash "%~dp0pack_game.sh" %SLUG%
if errorlevel 1 (
  echo Note: pack_game.bat requires bash ^(Git Bash / WSL^). Or run pack_game.sh directly.
  exit /b 1
)
