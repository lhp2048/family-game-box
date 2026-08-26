@echo off
setlocal
cd /d "%~dp0.."
if exist dist rmdir /s /q dist
if exist release rmdir /s /q release
echo Cleaned dist/ and release/
exit /b 0
