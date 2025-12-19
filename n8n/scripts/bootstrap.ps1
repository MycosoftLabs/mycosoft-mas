# MYCA n8n Integration Fabric Bootstrap Script
# This script initializes the n8n stack and imports all workflows

param(
    [switch]$Force,
    [switch]$SkipImport,
    [string]$Env = ".env"
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$N8nRoot = Split-Path -Parent $ScriptDir

Write-Host "==================================" -ForegroundColor Cyan
Write-Host "MYCA n8n Integration Fabric Setup" -ForegroundColor Cyan
Write-Host "==================================" -ForegroundColor Cyan
Write-Host ""

# Check if Docker is running
Write-Host "[1/6] Checking Docker..." -ForegroundColor Yellow
try {
    $dockerCheck = docker info 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: Docker is not running. Please start Docker Desktop." -ForegroundColor Red
        exit 1
    }
    Write-Host "  ✓ Docker is running" -ForegroundColor Green
} catch {
    Write-Host "ERROR: Docker is not available. Please install Docker Desktop." -ForegroundColor Red
    exit 1
}

# Check for .env file
Write-Host "`n[2/6] Checking environment configuration..." -ForegroundColor Yellow
$envPath = Join-Path $N8nRoot $Env
if (-not (Test-Path $envPath)) {
    Write-Host "  ! No .env file found. Creating from template..." -ForegroundColor Yellow
    
    $envTemplate = @"
# MYCA n8n Integration Fabric Environment Configuration
# Generated: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")

# n8n Basic Auth
N8N_USER=admin
N8N_PASSWORD=myca_n8n_secure_$(Get-Random -Minimum 1000 -Maximum 9999)

# Database
POSTGRES_DB=n8n
POSTGRES_USER=n8n
POSTGRES_PASSWORD=n8n_secure_password_$(Get-Random -Minimum 1000 -Maximum 9999)

# Redis
REDIS_PASSWORD=redis_secure_password_$(Get-Random -Minimum 1000 -Maximum 9999)

# n8n Settings
N8N_HOST=localhost
N8N_PROTOCOL=http
N8N_WEBHOOK_URL=http://localhost:5678
TIMEZONE=America/New_York

# Vault (optional - configure if using)
VAULT_ADDR=
VAULT_TOKEN=

# Logging
N8N_LOG_LEVEL=info
"@
    
    Set-Content -Path $envPath -Value $envTemplate
    Write-Host "  ✓ Created .env file at: $envPath" -ForegroundColor Green
    Write-Host "  ! Please review and update credentials before production use!" -ForegroundColor Yellow
} else {
    Write-Host "  ✓ Found .env file" -ForegroundColor Green
}

# Start Docker Compose stack
Write-Host "`n[3/6] Starting n8n stack..." -ForegroundColor Yellow
Push-Location $N8nRoot
try {
    if ($Force) {
        Write-Host "  ! Force flag set - recreating containers..." -ForegroundColor Yellow
        docker-compose down -v 2>&1 | Out-Null
    }
    
    docker-compose up -d
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: Failed to start Docker Compose stack" -ForegroundColor Red
        exit 1
    }
    
    Write-Host "  ✓ Docker Compose stack started" -ForegroundColor Green
} finally {
    Pop-Location
}

# Wait for n8n to be ready
Write-Host "`n[4/6] Waiting for n8n to be ready..." -ForegroundColor Yellow
$maxAttempts = 30
$attempt = 0
$ready = $false

while ($attempt -lt $maxAttempts -and -not $ready) {
    $attempt++
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:5678/healthz" -TimeoutSec 2 -UseBasicParsing 2>&1
        if ($response.StatusCode -eq 200) {
            $ready = $true
        }
    } catch {
        Start-Sleep -Seconds 2
    }
    
    if ($attempt % 5 -eq 0) {
        Write-Host "  ... waiting ($attempt/$maxAttempts)" -ForegroundColor Gray
    }
}

if (-not $ready) {
    Write-Host "ERROR: n8n did not become ready in time" -ForegroundColor Red
    Write-Host "Check logs with: docker-compose logs n8n" -ForegroundColor Yellow
    exit 1
}

Write-Host "  ✓ n8n is ready at http://localhost:5678" -ForegroundColor Green

# Import workflows
if (-not $SkipImport) {
    Write-Host "`n[5/6] Importing workflows..." -ForegroundColor Yellow
    $importScript = Join-Path $ScriptDir "import.ps1"
    if (Test-Path $importScript) {
        & $importScript
        if ($LASTEXITCODE -ne 0) {
            Write-Host "WARNING: Workflow import had issues. Check manually." -ForegroundColor Yellow
        }
    } else {
        Write-Host "  ! Import script not found. Skipping workflow import." -ForegroundColor Yellow
        Write-Host "  ! Import workflows manually via n8n UI" -ForegroundColor Yellow
    }
} else {
    Write-Host "`n[5/6] Skipping workflow import (--SkipImport flag)" -ForegroundColor Gray
}

# Display summary
Write-Host "`n[6/6] Setup complete!" -ForegroundColor Green
Write-Host ""
Write-Host "==================================" -ForegroundColor Cyan
Write-Host "MYCA n8n Integration Fabric" -ForegroundColor Cyan
Write-Host "==================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "n8n UI:        http://localhost:5678" -ForegroundColor White
Write-Host "Command API:   http://localhost:5678/webhook/myca/command" -ForegroundColor White
Write-Host "Event API:     http://localhost:5678/webhook/myca/event" -ForegroundColor White
Write-Host ""
Write-Host "Credentials:" -ForegroundColor Yellow
Write-Host "  Username: admin" -ForegroundColor Gray
Write-Host "  Password: (see .env file)" -ForegroundColor Gray
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. Configure credentials in n8n UI" -ForegroundColor White
Write-Host "  2. Import integration_registry.json" -ForegroundColor White
Write-Host "  3. Test with: curl -X POST http://localhost:5678/webhook/myca/command" -ForegroundColor White
Write-Host ""
Write-Host "Logs:    docker-compose logs -f n8n" -ForegroundColor Gray
Write-Host "Stop:    docker-compose down" -ForegroundColor Gray
Write-Host "Restart: docker-compose restart n8n" -ForegroundColor Gray
Write-Host ""
