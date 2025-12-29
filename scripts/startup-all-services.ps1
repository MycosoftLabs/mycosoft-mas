# MYCOSOFT Complete System Startup Script
# This script starts all services and ensures they persist across restarts
# Run this script at Windows startup for full system availability

param(
    [switch]$CheckOnly,
    [switch]$StopAll
)

$ErrorActionPreference = "Continue"

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  MYCOSOFT System Startup                   " -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# Configuration
$MASDir = "C:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas"
$WebsiteDir = "C:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website"
$LogDir = "$MASDir\logs"

# Create log directory
if (-not (Test-Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
}

# Function to check if a port is in use
function Test-Port {
    param([int]$Port)
    $connection = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue
    return $null -ne $connection
}

# Function to start a process in background
function Start-BackgroundProcess {
    param(
        [string]$Name,
        [string]$WorkingDir,
        [string]$Command,
        [string]$Arguments,
        [string]$LogFile
    )
    
    Write-Host "Starting $Name..." -ForegroundColor Yellow
    
    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = $Command
    $psi.Arguments = $Arguments
    $psi.WorkingDirectory = $WorkingDir
    $psi.UseShellExecute = $false
    $psi.CreateNoWindow = $true
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    
    $process = [System.Diagnostics.Process]::Start($psi)
    
    Write-Host "$Name started (PID: $($process.Id))" -ForegroundColor Green
    return $process
}

# Stop all services
if ($StopAll) {
    Write-Host "Stopping all services..." -ForegroundColor Red
    
    # Stop Docker containers
    Set-Location $MASDir
    docker-compose down 2>$null
    docker-compose -f docker-compose.mindex.yml down 2>$null
    docker-compose -f docker-compose.integrations.yml down 2>$null
    
    # Stop Node processes
    Get-Process -Name "node" -ErrorAction SilentlyContinue | Stop-Process -Force
    
    Write-Host "All services stopped." -ForegroundColor Green
    exit 0
}

# Check status only
if ($CheckOnly) {
    Write-Host "Checking service status..." -ForegroundColor Yellow
    Write-Host ""
    
    # Docker containers
    Write-Host "Docker Containers:" -ForegroundColor Cyan
    docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
    
    Write-Host ""
    Write-Host "Port Status:" -ForegroundColor Cyan
    $ports = @{
        3000 = "Website (Next.js)"
        3001 = "MYCA App"
        3100 = "UniFi Dashboard"
        5678 = "n8n Workflows"
        8000 = "MINDEX API"
        8001 = "MAS Orchestrator"
    }
    
    foreach ($port in $ports.Keys | Sort-Object) {
        if (Test-Port $port) {
            Write-Host "  Port $port ($($ports[$port])): " -NoNewline
            Write-Host "RUNNING" -ForegroundColor Green
        } else {
            Write-Host "  Port $port ($($ports[$port])): " -NoNewline
            Write-Host "NOT RUNNING" -ForegroundColor Red
        }
    }
    
    exit 0
}

Write-Host "Starting all MYCOSOFT services..." -ForegroundColor Yellow
Write-Host ""

# ============================================
# 1. Start Docker Containers
# ============================================
Write-Host "[1/4] Starting Docker containers..." -ForegroundColor Cyan

Set-Location $MASDir

# Check if Docker is running
$dockerStatus = docker info 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "Docker is not running. Starting Docker Desktop..." -ForegroundColor Yellow
    Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe"
    Start-Sleep -Seconds 30
}

# Create network if needed
docker network create mycosoft-network 2>$null

# Start main containers
Write-Host "  Starting core containers..." -ForegroundColor Gray
docker-compose up -d 2>$null

# Start MINDEX
Write-Host "  Starting MINDEX..." -ForegroundColor Gray
docker-compose -f docker-compose.mindex.yml up -d 2>$null

# Start integrations
Write-Host "  Starting integrations..." -ForegroundColor Gray
docker-compose -f docker-compose.integrations.yml up -d 2>$null

# Ensure restart policies
Write-Host "  Setting restart policies..." -ForegroundColor Gray
docker ps -q | ForEach-Object { docker update --restart unless-stopped $_ 2>$null }

Write-Host "  Docker containers started." -ForegroundColor Green

# ============================================
# 2. Start Website
# ============================================
Write-Host ""
Write-Host "[2/4] Starting Website..." -ForegroundColor Cyan

if (-not (Test-Port 3000)) {
    Set-Location $WebsiteDir
    
    # Start website in background using Start-Process
    $websiteLog = "$LogDir\website.log"
    Start-Process -FilePath "cmd.exe" -ArgumentList "/c npm run dev > `"$websiteLog`" 2>&1" -WorkingDirectory $WebsiteDir -WindowStyle Hidden
    
    Write-Host "  Website starting on port 3000..." -ForegroundColor Green
    Start-Sleep -Seconds 5
} else {
    Write-Host "  Website already running on port 3000" -ForegroundColor Green
}

# ============================================
# 3. Verify All Services
# ============================================
Write-Host ""
Write-Host "[3/4] Verifying services..." -ForegroundColor Cyan

Start-Sleep -Seconds 5

$services = @(
    @{Name="Website"; Port=3000; URL="http://localhost:3000"},
    @{Name="MYCA App"; Port=3001; URL="http://localhost:3001"},
    @{Name="UniFi Dashboard"; Port=3100; URL="http://localhost:3100"},
    @{Name="n8n Workflows"; Port=5678; URL="http://localhost:5678"},
    @{Name="MINDEX API"; Port=8000; URL="http://localhost:8000/health"},
    @{Name="MAS Orchestrator"; Port=8001; URL="http://localhost:8001/health"}
)

$allRunning = $true
foreach ($svc in $services) {
    if (Test-Port $svc.Port) {
        Write-Host "  $($svc.Name): " -NoNewline
        Write-Host "RUNNING" -ForegroundColor Green -NoNewline
        Write-Host " ($($svc.URL))"
    } else {
        Write-Host "  $($svc.Name): " -NoNewline
        Write-Host "NOT RUNNING" -ForegroundColor Red
        $allRunning = $false
    }
}

# ============================================
# 4. Summary
# ============================================
Write-Host ""
Write-Host "[4/4] Summary" -ForegroundColor Cyan

if ($allRunning) {
    Write-Host ""
    Write-Host "============================================" -ForegroundColor Green
    Write-Host "  ALL SERVICES RUNNING SUCCESSFULLY!        " -ForegroundColor Green
    Write-Host "============================================" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "Some services may not be running." -ForegroundColor Yellow
    Write-Host "Check logs in: $LogDir" -ForegroundColor Gray
}

Write-Host ""
Write-Host "Services will persist after Cursor closes." -ForegroundColor Cyan
Write-Host ""
Write-Host "Quick Links:" -ForegroundColor White
Write-Host "  Website:       http://localhost:3000" -ForegroundColor Gray
Write-Host "  NatureOS:      http://localhost:3000/natureos" -ForegroundColor Gray
Write-Host "  MINDEX:        http://localhost:3000/natureos/mindex" -ForegroundColor Gray
Write-Host "  n8n:           http://localhost:5678" -ForegroundColor Gray
Write-Host "  UniFi:         http://localhost:3100" -ForegroundColor Gray
Write-Host ""
