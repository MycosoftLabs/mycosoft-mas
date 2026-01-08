@echo off
echo ========================================
echo MYCOBRAIN COMPLETE TEST
echo Testing: Buzzer, Lights, Commands
echo ========================================
echo.

cd /d "%~dp0\.."
python scripts\test_buzzer_lights.py

pause
