# Sync Development Data to/from NAS
# This script syncs data between mycocomp and the NAS storage

param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("push", "pull", "status")]
    [string]$Action,
    
    [ValidateSet("all", "models", "configs", "data")]
    [string]$Target = "all",
    
    [switch]$DryRun,
    [switch]$Force
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot

# Configuration
$NAS_DRIVE = "M:"
$NAS_DEV_PATH = "$NAS_DRIVE\dev"
$NAS_SHARED_PATH = "$NAS_DRIVE\shared"
$LOCAL_DATA_PATH = "$ProjectRoot\data"
$LOCAL_MODELS_PATH = "$ProjectRoot\models"
$LOCAL_CONFIG_PATH = "$ProjectRoot\config"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  MYCA Dev Data Sync" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if NAS is mounted
if (-not (Test-Path $NAS_DRIVE)) {
    Write-Host "ERROR: NAS not mounted at $NAS_DRIVE" -ForegroundColor Red
    Write-Host "Run: .\scripts\mount_nas.ps1" -ForegroundColor Yellow
    exit 1
}

Write-Host "NAS mounted at $NAS_DRIVE" -ForegroundColor Green
Write-Host ""

function Sync-Directory {
    param(
        [string]$Source,
        [string]$Destination,
        [string]$Name,
        [switch]$DryRun
    )
    
    Write-Host "Syncing $Name..." -ForegroundColor Cyan
    Write-Host "  From: $Source" -ForegroundColor DarkGray
    Write-Host "  To:   $Destination" -ForegroundColor DarkGray
    
    if (-not (Test-Path $Source)) {
        Write-Host "  Source does not exist, skipping" -ForegroundColor Yellow
        return
    }
    
    if (-not (Test-Path $Destination)) {
        if ($DryRun) {
            Write-Host "  Would create: $Destination" -ForegroundColor Yellow
        } else {
            New-Item -Path $Destination -ItemType Directory -Force | Out-Null
        }
    }
    
    # Use robocopy for efficient sync
    $robocopyArgs = @(
        $Source,
        $Destination,
        "/MIR",     # Mirror
        "/MT:4",    # 4 threads
        "/R:2",     # 2 retries
        "/W:5",     # 5 second wait
        "/NP",      # No progress
        "/NDL",     # No directory list
        "/NFL"      # No file list
    )
    
    if ($DryRun) {
        $robocopyArgs += "/L"  # List only
        Write-Host "  DRY RUN:" -ForegroundColor Yellow
    }
    
    $result = robocopy @robocopyArgs 2>&1
    
    # Robocopy exit codes: 0-7 are success, 8+ are failures
    if ($LASTEXITCODE -lt 8) {
        Write-Host "  ✓ Sync complete" -ForegroundColor Green
    } else {
        Write-Host "  ✗ Sync failed (exit code: $LASTEXITCODE)" -ForegroundColor Red
    }
}

function Get-DirectoryStats {
    param([string]$Path)
    
    if (-not (Test-Path $Path)) {
        return @{ Files = 0; Size = "0 B" }
    }
    
    $items = Get-ChildItem -Path $Path -Recurse -File -ErrorAction SilentlyContinue
    $totalSize = ($items | Measure-Object -Property Length -Sum).Sum
    
    if ($totalSize -ge 1GB) {
        $sizeStr = "{0:N2} GB" -f ($totalSize / 1GB)
    } elseif ($totalSize -ge 1MB) {
        $sizeStr = "{0:N2} MB" -f ($totalSize / 1MB)
    } else {
        $sizeStr = "{0:N2} KB" -f ($totalSize / 1KB)
    }
    
    return @{ Files = $items.Count; Size = $sizeStr }
}

switch ($Action) {
    "status" {
        Write-Host "Current Status:" -ForegroundColor Cyan
        Write-Host ""
        
        Write-Host "Local Directories:" -ForegroundColor White
        $localData = Get-DirectoryStats $LOCAL_DATA_PATH
        $localModels = Get-DirectoryStats $LOCAL_MODELS_PATH
        $localConfig = Get-DirectoryStats $LOCAL_CONFIG_PATH
        Write-Host "  data/    - $($localData.Files) files, $($localData.Size)" -ForegroundColor Gray
        Write-Host "  models/  - $($localModels.Files) files, $($localModels.Size)" -ForegroundColor Gray
        Write-Host "  config/  - $($localConfig.Files) files, $($localConfig.Size)" -ForegroundColor Gray
        
        Write-Host ""
        Write-Host "NAS Directories:" -ForegroundColor White
        $nasDevData = Get-DirectoryStats "$NAS_DEV_PATH\data"
        $nasSharedModels = Get-DirectoryStats "$NAS_SHARED_PATH\models"
        $nasSharedConfigs = Get-DirectoryStats "$NAS_SHARED_PATH\configs"
        Write-Host "  dev/data/       - $($nasDevData.Files) files, $($nasDevData.Size)" -ForegroundColor Gray
        Write-Host "  shared/models/  - $($nasSharedModels.Files) files, $($nasSharedModels.Size)" -ForegroundColor Gray
        Write-Host "  shared/configs/ - $($nasSharedConfigs.Files) files, $($nasSharedConfigs.Size)" -ForegroundColor Gray
    }
    
    "push" {
        Write-Host "Pushing local data to NAS..." -ForegroundColor Cyan
        Write-Host ""
        
        if ($Target -eq "all" -or $Target -eq "data") {
            Sync-Directory -Source $LOCAL_DATA_PATH -Destination "$NAS_DEV_PATH\data" -Name "Development Data" -DryRun:$DryRun
        }
        
        if ($Target -eq "all" -or $Target -eq "models") {
            Sync-Directory -Source $LOCAL_MODELS_PATH -Destination "$NAS_SHARED_PATH\models" -Name "AI Models" -DryRun:$DryRun
        }
        
        if ($Target -eq "all" -or $Target -eq "configs") {
            Sync-Directory -Source $LOCAL_CONFIG_PATH -Destination "$NAS_SHARED_PATH\configs" -Name "Configurations" -DryRun:$DryRun
        }
    }
    
    "pull" {
        Write-Host "Pulling NAS data to local..." -ForegroundColor Cyan
        Write-Host ""
        
        if (-not $Force) {
            Write-Host "WARNING: This will overwrite local data" -ForegroundColor Yellow
            $confirm = Read-Host "Continue? (y/N)"
            if ($confirm -ne "y") {
                exit 0
            }
        }
        
        if ($Target -eq "all" -or $Target -eq "data") {
            Sync-Directory -Source "$NAS_DEV_PATH\data" -Destination $LOCAL_DATA_PATH -Name "Development Data" -DryRun:$DryRun
        }
        
        if ($Target -eq "all" -or $Target -eq "models") {
            Sync-Directory -Source "$NAS_SHARED_PATH\models" -Destination $LOCAL_MODELS_PATH -Name "AI Models" -DryRun:$DryRun
        }
        
        if ($Target -eq "all" -or $Target -eq "configs") {
            Sync-Directory -Source "$NAS_SHARED_PATH\configs" -Destination $LOCAL_CONFIG_PATH -Name "Configurations" -DryRun:$DryRun
        }
    }
}

Write-Host ""
Write-Host "Done!" -ForegroundColor Green
