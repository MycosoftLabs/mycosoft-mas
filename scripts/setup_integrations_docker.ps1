# Setup script for MINDEX, NATUREOS, and WEBSITE Docker services
# This script helps clone repositories and set up Docker services

param(
    [switch]$SkipClone,
    [switch]$BuildOnly,
    [string]$MindexRepo = "https://github.com/MycosoftLabs/mindex.git",
    [string]$NatureOSRepo = "https://github.com/MycosoftLabs/NatureOS.git",
    [string]$WebsiteRepo = "https://github.com/MycosoftLabs/mycosoft-website.git"
)

$ErrorActionPreference = "Stop"

Write-Host "=== MYCOSOFT Integration Services Setup ===" -ForegroundColor Cyan
Write-Host ""

$rootDir = Split-Path -Parent $PSScriptRoot
$integrationsDir = Join-Path $rootDir "integrations"

# Create integrations directory
if (-not (Test-Path $integrationsDir)) {
    New-Item -ItemType Directory -Path $integrationsDir | Out-Null
    Write-Host "Created integrations directory: $integrationsDir" -ForegroundColor Green
}

# Clone repositories if not skipping
if (-not $SkipClone) {
    Write-Host "=== Cloning Repositories ===" -ForegroundColor Yellow
    
    # Clone MINDEX
    $mindexDir = Join-Path $integrationsDir "mindex"
    if (-not (Test-Path $mindexDir)) {
        Write-Host "Cloning MINDEX..." -ForegroundColor Cyan
        git clone $MindexRepo $mindexDir
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✓ MINDEX cloned" -ForegroundColor Green
        } else {
            Write-Host "✗ Failed to clone MINDEX" -ForegroundColor Red
        }
    } else {
        Write-Host "MINDEX directory already exists, skipping clone" -ForegroundColor Yellow
    }
    
    # Clone NATUREOS
    $natureosDir = Join-Path $integrationsDir "natureos"
    if (-not (Test-Path $natureosDir)) {
        Write-Host "Cloning NATUREOS..." -ForegroundColor Cyan
        git clone $NatureOSRepo $natureosDir
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✓ NATUREOS cloned" -ForegroundColor Green
        } else {
            Write-Host "✗ Failed to clone NATUREOS" -ForegroundColor Red
        }
    } else {
        Write-Host "NATUREOS directory already exists, skipping clone" -ForegroundColor Yellow
    }
    
    # Clone Website
    $websiteDir = Join-Path $integrationsDir "website"
    if (-not (Test-Path $websiteDir)) {
        Write-Host "Cloning Website..." -ForegroundColor Cyan
        git clone $WebsiteRepo $websiteDir
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✓ Website cloned" -ForegroundColor Green
        } else {
            Write-Host "✗ Failed to clone Website" -ForegroundColor Red
        }
    } else {
        Write-Host "Website directory already exists, skipping clone" -ForegroundColor Yellow
    }
}

# Build and start Docker services
Write-Host ""
Write-Host "=== Building Docker Services ===" -ForegroundColor Yellow

$composeFile = Join-Path $rootDir "docker-compose.integrations.yml"

if (Test-Path $composeFile) {
    Write-Host "Starting Docker Compose services..." -ForegroundColor Cyan
    docker-compose -f $composeFile up -d --build
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host "✓ Docker services started successfully!" -ForegroundColor Green
        Write-Host ""
        Write-Host "Services available at:" -ForegroundColor Cyan
        Write-Host "  - MINDEX API: http://localhost:8000" -ForegroundColor White
        Write-Host "  - MINDEX Database: localhost:5432" -ForegroundColor White
        Write-Host "  - NATUREOS API: http://localhost:8002" -ForegroundColor White
        Write-Host "  - NATUREOS Database: localhost:5434" -ForegroundColor White
        Write-Host "  - Website: http://localhost:3001" -ForegroundColor White
        Write-Host ""
        Write-Host "To view logs: docker-compose -f $composeFile logs -f" -ForegroundColor Yellow
        Write-Host "To stop: docker-compose -f $composeFile down" -ForegroundColor Yellow
    } else {
        Write-Host "✗ Failed to start Docker services" -ForegroundColor Red
        Write-Host "Check the error messages above and ensure:" -ForegroundColor Yellow
        Write-Host "  1. Docker Desktop is running" -ForegroundColor Yellow
        Write-Host "  2. Repositories are cloned in integrations/ directory" -ForegroundColor Yellow
        Write-Host "  3. Dockerfiles exist in each integration directory" -ForegroundColor Yellow
        exit 1
    }
} else {
    Write-Host "✗ docker-compose.integrations.yml not found at: $composeFile" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "=== Setup Complete ===" -ForegroundColor Green
