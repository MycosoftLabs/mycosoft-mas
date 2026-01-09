# Deploy from mycocomp to Production
# This script deploys code changes from the development machine to production

param(
    [Parameter(Mandatory=$false)]
    [ValidateSet("all", "orchestrator", "website", "agents")]
    [string]$Target = "all",
    
    [switch]$DryRun,
    [switch]$Force,
    [switch]$SkipTests,
    [string]$Branch = "main"
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot

# Production configuration
$PROD_HOST = "192.168.20.10"  # MYCA Core VM
$PROD_USER = "myca"
$PROD_PATH = "/opt/myca"
$WEBSITE_HOST = "192.168.20.11"  # Website VM

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  MYCA Production Deployment" -ForegroundColor Cyan
Write-Host "  From: mycocomp (development)" -ForegroundColor Cyan
Write-Host "  To: Proxmox Production Cluster" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Change to project root
Set-Location $ProjectRoot

# ==============================================
# Pre-flight Checks
# ==============================================
Write-Host "[1/6] Pre-flight Checks..." -ForegroundColor Cyan

# Check Git status
$gitStatus = git status --porcelain
if ($gitStatus -and -not $Force) {
    Write-Host "ERROR: Uncommitted changes detected" -ForegroundColor Red
    Write-Host $gitStatus
    Write-Host "Commit your changes or use -Force to deploy anyway" -ForegroundColor Yellow
    exit 1
}

# Check current branch
$currentBranch = git rev-parse --abbrev-ref HEAD
if ($currentBranch -ne $Branch -and -not $Force) {
    Write-Host "WARNING: Not on $Branch branch (currently on $currentBranch)" -ForegroundColor Yellow
    $confirm = Read-Host "Deploy from $currentBranch? (y/N)"
    if ($confirm -ne "y") {
        exit 0
    }
}

$gitHash = git rev-parse --short HEAD
Write-Host "  Deploying commit: $gitHash from $currentBranch" -ForegroundColor Green

# ==============================================
# Run Tests
# ==============================================
if (-not $SkipTests) {
    Write-Host ""
    Write-Host "[2/6] Running Tests..." -ForegroundColor Cyan
    
    # Run Python tests
    Write-Host "  Running Python tests..." -ForegroundColor White
    & python -m pytest tests/ -q --tb=short
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: Tests failed" -ForegroundColor Red
        exit 1
    }
    Write-Host "  Tests passed!" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "[2/6] Skipping Tests (--SkipTests)" -ForegroundColor Yellow
}

# ==============================================
# Build Docker Images
# ==============================================
Write-Host ""
Write-Host "[3/6] Building Docker Images..." -ForegroundColor Cyan

if ($Target -eq "all" -or $Target -eq "orchestrator") {
    Write-Host "  Building MAS Orchestrator..." -ForegroundColor White
    docker build -t mycosoft/mas-orchestrator:$gitHash -t mycosoft/mas-orchestrator:latest .
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: Build failed" -ForegroundColor Red
        exit 1
    }
}

if ($Target -eq "all" -or $Target -eq "website") {
    Write-Host "  Building Website..." -ForegroundColor White
    docker build -t mycosoft/website:$gitHash -t mycosoft/website:latest -f unifi-dashboard/Dockerfile ./unifi-dashboard
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: Website build failed" -ForegroundColor Red
        exit 1
    }
}

Write-Host "  Images built successfully!" -ForegroundColor Green

# ==============================================
# Push to Registry (or save/load)
# ==============================================
Write-Host ""
Write-Host "[4/6] Transferring Images..." -ForegroundColor Cyan

