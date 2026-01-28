@echo off
REM PersonaPlex Local Startup - January 28, 2026
REM Run on local machine with RTX 5090

echo ========================================
echo PersonaPlex Local Server
echo GPU: RTX 5090 (32GB VRAM)
echo ========================================

REM Set environment
set PERSONAPLEX_HOST=0.0.0.0
set PERSONAPLEX_PORT=8998
set CUDA_VISIBLE_DEVICES=0

REM Check GPU
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader
echo.

REM Start PersonaPlex server
echo Starting PersonaPlex WebSocket server on port 8998...
start "PersonaPlex Server" cmd /k "cd /d %~dp0 && python server.py"

REM Wait for server
timeout /t 5

REM Start Bridge API
echo Starting Bridge API on port 8999...
start "Bridge API" cmd /k "cd /d %~dp0 && python bridge_api.py"

echo.
echo ========================================
echo PersonaPlex running!
echo - WebSocket: ws://localhost:8998
echo - Bridge API: http://localhost:8999
echo - Health: http://localhost:8999/health
echo ========================================
