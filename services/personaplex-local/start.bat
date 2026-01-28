@echo off
REM PersonaPlex Local Startup - January 28, 2026
REM Runs PersonaPlex on local RTX 5090 GPU

echo ============================================
echo PersonaPlex Local Server Startup
echo ============================================
echo.

REM Check for Python
python --version >nul 2>&1
if errorlevel 1 (
    echo Python not found! Please install Python 3.10+
    exit /b 1
)

REM Check for CUDA
nvidia-smi >nul 2>&1
if errorlevel 1 (
    echo WARNING: nvidia-smi not found, GPU may not be available
)

REM Install requirements if needed
echo Installing requirements...
pip install -q websockets numpy torch aiohttp fastapi uvicorn httpx

REM Start PersonaPlex server in background
echo Starting PersonaPlex server on port 8998...
start "PersonaPlex Server" cmd /c "python server.py"

REM Wait for server to start
timeout /t 3 /nobreak >nul

REM Start Bridge API
echo Starting Bridge API on port 8999...
start "PersonaPlex Bridge" cmd /c "python bridge.py"

echo.
echo ============================================
echo PersonaPlex is running!
echo Server: ws://localhost:8998
echo Bridge: http://localhost:8999
echo ============================================
echo.
echo Press any key to stop...
pause >nul

REM Cleanup
taskkill /FI "WINDOWTITLE eq PersonaPlex Server" /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq PersonaPlex Bridge" /F >nul 2>&1
