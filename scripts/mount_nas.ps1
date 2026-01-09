# Mount NAS Storage Script for Windows (mycocomp)
# This script mounts the UDM Pro 26TB storage as a network drive

param(
    [string]$DriveLetter = "M",
    [string]$NASAddress = "192.168.0.1",
    [string]$ShareName = "mycosoft",
    [switch]$Persistent = $true,
    [switch]$Force = $false
)

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  MYCA NAS Storage Mount Script" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if drive is already mounted
$existingDrive = Get-PSDrive -Name $DriveLetter -ErrorAction SilentlyContinue

if ($existingDrive) {
    if ($Force) {
        Write-Host "Drive $DriveLetter`: already mounted, removing..." -ForegroundColor Yellow
        Remove-PSDrive -Name $DriveLetter -Force
        net use "${DriveLetter}:" /delete /y 2>$null
    } else {
        Write-Host "Drive $DriveLetter`: is already mounted at $($existingDrive.Root)" -ForegroundColor Green
        Write-Host "Use -Force to remount" -ForegroundColor Yellow
        exit 0
    }
}

# Test network connectivity
Write-Host "Testing connectivity to $NASAddress..." -ForegroundColor Cyan
$pingResult = Test-NetConnection -ComputerName $NASAddress -Port 445 -WarningAction SilentlyContinue

if (-not $pingResult.TcpTestSucceeded) {
    Write-Host "ERROR: Cannot connect to $NASAddress on port 445 (SMB)" -ForegroundColor Red
    Write-Host "Please verify:" -ForegroundColor Yellow
    Write-Host "  1. UDM Pro is online and accessible" -ForegroundColor Yellow
    Write-Host "  2. SMB share is enabled in UniFi OS" -ForegroundColor Yellow
    Write-Host "  3. Firewall allows SMB traffic" -ForegroundColor Yellow
    exit 1
}

Write-Host "Connectivity test passed!" -ForegroundColor Green

# Mount the network drive
$SharePath = "\\$NASAddress\$ShareName"
Write-Host "Mounting $SharePath as $DriveLetter`:..." -ForegroundColor Cyan

try {
    if ($Persistent) {
        # Use net use for persistent mount
        $result = net use "${DriveLetter}:" $SharePath /persistent:yes 2>&1
        if ($LASTEXITCODE -ne 0) {
            throw "net use failed: $result"
        }
    } else {
        # Use New-PSDrive for session mount
        New-PSDrive -Name $DriveLetter -PSProvider FileSystem -Root $SharePath -Scope Global | Out-Null
    }
    
    Write-Host "Successfully mounted $SharePath as $DriveLetter`:" -ForegroundColor Green
} catch {
    Write-Host "ERROR: Failed to mount network drive" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    
    # Check if credentials are needed
    Write-Host ""
    Write-Host "If credentials are required, run:" -ForegroundColor Yellow
    Write-Host "  net use ${DriveLetter}: $SharePath /user:USERNAME PASSWORD /persistent:yes" -ForegroundColor Yellow
    exit 1
}

# Verify mount
Write-Host ""
Write-Host "Verifying mount..." -ForegroundColor Cyan

$drive = Get-PSDrive -Name $DriveLetter -ErrorAction SilentlyContinue
if ($drive) {
    $freeSpace = [math]::Round($drive.Free / 1TB, 2)
    $usedSpace = [math]::Round($drive.Used / 1TB, 2)
    
    Write-Host ""
    Write-Host "Mount Successful!" -ForegroundColor Green
    Write-Host "  Drive: $DriveLetter`:" -ForegroundColor White
    Write-Host "  Path: $SharePath" -ForegroundColor White
    Write-Host "  Free Space: ${freeSpace} TB" -ForegroundColor White
    Write-Host "  Used Space: ${usedSpace} TB" -ForegroundColor White
} else {
    Write-Host "WARNING: Mount may not be complete. Check manually." -ForegroundColor Yellow
}

# Create directory structure if it doesn't exist
Write-Host ""
Write-Host "Checking directory structure..." -ForegroundColor Cyan

$directories = @(
    "${DriveLetter}:\databases",
    "${DriveLetter}:\databases\postgres",
    "${DriveLetter}:\databases\redis",
    "${DriveLetter}:\databases\qdrant",
    "${DriveLetter}:\knowledge",
    "${DriveLetter}:\knowledge\embeddings",
    "${DriveLetter}:\knowledge\documents",
    "${DriveLetter}:\agents",
    "${DriveLetter}:\agents\cycles",
    "${DriveLetter}:\agents\insights",
    "${DriveLetter}:\agents\workloads",
    "${DriveLetter}:\agents\wisdom",
    "${DriveLetter}:\website",
    "${DriveLetter}:\website\static",
    "${DriveLetter}:\website\uploads",
    "${DriveLetter}:\backups",
    "${DriveLetter}:\backups\daily",
    "${DriveLetter}:\backups\weekly",
    "${DriveLetter}:\backups\monthly",
    "${DriveLetter}:\audit",
    "${DriveLetter}:\audit\logs",
    "${DriveLetter}:\dev",
    "${DriveLetter}:\dev\data",
    "${DriveLetter}:\dev\logs",
    "${DriveLetter}:\shared",
    "${DriveLetter}:\shared\models",
    "${DriveLetter}:\shared\configs"
)

$created = 0
foreach ($dir in $directories) {
    if (-not (Test-Path $dir)) {
        New-Item -Path $dir -ItemType Directory -Force | Out-Null
        $created++
    }
}

if ($created -gt 0) {
    Write-Host "Created $created directories" -ForegroundColor Green
} else {
    Write-Host "All directories already exist" -ForegroundColor Green
}

# Set environment variable
Write-Host ""
Write-Host "Setting NAS_STORAGE_PATH environment variable..." -ForegroundColor Cyan
[Environment]::SetEnvironmentVariable("NAS_STORAGE_PATH", "${DriveLetter}:\", "User")
$env:NAS_STORAGE_PATH = "${DriveLetter}:\"
Write-Host "NAS_STORAGE_PATH = ${DriveLetter}:\" -ForegroundColor Green

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  NAS Mount Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "You can now access the NAS at ${DriveLetter}:\" -ForegroundColor White
Write-Host "Environment variable NAS_STORAGE_PATH is set" -ForegroundColor White
