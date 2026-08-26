@echo off
setlocal EnableExtensions
rem Install entry (REQ): delegates to service.bat install
cd /d "%~dp0"
call "%~dp0service.bat" install %*
exit /b %ERRORLEVEL%
