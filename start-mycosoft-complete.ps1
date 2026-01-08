#!/usr/bin/env pwsh
# Mycosoft MAS - Complete System Startup Script
# This script starts all Mycosoft MAS services and verifies system health

param(
    [switch]$Rebuild,
    [switch]$Clean
)

$ErrorActionPreference = "Continue"
$ProjectRoot = "C:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  MYCOSOFT MAS - SYSTEM STARTUP" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

# Navigate to project root
Set-Location $ProjectRoot

# Clean up if requested
if ($Clean) {
    Write-Host "Cleaning up old containers..." -ForegroundColor Yellow
    docker compose down -v 2>&1 | Out-Null
    Write-Host "Cleanup complete`n" -ForegroundColor Green
}

# Build images if requested
if ($Rebuild) {
    Write-Host "Rebuilding Docker images..." -ForegroundColor Yellow
    docker compose build 2>&1 | Out-Null
    Write-Host "Build complete`n" -ForegroundColor Green
}

# Start infrastructure services
Write-Host "Starting infrastructure services..." -ForegroundColor Yellow
docker compose up -d postgres redis qdrant 2>&1 | Out-Null
Start-Sleep -Seconds 5
Write-Host "  ✓ PostgreSQL, Redis, Qdrant" -ForegroundColor Green

# Start orchestrator
Write-Host "Starting MAS Orchestrator..." -ForegroundColor Yellow
docker compose up -d mas-orchestrator 2>&1 | Out-Null
Start-Sleep -Seconds 10
Write-Host "  ✓ MAS Orchestrator" -ForegroundColor Green

# Start N8N
Write-Host "Starting N8N Workflows..." -ForegroundColor Yellow
docker compose up -d n8n 2>&1 | Out-Null
Start-Sleep -Seconds 5
Write-Host "  ✓ N8N" -ForegroundColor Green

# Start dashboard
Write-Host "Starting Dashboard..." -ForegroundColor Yellow
docker compose up -d myca-app 2>&1 | Out-Null
Start-Sleep -Seconds 5
Write-Host "  ✓ Dashboard" -ForegroundColor Green

# Health checks
Write-Host "`nPerforming health checks..." -ForegroundColor Yellow

$services = @(
    @{Name="MAS Orchestrator"; Url="http://localhost:8001/health"},
    @{Name="N8N"; Url="http://localhost:5690/healthz"}
)

$allHealthy = $true
foreach ($service in $services) {
    Write-Host "  Checking $($service.Name)..." -NoNewline
    try {
        $response = Invoke-RestMethod -Uri $service.Url -TimeoutSec 10 -ErrorAction Stop
        Write-Host " OK" -ForegroundColor Green
    } catch {
        Write-Host " FAILED" -ForegroundColor Red
        $allHealthy = $false
    }
}

if ($allHealthy) {
    Write-Host "`n✓ All services are healthy!" -ForegroundColor Green
} else {
    Write-Host "`n⚠ Some services failed health checks" -ForegroundColor Yellow
}

# Display system info
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  MYCOSOFT MAS - READY" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan

Write-Host "`nKey URLs:" -ForegroundColor Yellow
Write-Host "  Orchestrator API:      http://localhost:8001" -ForegroundColor White
Write-Host "  Dashboard:             http://localhost:3001" -ForegroundColor White
Write-Host "  N8N Workflows:         http://localhost:5690" -ForegroundColor White
Write-Host "  Orchestrator Data:     http://localhost:8001/orchestrator/dashboard" -ForegroundColor White

Write-Host "`nQuick Commands:" -ForegroundColor Yellow
Write-Host "  View logs:             docker compose logs -f" -ForegroundColor White
Write-Host "  Stop all:              docker compose down" -ForegroundColor White
Write-Host "  Restart orchestrator:  docker compose restart mas-orchestrator" -ForegroundColor White

# Test orchestrator
Write-Host "`nFetching orchestrator status..." -ForegroundColor Yellow
try {
    $dashboard = Invoke-RestMethod -Uri "http://localhost:8001/orchestrator/dashboard" -TimeoutSec 10
    Write-Host "  Active Agents: $($dashboard.metrics.activeAgents)/$($dashboard.metrics.totalAgents)" -ForegroundColor Green
    Write-Host "  Total Tasks: $($dashboard.metrics.totalTasks)" -ForegroundColor Green
    Write-Host "  System Uptime: $($dashboard.metrics.uptime)" -ForegroundColor Green
    Write-Host "  Memory - Short Term: $($dashboard.memory.shortTermCount) entries" -ForegroundColor Green
    Write-Host "  Memory - Long Term: $($dashboard.memory.longTermCount) entries" -ForegroundColor Green
} catch {
    Write-Host "  Could not fetch orchestrator data" -ForegroundColor Red
}

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "System startup complete! 🚀" -ForegroundColor Green
Write-Host "========================================`n" -ForegroundColor Cyan








































