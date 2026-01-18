# PowerShell Script for Codebase Transfer
# Run this on Windows machine to transfer codebase to VM1

param(
    [string]$VM1IP = "192.168.1.100",
    [string]$VM1User = "mycosoft",
    [string]$RemoteDir = "/opt/mycosoft"
)

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Mycosoft Codebase Transfer" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# Check if SSH is available
if (-not (Get-Command ssh -ErrorAction SilentlyContinue)) {
    Write-Host "ERROR: SSH not found. Install OpenSSH or use WSL." -ForegroundColor Red
    exit 1
}

# Check if rsync is available (preferred)
$useRsync = $false
if (Get-Command rsync -ErrorAction SilentlyContinue) {
    $useRsync = $true
    Write-Host "Using rsync for transfer (faster)" -ForegroundColor Green
} else {
    Write-Host "Using SCP for transfer (rsync not available)" -ForegroundColor Yellow
    Write-Host "Consider installing rsync via WSL for better performance" -ForegroundColor Yellow
}

# Source directories
$masSource = "C:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas"
$websiteSource = "C:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website"

# Verify source directories exist
if (-not (Test-Path $masSource)) {
    Write-Host "ERROR: MAS source directory not found: $masSource" -ForegroundColor Red
    exit 1
}

Write-Host "Source: $masSource" -ForegroundColor Gray
Write-Host "Target: ${VM1User}@${VM1IP}:${RemoteDir}" -ForegroundColor Gray
Write-Host ""

# Test SSH connection
Write-Host "[1/3] Testing SSH connection..." -ForegroundColor Yellow
$testConnection = ssh -o ConnectTimeout=5 -o BatchMode=yes "${VM1User}@${VM1IP}" "echo 'connected'" 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "WARNING: SSH connection test failed. You may need to enter password." -ForegroundColor Yellow
    Write-Host "Continuing anyway..." -ForegroundColor Yellow
} else {
    Write-Host "SSH connection successful" -ForegroundColor Green
}

# Transfer MAS codebase
Write-Host "[2/3] Transferring MAS codebase..." -ForegroundColor Yellow
if ($useRsync) {
    # Use rsync (if available via WSL)
    wsl rsync -avz --progress `
        --exclude 'node_modules' `
        --exclude '.next' `
        --exclude 'venv*' `
        --exclude '__pycache__' `
        --exclude '*.pyc' `
        --exclude '.git' `
        --exclude '*.log' `
        "/mnt/c/Users/admin2/Desktop/MYCOSOFT/CODE/MAS/mycosoft-mas/" `
        "${VM1User}@${VM1IP}:${RemoteDir}/"
} else {
    # Use SCP
    scp -r "$masSource\*" "${VM1User}@${VM1IP}:${RemoteDir}/"
}

if ($LASTEXITCODE -eq 0) {
    Write-Host "MAS codebase transferred successfully" -ForegroundColor Green
} else {
    Write-Host "ERROR: MAS codebase transfer failed" -ForegroundColor Red
    exit 1
}

# Transfer website codebase (if exists)
if (Test-Path $websiteSource) {
    Write-Host "[3/3] Transferring website codebase..." -ForegroundColor Yellow
    if ($useRsync) {
        wsl rsync -avz --progress `
            --exclude 'node_modules' `
            --exclude '.next' `
            --exclude '.git' `
            "/mnt/c/Users/admin2/Desktop/MYCOSOFT/CODE/WEBSITE/website/" `
            "${VM1User}@${VM1IP}:${RemoteDir}/website/"
    } else {
        scp -r "$websiteSource\*" "${VM1User}@${VM1IP}:${RemoteDir}/website/"
    }
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Website codebase transferred successfully" -ForegroundColor Green
    } else {
        Write-Host "WARNING: Website codebase transfer failed" -ForegroundColor Yellow
    }
} else {
    Write-Host "[3/3] Website codebase not found, skipping..." -ForegroundColor Gray
}

Write-Host ""
Write-Host "==========================================" -ForegroundColor Green
Write-Host "Transfer completed!" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "  1. SSH to VM1: ssh ${VM1User}@${VM1IP}" -ForegroundColor White
Write-Host "  2. Verify files: ls -la ${RemoteDir}" -ForegroundColor White
Write-Host "  3. Run setup: cd ${RemoteDir} && ./migration/setup-production.sh" -ForegroundColor White
