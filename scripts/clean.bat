@echo off
setlocal
cd /d "%~dp0.."
if exist dist rmdir /s /q dist
if exist dist_out rmdir /s /q dist_out
if exist release rmdir /s /q release
echo Cleaned dist/, dist_out/, and release/
exit /b 0
