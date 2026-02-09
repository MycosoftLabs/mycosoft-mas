@echo off
echo =====================================================================
echo   MYCOSOFT LOCAL GPU SERVICES
echo   All GPU operations on local RTX 5090 for dev server localhost:3010
echo =====================================================================
echo.

:: Check if running as admin (recommended for best performance)
net session >nul 2>&1
if %errorLevel% == 0 (
    echo [OK] Running as Administrator
) else (
    echo [WARN] Not running as Administrator - some features may be limited
)

echo.
echo Services to start:
echo   - GPU Gateway:       localhost:8300  (unified entry point)
echo   - PersonaPlex/Moshi: localhost:8998  (voice AI, 23GB VRAM)
echo   - PersonaPlex Bridge:localhost:8999  (voice routing)
echo   - Earth2Studio API:  localhost:8220  (weather AI)
echo.
echo For dev server, run: npm run dev in website folder (localhost:3010)
echo.
echo Starting unified GPU services...
echo.

python scripts\local_gpu_services.py

pause
