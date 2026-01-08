# Docker State Manager - Real-time Container Status
# Run this anytime to see complete system state

Write-Host "=== MYCOSOFT DOCKER STATE MANAGER ===" -ForegroundColor Cyan
Write-Host "Updated: $(Get-Date)" -ForegroundColor Gray
Write-Host ""

# Critical Services Health
$critical = @(
    @{Name="MINDEX"; Container="mycosoft-always-on-mindex-1"; Port=8000; Health="/api/mindex/health"},
    @{Name="MycoBrain"; Container="local-service"; Port=8003; Health="/health"},
    @{Name="Website"; Container="mycosoft-always-on-mycosoft-website-1"; Port=3000; Health="/"},
    @{Name="MAS Orch"; Container="mycosoft-mas-mas-orchestrator-1"; Port=8001; Health="/health"},
    @{Name="n8n"; Container="mycosoft-mas-n8n-1"; Port=5678; Health="/healthz"}
)

Write-Host "CRITICAL SERVICES:" -ForegroundColor Yellow
foreach ($svc in $critical) {
    # Check container
    $containerStatus = docker ps --filter "name=$($svc.Container)" --format "{{.Status}}" 2>$null
    
    # Check HTTP health
    try {
        if ($svc.Container -eq "local-service") {
            $health = Invoke-RestMethod "http://localhost:$($svc.Port)$($svc.Health)" -TimeoutSec 2 -ErrorAction Stop
            Write-Host "  ✅ $($svc.Name) (Local:$($svc.Port)): ONLINE" -ForegroundColor Green
        } else {
            $health = Invoke-RestMethod "http://localhost:$($svc.Port)$($svc.Health)" -TimeoutSec 2 -ErrorAction Stop
            Write-Host "  ✅ $($svc.Name) ($($svc.Port)): $containerStatus" -ForegroundColor Green
        }
    } catch {
        Write-Host "  ❌ $($svc.Name) ($($svc.Port)): OFFLINE" -ForegroundColor Red
    }
}

# Container Summary
Write-Host "`nCONTAINER SUMMARY:" -ForegroundColor Yellow
$containers = docker ps -a --format "{{.Names}}|{{.Status}}|{{.Image}}"
$running = ($containers | Select-String "Up").Count
$stopped = ($containers | Select-String "Exited|Created").Count
$unhealthy = ($containers | Select-String "unhealthy").Count
$total = ($containers | Measure-Object).Count

Write-Host "  Total: $total | Running: $running | Stopped: $stopped | Unhealthy: $unhealthy"

if ($unhealthy -gt 0) {
    Write-Host "`n  UNHEALTHY CONTAINERS:" -ForegroundColor Red
    docker ps --filter "health=unhealthy" --format "    - {{.Names}}: {{.Status}}"
}

# Resource Usage
Write-Host "`nRESOURCE USAGE:" -ForegroundColor Yellow
$usage = docker system df --format "{{.Type}}\t{{.TotalCount}}\t{{.Size}}\t{{.Reclaimable}}"
$usage | ForEach-Object {
    $parts = $_ -split "`t"
    Write-Host "  $($parts[0]): $($parts[2]) ($($parts[1]) items, $($parts[3]) reclaimable)"
}

# Quick Actions
Write-Host "`nQUICK ACTIONS:" -ForegroundColor Cyan
Write-Host "  1. View logs:     docker logs <container-name>"
Write-Host "  2. Restart:       docker restart <container-name>"
Write-Host "  3. Shell access:  docker exec -it <container-name> sh"
Write-Host "  4. Clean cache:   docker builder prune -f"
Write-Host "  5. Full cleanup:  docker system prune -af"

# Service URLs
Write-Host "`nSERVICE URLs:" -ForegroundColor Cyan
Write-Host "  MINDEX:          http://localhost:8000/api/mindex/health"
Write-Host "  MycoBrain:       http://localhost:8003/health"
Write-Host "  Website:         http://localhost:3000"
Write-Host "  Device Manager:  http://localhost:3000/natureos/devices"
Write-Host "  MAS:             http://localhost:8001/health"
Write-Host "  n8n:             http://localhost:5678"
Write-Host "  MYCA Dashboard:  http://localhost:3100"

