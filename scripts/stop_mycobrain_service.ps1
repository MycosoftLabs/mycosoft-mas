# Stop MycoBrain Service to Free COM Port
# Run this before uploading firmware

Write-Host "Stopping MycoBrain service..." -ForegroundColor Yellow

# Find MycoBrain service process
$processes = Get-Process python* -ErrorAction SilentlyContinue | Where-Object {
    $_.Path -like "*python*"
}

$stopped = $false
foreach ($proc in $processes) {
    # Check if it's using port 8003 (MycoBrain service)
    $netstat = netstat -ano | findstr "8003" | findstr "$($proc.Id)"
    if ($netstat) {
        Write-Host "Found MycoBrain service (PID: $($proc.Id))" -ForegroundColor Cyan
        Stop-Process -Id $proc.Id -Force
        Write-Host "Stopped!" -ForegroundColor Green
        $stopped = $true
    }
}

if (-not $stopped) {
    Write-Host "No MycoBrain service found running on port 8003" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "COM3 should now be free for uploading!" -ForegroundColor Green
Write-Host "After uploading, restart the service with:" -ForegroundColor Cyan
Write-Host "  python services/mycobrain/mycobrain_dual_service.py" -ForegroundColor White

