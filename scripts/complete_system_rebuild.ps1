#!/usr/bin/env pwsh
# Complete System Rebuild Script
# Cleans all caches and rebuilds entire system

Write-Host "=== MYCOSOFT COMPLETE SYSTEM REBUILD ===" -ForegroundColor Cyan
Write-Host ""

$ErrorActionPreference = "Continue"
cd C:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas

# Step 1: Stop all containers
Write-Host "[1/8] Stopping all containers..." -ForegroundColor Yellow
docker stop $(docker ps -aq) 2>$null
Write-Host "  Done" -ForegroundColor Green

# Step 2: Remove old website containers/images
Write-Host "[2/8] Removing old website containers and images..." -ForegroundColor Yellow
docker rm -f mycosoft-always-on-mycosoft-website-1 2>$null
docker rm -f mycosoft-website 2>$null
docker rmi -f mycosoft-always-on-mycosoft-website 2>$null
docker rmi -f mycosoft-website-fixed 2>$null
Write-Host "  Done" -ForegroundColor Green

# Step 3: Clean local build caches
Write-Host "[3/8] Cleaning local build caches..." -ForegroundColor Yellow
if (Test-Path ".next") { 
    Remove-Item -Recurse -Force .next 
    Write-Host "  Removed .next" -ForegroundColor Gray
}
if (Test-Path "node_modules/.cache") { 
    Remove-Item -Recurse -Force node_modules/.cache 
    Write-Host "  Removed node_modules/.cache" -ForegroundColor Gray
}
if (Test-Path "tsconfig.tsbuildinfo") { 
    Remove-Item tsconfig.tsbuildinfo 
    Write-Host "  Removed tsbuildinfo" -ForegroundColor Gray
}
Write-Host "  Done" -ForegroundColor Green

# Step 4: Clear Docker build cache
Write-Host "[4/8] Clearing Docker build cache..." -ForegroundColor Yellow
docker builder prune -af --filter "label=stage=builder" 2>$null
Write-Host "  Done" -ForegroundColor Green

# Step 5: Verify source code is clean
Write-Host "[5/8] Verifying source code..." -ForegroundColor Yellow
$criticalFiles = @(
    "components/mycobrain-device-manager.tsx",
    "app/api/mycobrain/devices/route.ts",
    "app/natureos/devices/page.tsx"
)
$allGood = $true
foreach ($file in $criticalFiles) {
    if (Test-Path $file) {
        $content = Get-Content $file -Raw
        if ($content -match "initialTimeout") {
            Write-Host "  ERROR: $file contains 'initialTimeout'" -ForegroundColor Red
            $allGood = $false
        } else {
            Write-Host "  ✓ $file" -ForegroundColor Green
        }
    } else {
        Write-Host "  ✗ $file MISSING" -ForegroundColor Red
        $allGood = $false
    }
}

if (-not $allGood) {
    Write-Host "ERROR: Source code issues found!" -ForegroundColor Red
    exit 1
}
Write-Host "  Done" -ForegroundColor Green

# Step 6: Build fresh Docker images
Write-Host "[6/8] Building fresh Docker images (this takes 2-3 minutes)..." -ForegroundColor Yellow
docker-compose -f docker-compose.always-on.yml build --no-cache mycosoft-website
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Docker build failed!" -ForegroundColor Red
    exit 1
}
Write-Host "  Done" -ForegroundColor Green

# Step 7: Start all services
Write-Host "[7/8] Starting all services..." -ForegroundColor Yellow

# Start MINDEX (if not running)
$mindexStatus = docker ps --filter "name=mindex" --format "{{.Status}}"
if (-not $mindexStatus) {
    docker-compose -f docker-compose.always-on.yml up -d --no-deps mindex
    Write-Host "  MINDEX started" -ForegroundColor Gray
} else {
    Write-Host "  MINDEX already running" -ForegroundColor Gray
}

# Start website
docker-compose -f docker-compose.always-on.yml up -d --no-deps mycosoft-website
Write-Host "  Website started" -ForegroundColor Gray
Write-Host "  Done" -ForegroundColor Green

# Step 8: Health checks
Write-Host "[8/8] Running health checks..." -ForegroundColor Yellow
Start-Sleep -Seconds 20

Write-Host ""
Write-Host "=== SERVICE STATUS ===" -ForegroundColor Cyan

# Check MINDEX
try {
    $mindex = Invoke-RestMethod http://localhost:8000/api/mindex/health -TimeoutSec 5
    Write-Host "✓ MINDEX (8000): ONLINE - v$($mindex.version)" -ForegroundColor Green
} catch {
    Write-Host "✗ MINDEX (8000): OFFLINE" -ForegroundColor Red
}

# Check MycoBrain
try {
    $mb = Invoke-RestMethod http://localhost:8003/health -TimeoutSec 5
    Write-Host "✓ MycoBrain (8003): ONLINE - v$($mb.version) - $($mb.devices_connected) devices" -ForegroundColor Green
} catch {
    Write-Host "✗ MycoBrain (8003): OFFLINE" -ForegroundColor Red
}

# Check Website
try {
    $web = Invoke-WebRequest http://localhost:3000 -TimeoutSec 5 -UseBasicParsing
    if ($web.StatusCode -eq 200) {
        Write-Host "✓ Website (3000): ONLINE" -ForegroundColor Green
    }
} catch {
    Write-Host "✗ Website (3000): OFFLINE" -ForegroundColor Red
}

# Check n8n
try {
    $n8n = Invoke-WebRequest http://localhost:5678/healthz -TimeoutSec 3 -UseBasicParsing
    if ($n8n.StatusCode -eq 200) {
        Write-Host "✓ n8n (5678): ONLINE" -ForegroundColor Green
    }
} catch {
    Write-Host "✗ n8n (5678): OFFLINE" -ForegroundColor Yellow
}

# Check MAS
try {
    $mas = Invoke-RestMethod http://localhost:8001/health -TimeoutSec 3
    Write-Host "✓ MAS Orchestrator (8001): ONLINE" -ForegroundColor Green
} catch {
    Write-Host "✗ MAS Orchestrator (8001): OFFLINE" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "=== REBUILD COMPLETE ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "Website: http://localhost:3000" -ForegroundColor White
Write-Host "Device Manager: http://localhost:3000/natureos/devices" -ForegroundColor White
Write-Host "MINDEX: http://localhost:8000/api/mindex/health" -ForegroundColor White
Write-Host "MycoBrain: http://localhost:8003/health" -ForegroundColor White
Write-Host ""

