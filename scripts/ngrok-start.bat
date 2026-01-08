@echo off
REM Quick start ngrok tunnels for MAS
REM Run this to expose all running services

echo.
echo ========================================
echo   Mycosoft MAS - Quick Tunnel Start
echo ========================================
echo.

REM Refresh PATH to include ngrok
set PATH=%PATH%;%LOCALAPPDATA%\Microsoft\WinGet\Packages\Ngrok.Ngrok_Microsoft.Winget.Source_8wekyb3d8bbwe

REM Start the PowerShell script
powershell -ExecutionPolicy Bypass -File "%~dp0start_ngrok_tunnels.ps1" -All

pause

