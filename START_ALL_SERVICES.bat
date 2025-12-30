@echo off
title MYCOSOFT - Start All Services
color 0B

echo.
echo ========================================
echo    MYCOSOFT - Starting All Services
echo ========================================
echo.

cd /d "%~dp0"

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "scripts\start-all-with-watchdog.ps1"

echo.
echo Services are starting...
echo Press any key to close this window (services will continue running)
pause > nul
