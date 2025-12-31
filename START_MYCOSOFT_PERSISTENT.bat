@echo off
title MYCOSOFT Persistent Services
color 0B

echo.
echo ========================================
echo   MYCOSOFT Persistent Service Startup
echo ========================================
echo.

cd /d "%~dp0"

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "scripts\start-all-persistent.ps1"

echo.
echo Press any key to exit...
pause >nul










