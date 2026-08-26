@echo off
cd /d "%~dp0"
call "%~dp0deploy\service.bat" %*
exit /b %ERRORLEVEL%