if ($DryRun) {
    Write-Host "  DRY RUN - Would transfer images to production" -ForegroundColor Yellow
} else {
    # Option 1: Use Docker registry
    # docker push mycosoft/mas-orchestrator:$gitHash
    
    # Option 2: Save and transfer via SSH (for air-gapped networks)
    Write-Host "  Saving images..." -ForegroundColor White
    
    if ($Target -eq "all" -or $Target -eq "orchestrator") {
        docker save mycosoft/mas-orchestrator:latest | gzip > "$env:TEMP\mas-orchestrator.tar.gz"
        Write-Host "  Transferring orchestrator to $PROD_HOST..." -ForegroundColor White
        scp "$env:TEMP\mas-orchestrator.tar.gz" "${PROD_USER}@${PROD_HOST}:/tmp/"
        ssh "${PROD_USER}@${PROD_HOST}" "gunzip -c /tmp/mas-orchestrator.tar.gz | docker load && rm /tmp/mas-orchestrator.tar.gz"
        Remove-Item "$env:TEMP\mas-orchestrator.tar.gz" -Force
    }
    
    if ($Target -eq "all" -or $Target -eq "website") {
        docker save mycosoft/website:latest | gzip > "$env:TEMP\website.tar.gz"
        Write-Host "  Transferring website to $WEBSITE_HOST..." -ForegroundColor White
        scp "$env:TEMP\website.tar.gz" "${PROD_USER}@${WEBSITE_HOST}:/tmp/"
        ssh "${PROD_USER}@${WEBSITE_HOST}" "gunzip -c /tmp/website.tar.gz | docker load && rm /tmp/website.tar.gz"
        Remove-Item "$env:TEMP\website.tar.gz" -Force
    }
}

# ==============================================
# Deploy to Production
# ==============================================
Write-Host ""
Write-Host "[5/6] Deploying to Production..." -ForegroundColor Cyan

if ($DryRun) {
    Write-Host "  DRY RUN - Would deploy to production" -ForegroundColor Yellow
} else {
    # Copy configuration files
    Write-Host "  Syncing configuration..." -ForegroundColor White
    scp config/production.env "${PROD_USER}@${PROD_HOST}:${PROD_PATH}/.env"
    scp config/nginx/mycosoft.conf "${PROD_USER}@${WEBSITE_HOST}:/etc/nginx/sites-available/"
    
    if ($Target -eq "all" -or $Target -eq "orchestrator") {
        Write-Host "  Restarting orchestrator..." -ForegroundColor White
        ssh "${PROD_USER}@${PROD_HOST}" "cd ${PROD_PATH} && docker compose up -d --force-recreate mas-orchestrator"
    }
    
    if ($Target -eq "all" -or $Target -eq "website") {
        Write-Host "  Restarting website..." -ForegroundColor White
        ssh "${PROD_USER}@${WEBSITE_HOST}" "pm2 restart mycosoft-website && sudo nginx -t && sudo systemctl reload nginx"
    }
}

# ==============================================
# Verify Deployment
# ==============================================
Write-Host ""
Write-Host "[6/6] Verifying Deployment..." -ForegroundColor Cyan

if ($DryRun) {
    Write-Host "  DRY RUN - Would verify deployment" -ForegroundColor Yellow
} else {
    Start-Sleep -Seconds 10
    
    if ($Target -eq "all" -or $Target -eq "orchestrator") {
        Write-Host "  Checking orchestrator health..." -ForegroundColor White
        $health = Invoke-RestMethod -Uri "http://${PROD_HOST}:8001/health" -TimeoutSec 10 -ErrorAction SilentlyContinue
        if ($health.status -eq "healthy") {
            Write-Host "  [OK] Orchestrator is healthy" -ForegroundColor Green
        } else {
            Write-Host "  [FAIL] Orchestrator health check failed" -ForegroundColor Red
        }
    }
    
    if ($Target -eq "all" -or $Target -eq "website") {
        Write-Host "  Checking website..." -ForegroundColor White
        $webCheck = Invoke-WebRequest -Uri "http://${WEBSITE_HOST}:3000" -TimeoutSec 10 -ErrorAction SilentlyContinue
        if ($webCheck.StatusCode -eq 200) {
            Write-Host "  [OK] Website is responding" -ForegroundColor Green
        } else {
            Write-Host "  [FAIL] Website check failed" -ForegroundColor Red
        }
    }
}

# ==============================================
# Summary
# ==============================================
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
if ($DryRun) {
    Write-Host "  DRY RUN Complete" -ForegroundColor Yellow
} else {
    Write-Host "  Deployment Complete!" -ForegroundColor Green
}
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Deployed: $gitHash ($currentBranch)" -ForegroundColor White
Write-Host "Target:   $Target" -ForegroundColor White
Write-Host ""
Write-Host "Production URLs:" -ForegroundColor White
Write-Host "  MYCA API:  http://${PROD_HOST}:8001" -ForegroundColor White
Write-Host "  Website:   http://${WEBSITE_HOST}:3000" -ForegroundColor White
Write-Host "  External:  https://mycosoft.com" -ForegroundColor White
