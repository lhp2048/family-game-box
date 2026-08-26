@echo off
cd /d "%~dp0"
call "%~dp0deploy\install.bat" %*
exit /b %ERRORLEVEL%
