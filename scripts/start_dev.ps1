# Start Development Environment on mycocomp
# This script starts all development services with GPU support

param(
    [switch]$Minimal,       # Start only essential services
    [switch]$WithGPU,       # Include GPU services (Ollama, Whisper)
    [switch]$NoBuild,       # Skip rebuilding images
    [switch]$Detached       # Run in background
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  MYCA Development Environment Startup" -ForegroundColor Cyan
Write-Host "  Machine: mycocomp (RTX 5090)" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Change to project root
Set-Location $ProjectRoot

# Check if NAS is mounted
$NASPath = $env:NAS_STORAGE_PATH
if (-not $NASPath -or -not (Test-Path $NASPath)) {
    Write-Host "NAS storage not mounted. Running mount script..." -ForegroundColor Yellow
    & "$ProjectRoot\scripts\mount_nas.ps1"
}

# Load development environment
if (Test-Path "$ProjectRoot\config\development.env") {
    Write-Host "Loading development environment..." -ForegroundColor Cyan
    Get-Content "$ProjectRoot\config\development.env" | ForEach-Object {
        if ($_ -match '^([^#=]+)=(.*)$') {
            $name = $matches[1].Trim()
            $value = $matches[2].Trim()
            [Environment]::SetEnvironmentVariable($name, $value, "Process")
        }
    }
}

# Build docker compose command
$composeArgs = @()

if ($Detached) {
    $composeArgs += "-d"
}

if (-not $NoBuild) {
    $composeArgs += "--build"
}

# Determine which services to start
if ($Minimal) {
    Write-Host "Starting minimal services (databases only)..." -ForegroundColor Cyan
    $services = @("postgres", "redis", "qdrant")
} elseif ($WithGPU) {
    Write-Host "Starting full stack with GPU services..." -ForegroundColor Cyan
    $services = @(
        "postgres", "redis", "qdrant",
        "ollama", "whisper",
        "mas-orchestrator", "n8n",
        "openedai-speech", "voice-ui"
    )
} else {
    Write-Host "Starting standard development stack..." -ForegroundColor Cyan
    $services = @(
        "postgres", "redis", "qdrant",
        "mas-orchestrator", "n8n"
    )
}

# Check for GPU
$gpuAvailable = $false
try {
    $nvidiaCheck = & nvidia-smi --query-gpu=name --format=csv,noheader 2>$null
    if ($LASTEXITCODE -eq 0) {
        $gpuAvailable = $true
        Write-Host "GPU detected: $nvidiaCheck" -ForegroundColor Green
    }
} catch {
    Write-Host "No NVIDIA GPU detected" -ForegroundColor Yellow
}

if ($WithGPU -and -not $gpuAvailable) {
    Write-Host "WARNING: GPU services requested but no GPU detected!" -ForegroundColor Yellow
    Write-Host "GPU services may fail to start." -ForegroundColor Yellow
}

# Start services
Write-Host ""
Write-Host "Starting services: $($services -join ', ')" -ForegroundColor Cyan
Write-Host ""

$composeCmd = "docker compose up $($composeArgs -join ' ') $($services -join ' ')"
Write-Host "Running: $composeCmd" -ForegroundColor DarkGray
Invoke-Expression $composeCmd

if ($Detached) {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "  Development Environment Started!" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Services:" -ForegroundColor White
    Write-Host "  MAS API:     http://localhost:8001" -ForegroundColor White
    Write-Host "  Dashboard:   http://localhost:3100" -ForegroundColor White
    Write-Host "  N8N:         http://localhost:5678" -ForegroundColor White
    if ($WithGPU) {
        Write-Host "  Ollama:      http://localhost:11434" -ForegroundColor White
        Write-Host "  Whisper:     http://localhost:8765" -ForegroundColor White
    }
    Write-Host ""
    Write-Host "To view logs: docker compose logs -f" -ForegroundColor DarkGray
    Write-Host "To stop:      docker compose down" -ForegroundColor DarkGray
}
