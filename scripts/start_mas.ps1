# ============================================================================
# MYCOSOFT MAS Startup Script
# ============================================================================
# This script starts the complete MYCOSOFT MAS platform including:
# - Infrastructure (PostgreSQL, Redis, Qdrant)
# - MAS Orchestrator API
# - Voice Integration (Whisper STT, Ollama LLM, TTS)
# - Dashboards (MYCA Next.js, Voice UI)
# - Monitoring (Prometheus, Grafana)
# - Workflow Automation (n8n)
# ============================================================================

param (
    [string]$Profile = "default",
    [switch]$Rebuild,
    [switch]$Verify,
    [switch]$Verbose
)

$ErrorActionPreference = "Stop"
$PROJECT_NAME = "omc"

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  MYCOSOFT MAS Platform Startup" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# Function to check if a port is in use
function Test-Port {
    param([int]$Port)
    $connection = Test-NetConnection -ComputerName localhost -Port $Port -WarningAction SilentlyContinue
    return $connection.TcpTestSucceeded
}

# Check Docker is running
try {
    docker info | Out-Null
} catch {
    Write-Host "[ERROR] Docker is not running. Please start Docker Desktop." -ForegroundColor Red
    exit 1
}

# Determine which profiles to use
$profiles = @()
if ($Profile -eq "full" -or $Profile -eq "all") {
    $profiles = @("observability", "local-llm")
}
elseif ($Profile -eq "voice") {
    $profiles = @()  # Voice services are default
}
elseif ($Profile -eq "observability") {
    $profiles = @("observability")
}

# Build command
$composeArgs = @("-p", $PROJECT_NAME)
foreach ($p in $profiles) {
    $composeArgs += @("--profile", $p)
}
$composeArgs += @("up", "-d")

if ($Rebuild) {
    $composeArgs += "--build"
}

Write-Host "[1/5] Starting infrastructure services..." -ForegroundColor Yellow
docker-compose -p $PROJECT_NAME up -d redis postgres qdrant
Start-Sleep -Seconds 5

Write-Host "[2/5] Starting Ollama LLM..." -ForegroundColor Yellow
docker-compose -p $PROJECT_NAME up -d ollama
Start-Sleep -Seconds 10

# Pull the LLM model if not already present
Write-Host "      Ensuring LLM model is available..."
docker exec "$PROJECT_NAME-ollama-1" ollama pull llama3.2:3b 2>$null | Out-Null

Write-Host "[3/5] Starting voice services (Whisper STT, TTS)..." -ForegroundColor Yellow
docker-compose -p $PROJECT_NAME up -d whisper openedai-speech tts

Write-Host "[4/5] Starting MAS Orchestrator..." -ForegroundColor Yellow
if ($Rebuild) {
    docker-compose -p $PROJECT_NAME up -d --build mas-orchestrator
} else {
    docker-compose -p $PROJECT_NAME up -d mas-orchestrator
}
Start-Sleep -Seconds 10

Write-Host "[5/5] Starting dashboards and services..." -ForegroundColor Yellow
docker-compose -p $PROJECT_NAME up -d myca-app voice-ui n8n

if ($profiles -contains "observability") {
    Write-Host "      Starting observability stack (Prometheus, Grafana)..."
    docker-compose -p $PROJECT_NAME --profile observability up -d prometheus grafana
}

Start-Sleep -Seconds 5

Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host "  MYCOSOFT MAS Platform Started!" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host ""
Write-Host "  Service URLs:" -ForegroundColor White
Write-Host "  - MAS API:          http://localhost:8001" -ForegroundColor Gray
Write-Host "  - MYCA Dashboard:   http://localhost:3001" -ForegroundColor Gray
Write-Host "  - Voice UI:         http://localhost:8090" -ForegroundColor Gray
Write-Host "  - n8n Workflows:    http://localhost:5678" -ForegroundColor Gray
Write-Host "  - Grafana:          http://localhost:3000 (admin/admin)" -ForegroundColor Gray
Write-Host "  - Prometheus:       http://localhost:9090" -ForegroundColor Gray
Write-Host ""
Write-Host "  Quick Health Check:" -ForegroundColor White
try {
    $health = Invoke-RestMethod -Uri "http://localhost:8001/health" -TimeoutSec 10
    Write-Host "  - MAS Orchestrator: OK" -ForegroundColor Green
} catch {
    Write-Host "  - MAS Orchestrator: Starting..." -ForegroundColor Yellow
}
Write-Host ""

if ($Verify) {
    Write-Host "  Running full verification..." -ForegroundColor Yellow
    python scripts/verify_mas_complete.py
}

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  Talk to MYCA: http://localhost:8090" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
