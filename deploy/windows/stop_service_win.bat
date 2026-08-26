@echo off
setlocal
if not defined PORT set "PORT=18029"

call "%~dp0kill_port_listener.bat" %PORT% python
echo stopped port %PORT%
exit /b 0
