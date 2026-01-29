# PersonaPlex NVIDIA Integration Startup Script
# January 29, 2026

Write-Host "=== PersonaPlex NVIDIA Integration Startup ===" -ForegroundColor Cyan

# Set environment variables
$env:NO_TORCH_COMPILE = "1"
$env:HF_TOKEN = "$env:HF_TOKEN"
$env:MAS_ORCHESTRATOR_URL = "http://192.168.0.188:8001"
$env:MOSHI_HOST = "localhost"
$env:MOSHI_PORT = "8998"

# Check if Moshi server is already running on 8998
$moshi = Get-NetTCPConnection -LocalPort 8998 -ErrorAction SilentlyContinue
if ($moshi) {
    Write-Host "[OK] Moshi server already running on port 8998" -ForegroundColor Green
} else {
    Write-Host "[STARTING] Moshi server on port 8998..." -ForegroundColor Yellow
    Start-Process -FilePath "python" -ArgumentList "-m moshi.server --host 0.0.0.0 --port 8998" -NoNewWindow
    Start-Sleep -Seconds 5
}

# Check if bridge is already running on 8999
$bridge = Get-NetTCPConnection -LocalPort 8999 -ErrorAction SilentlyContinue
if ($bridge) {
    Write-Host "[OK] PersonaPlex Bridge already running on port 8999" -ForegroundColor Green
} else {
    Write-Host "[STARTING] PersonaPlex NVIDIA Bridge on port 8999..." -ForegroundColor Yellow
    Start-Process -FilePath "python" -ArgumentList "services/personaplex-local/personaplex_bridge_nvidia.py" -NoNewWindow
    Start-Sleep -Seconds 3
}

# Verify services
Write-Host ""
Write-Host "=== Service Status ===" -ForegroundColor Cyan
try {
    $health = Invoke-RestMethod -Uri "http://localhost:8999/health" -TimeoutSec 5
    if ($health.moshi_available) {
        Write-Host "[OK] PersonaPlex NVIDIA: AVAILABLE" -ForegroundColor Green
        Write-Host "     Voice: NATF2.pt (MYCA Natural Female)" -ForegroundColor Gray
        Write-Host "     MAS Orchestrator: $($health.mas_orchestrator)" -ForegroundColor Gray
    } else {
        Write-Host "[WARN] PersonaPlex: Moshi server not detected" -ForegroundColor Yellow
    }
} catch {
    Write-Host "[ERROR] Bridge health check failed" -ForegroundColor Red
}

Write-Host ""
Write-Host "=== Access PersonaPlex ===" -ForegroundColor Cyan
Write-Host "Native Moshi UI:    http://localhost:8998" -ForegroundColor White
Write-Host "Bridge API:         http://localhost:8999" -ForegroundColor White
Write-Host "Bridge Health:      http://localhost:8999/health" -ForegroundColor White
Write-Host "Website Voice:      http://localhost:3010/myca/voice-duplex" -ForegroundColor White
Write-Host ""
Write-Host "=== Full-Duplex Voice Ready ===" -ForegroundColor Green
