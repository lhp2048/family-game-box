@echo off
call "%~dp0stop_service_win.bat"
call "%~dp0run_service.bat"
exit /b 0
