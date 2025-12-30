# Stop all MYCOSOFT services

$ErrorActionPreference = "Continue"

$MASDir = "C:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas"

Write-Host "Stopping all MYCOSOFT services..." -ForegroundColor Yellow

# Stop watchdog
Get-Process -Name "powershell" -ErrorAction SilentlyContinue | Where-Object {
    try {
        $cmdLine = (Get-CimInstance Win32_Process -Filter "ProcessId = $($_.Id)").CommandLine
        $cmdLine -like "*service-watchdog*"
    } catch {
        $false
    }
} | Stop-Process -Force -ErrorAction SilentlyContinue

# Stop website (port 3000)
Get-NetTCPConnection -LocalPort 3000 -ErrorAction SilentlyContinue | 
    Select-Object -ExpandProperty OwningProcess -Unique | 
    ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue }

# Stop MycoBrain service (port 8003)
Get-Process -Name "python" -ErrorAction SilentlyContinue | Where-Object {
    try {
        $cmdLine = (Get-CimInstance Win32_Process -Filter "ProcessId = $($_.Id)").CommandLine
        $cmdLine -like "*mycobrain_service*"
    } catch {
        $false
    }
} | Stop-Process -Force -ErrorAction SilentlyContinue

# Stop Docker containers
Set-Location $MASDir
docker-compose down 2>$null | Out-Null
docker-compose -f docker-compose.mindex.yml down 2>$null | Out-Null
docker-compose -f docker-compose.integrations.yml down 2>$null | Out-Null

Write-Host "All services stopped." -ForegroundColor Green


