@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0start-digital-twin.ps1"
if errorlevel 1 pause
