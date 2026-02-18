# Start Moshi on localhost (RTX 5090) for full PersonaPlex
# Feb 13, 2026

$ErrorActionPreference = "Stop"

# Kill any existing Moshi
Write-Host "[CLEANUP] Stopping existing Moshi processes..." -ForegroundColor Yellow
Get-Process python -ErrorAction SilentlyContinue | Where-Object { 
    $_.CommandLine -like '*moshi.server*' -or $_.CommandLine -like '*moshi_server*' 
} | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2

# Check port
$portInUse = Get-NetTCPConnection -LocalPort 8998 -ErrorAction SilentlyContinue
if ($portInUse) {
    Write-Host "[ERROR] Port 8998 still in use by PID $($portInUse.OwningProcess)" -ForegroundColor Red
    $proc = Get-Process -Id $portInUse.OwningProcess -ErrorAction SilentlyContinue
    if ($proc) {
        Write-Host "Killing PID $($proc.Id)..." -ForegroundColor Yellow
        Stop-Process -Id $proc.Id -Force
        Start-Sleep -Seconds 2
    }
}

Write-Host "[STARTING] Moshi server with moshika-pytorch-bf16 (female voice) on RTX 5090..." -ForegroundColor Cyan
Write-Host "Model will download/load (~15GB), warmup takes 60-90 seconds" -ForegroundColor Gray
Write-Host "Listening on: http://localhost:8998 (WebSocket)" -ForegroundColor White

# Start Moshi in new window with visible output
$process = Start-Process -FilePath "python" -ArgumentList @(
    "-m", "moshi.server",
    "--host", "0.0.0.0",
    "--port", "8998",
    "--hf-repo", "kyutai/moshika-pytorch-bf16"
) -PassThru -WindowStyle Normal

Write-Host "[OK] Moshi started: PID $($process.Id)" -ForegroundColor Green
Write-Host ""
Write-Host "Waiting for warmup..." -ForegroundColor Yellow

# Wait and check
for ($i = 1; $i -le 12; $i++) {
    Start-Sleep -Seconds 10
    $proc = Get-Process -Id $process.Id -ErrorAction SilentlyContinue
    if (-not $proc) {
        Write-Host "[ERROR] Moshi crashed. Check the window for errors." -ForegroundColor Red
        exit 1
    }
    $memMB = [Math]::Round($proc.WorkingSet64 / 1MB)
    Write-Host "  [$i/12] PID $($process.Id) - Memory: ${memMB} MB" -ForegroundColor Gray
    
    # Check if listening
    $listening = Get-NetTCPConnection -LocalPort 8998 -ErrorAction SilentlyContinue
    if ($listening) {
        Write-Host ""
        Write-Host "[SUCCESS] Moshi is ONLINE and listening on port 8998!" -ForegroundColor Green
        Write-Host "Memory usage: ${memMB} MB" -ForegroundColor White
        Write-Host "Ready for PersonaPlex Bridge connection." -ForegroundColor White
        exit 0
    }
}

Write-Host "[WARN] Moshi still warming up after 120s. Check the Moshi window." -ForegroundColor Yellow
