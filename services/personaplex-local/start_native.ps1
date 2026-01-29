# PersonaPlex Native Moshi Startup Script - January 29, 2026
# Run this script to start the native Moshi TTS servers

Write-Host "=============================================="
Write-Host "PersonaPlex Native Moshi TTS - January 29, 2026"
Write-Host "=============================================="

# Kill existing servers
Write-Host "
Killing existing servers on ports 8998/8999..."
$pids = netstat -ano | findstr ":8998 :8999" | ForEach-Object { ($_ -split '\s+')[-1] } | Where-Object { $_ -match '^\d+$' -and $_ -ne "0" } | Select-Object -Unique
$pids | ForEach-Object { taskkill /PID $_ /F 2>$null }
Start-Sleep -Seconds 2

# Set environment
$env:NO_TORCH_COMPILE = "1"
$env:MAS_ORCHESTRATOR_URL = "http://192.168.0.188:8001"

# Start native moshi server
Write-Host "Starting Native Moshi TTS Server on port 8998..."
Start-Process -FilePath "python" -ArgumentList "moshi_native_v2.py" -WorkingDirectory "$PSScriptRoot" -WindowStyle Normal

# Wait for model to load
Write-Host "Waiting for model to load (15 seconds)..."
Start-Sleep -Seconds 15

# Start bridge API
Write-Host "Starting Bridge API on port 8999..."
Start-Process -FilePath "python" -ArgumentList "bridge_api_v2.py" -WorkingDirectory "$PSScriptRoot" -WindowStyle Normal

Start-Sleep -Seconds 3

# Test health
Write-Host "
Testing health endpoint..."
try {
    $health = Invoke-RestMethod -Uri http://localhost:8999/health -TimeoutSec 10
    Write-Host "Bridge Status: $($health.status)"
    Write-Host "PersonaPlex Available: $($health.personaplex)"
} catch {
    Write-Host "Health check failed - servers may still be starting"
}

Write-Host "
=============================================="
Write-Host "Servers started!"
Write-Host "- Native Moshi TTS: ws://localhost:8998"
Write-Host "- Bridge API: http://localhost:8999"
Write-Host "=============================================="
