# Start the always-on Docker stack (independent of Cursor)

$ErrorActionPreference = "Continue"

$MASDir = "C:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas"
Set-Location $MASDir

Write-Host "Starting MYCOSOFT always-on Docker stack..." -ForegroundColor Cyan

# Ensure Docker is running
$dockerOk = $true
try {
  docker info | Out-Null
} catch {
  $dockerOk = $false
}

if (-not $dockerOk) {
  Write-Host "Docker not responding. Launching Docker Desktop..." -ForegroundColor Yellow
  Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe" -ErrorAction SilentlyContinue
  Start-Sleep -Seconds 25
}

docker compose -f docker-compose.always-on.yml up -d --build

Write-Host ""
Write-Host "Stack started. Endpoints:" -ForegroundColor Green
Write-Host "  Website:   http://localhost:3000" -ForegroundColor White
Write-Host "  MycoBrain: http://localhost:8003/health" -ForegroundColor White
Write-Host "  MINDEX:    http://localhost:8000/health" -ForegroundColor White

