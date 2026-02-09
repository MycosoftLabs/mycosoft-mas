@echo off
echo =====================================================================
echo          EARTH2STUDIO LOCAL API SERVER
echo          February 5, 2026
echo =====================================================================
echo.
echo Activating Earth2Studio environment...
call C:\Users\admin2\.earth2studio-venv\Scripts\activate.bat

echo Starting API server on port 8220...
echo API Docs: http://localhost:8220/docs
echo.

python scripts\earth2_api_server.py

pause
