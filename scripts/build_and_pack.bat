@echo off
setlocal
call "%~dp0build.bat"
if errorlevel 1 exit /b 1
call "%~dp0pack.bat"
if errorlevel 1 exit /b 1
endlocal
