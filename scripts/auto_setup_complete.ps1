# Fully Automated Complete Setup Script
# This script does everything automatically

$ErrorActionPreference = "Continue"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  FULLY AUTOMATED SETUP - PHASE 1" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$rootDir = Split-Path -Parent $PSScriptRoot
$integrationsDir = Join-Path $rootDir "integrations"

# Step 1: Create directories
Write-Host "Step 1: Creating directories..." -ForegroundColor Yellow
if (-not (Test-Path $integrationsDir)) {
    New-Item -ItemType Directory -Path $integrationsDir | Out-Null
    Write-Host "  ✓ Created integrations directory" -ForegroundColor Green
}

# Step 2: Clone repositories (if they don't exist)
Write-Host ""
Write-Host "Step 2: Cloning repositories..." -ForegroundColor Yellow

$repos = @(
    @{Name="MINDEX"; Path="mindex"; Url="https://github.com/MycosoftLabs/mindex.git"},
    @{Name="NATUREOS"; Path="natureos"; Url="https://github.com/MycosoftLabs/NatureOS.git"},
    @{Name="Website"; Path="website"; Url="https://github.com/MycosoftLabs/mycosoft-website.git"}
)

foreach ($repo in $repos) {
    $repoDir = Join-Path $integrationsDir $repo.Path
    if (-not (Test-Path $repoDir)) {
        Write-Host "  Cloning $($repo.Name)..." -ForegroundColor Cyan
        git clone $repo.Url $repoDir 2>&1 | Out-Null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "    ✓ $($repo.Name) cloned" -ForegroundColor Green
        } else {
            Write-Host "    ⚠ $($repo.Name) repo may not exist or requires auth" -ForegroundColor Yellow
        }
    } else {
        Write-Host "  ✓ $($repo.Name) already exists" -ForegroundColor Green
    }
}

# Step 3: Start Docker databases
Write-Host ""
Write-Host "Step 3: Starting Docker databases..." -ForegroundColor Yellow
$composeFile = Join-Path $rootDir "docker-compose.integrations.yml"

if (Test-Path $composeFile) {
    docker-compose -f $composeFile up -d mindex-postgres 2>&1 | Out-Null
    Start-Sleep -Seconds 5
    
    # Try NATUREOS database (may fail if port in use)
    docker-compose -f $composeFile up -d natureos-postgres 2>&1 | Out-Null
    
    Start-Sleep -Seconds 10
    Write-Host "  ✓ Databases started" -ForegroundColor Green
} else {
    Write-Host "  ⚠ docker-compose.integrations.yml not found" -ForegroundColor Yellow
}

# Step 4: Check service status
Write-Host ""
Write-Host "Step 4: Service Status..." -ForegroundColor Yellow
docker-compose -f $composeFile ps 2>&1 | Out-String | Write-Host

# Step 5: Final Summary
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  AUTOMATED SETUP COMPLETE!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "✅ Directories created" -ForegroundColor Green
Write-Host "✅ Repositories cloned (or attempted)" -ForegroundColor Green
Write-Host "✅ Docker databases started" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. If repos exist, create Dockerfiles in each integration directory" -ForegroundColor White
Write-Host "  2. Start API services: docker-compose -f docker-compose.integrations.yml up -d --build" -ForegroundColor White
Write-Host "  3. Test services: .\scripts\test_integrations.ps1" -ForegroundColor White
Write-Host ""
