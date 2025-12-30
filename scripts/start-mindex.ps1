# MINDEX Startup Script
# Starts the MINDEX fungal knowledge service with Docker

param(
    [switch]$Build,
    [switch]$Detached,
    [string]$NasPath = "",
    [switch]$Logs,
    [switch]$Stop
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RootDir = Split-Path -Parent $ScriptDir

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  MINDEX - Mycological Index Service   " -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# Change to root directory
Set-Location $RootDir

# Handle stop command
if ($Stop) {
    Write-Host "`nStopping MINDEX containers..." -ForegroundColor Yellow
    docker-compose -f docker-compose.mindex.yml down
    Write-Host "MINDEX stopped." -ForegroundColor Green
    exit 0
}

# Handle logs command
if ($Logs) {
    Write-Host "`nShowing MINDEX logs..." -ForegroundColor Yellow
    docker-compose -f docker-compose.mindex.yml logs -f mindex
    exit 0
}

# Check if NAS path is set
if ($NasPath) {
    $env:MINDEX_HOST_PATH = $NasPath
    Write-Host "`nUsing NAS path: $NasPath" -ForegroundColor Green
} elseif ($env:MINDEX_HOST_PATH) {
    Write-Host "`nUsing configured NAS path: $env:MINDEX_HOST_PATH" -ForegroundColor Green
} else {
    Write-Host "`nNo NAS path configured, using local data directory" -ForegroundColor Yellow
    $env:MINDEX_HOST_PATH = "$RootDir\data\mindex"
    
    # Create local data directory if it doesn't exist
    if (-not (Test-Path $env:MINDEX_HOST_PATH)) {
        New-Item -ItemType Directory -Path $env:MINDEX_HOST_PATH -Force | Out-Null
        Write-Host "Created: $env:MINDEX_HOST_PATH" -ForegroundColor Gray
    }
}

# Check Docker is running
Write-Host "`nChecking Docker..." -ForegroundColor Yellow
$dockerStatus = docker info 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Docker is not running. Please start Docker Desktop." -ForegroundColor Red
    exit 1
}
Write-Host "Docker is running." -ForegroundColor Green

# Create network if it doesn't exist
Write-Host "`nEnsuring network exists..." -ForegroundColor Yellow
$networks = docker network ls --filter name=mycosoft-network --format "{{.Name}}"
if ($networks -notcontains "mycosoft-network") {
    docker network create mycosoft-network
    Write-Host "Created mycosoft-network" -ForegroundColor Green
} else {
    Write-Host "Network already exists" -ForegroundColor Green
}

# Build if requested
if ($Build) {
    Write-Host "`nBuilding MINDEX container..." -ForegroundColor Yellow
    docker-compose -f docker-compose.mindex.yml build --no-cache
}

# Start MINDEX
Write-Host "`nStarting MINDEX..." -ForegroundColor Yellow

if ($Detached) {
    docker-compose -f docker-compose.mindex.yml up -d
    Write-Host "`nMINDEX started in background." -ForegroundColor Green
    Write-Host "`nService endpoints:" -ForegroundColor Cyan
    Write-Host "  API:    http://localhost:8000" -ForegroundColor White
    Write-Host "  Health: http://localhost:8000/health" -ForegroundColor White
    Write-Host "  Stats:  http://localhost:8000/api/mindex/stats" -ForegroundColor White
    Write-Host "`nView logs: .\scripts\start-mindex.ps1 -Logs" -ForegroundColor Gray
    Write-Host "Stop:      .\scripts\start-mindex.ps1 -Stop" -ForegroundColor Gray
} else {
    docker-compose -f docker-compose.mindex.yml up
}

# MINDEX Startup Script
# Starts the MINDEX fungal knowledge service with Docker

param(
    [switch]$Build,
    [switch]$Detached,
    [string]$NasPath = "",
    [switch]$Logs,
    [switch]$Stop
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RootDir = Split-Path -Parent $ScriptDir

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  MINDEX - Mycological Index Service   " -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# Change to root directory
Set-Location $RootDir

# Handle stop command
if ($Stop) {
    Write-Host "`nStopping MINDEX containers..." -ForegroundColor Yellow
    docker-compose -f docker-compose.mindex.yml down
    Write-Host "MINDEX stopped." -ForegroundColor Green
    exit 0
}

# Handle logs command
if ($Logs) {
    Write-Host "`nShowing MINDEX logs..." -ForegroundColor Yellow
    docker-compose -f docker-compose.mindex.yml logs -f mindex
    exit 0
}

# Check if NAS path is set
if ($NasPath) {
    $env:MINDEX_HOST_PATH = $NasPath
    Write-Host "`nUsing NAS path: $NasPath" -ForegroundColor Green
} elseif ($env:MINDEX_HOST_PATH) {
    Write-Host "`nUsing configured NAS path: $env:MINDEX_HOST_PATH" -ForegroundColor Green
} else {
    Write-Host "`nNo NAS path configured, using local data directory" -ForegroundColor Yellow
    $env:MINDEX_HOST_PATH = "$RootDir\data\mindex"
    
    # Create local data directory if it doesn't exist
    if (-not (Test-Path $env:MINDEX_HOST_PATH)) {
        New-Item -ItemType Directory -Path $env:MINDEX_HOST_PATH -Force | Out-Null
        Write-Host "Created: $env:MINDEX_HOST_PATH" -ForegroundColor Gray
    }
}

# Check Docker is running
Write-Host "`nChecking Docker..." -ForegroundColor Yellow
$dockerStatus = docker info 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Docker is not running. Please start Docker Desktop." -ForegroundColor Red
    exit 1
}
Write-Host "Docker is running." -ForegroundColor Green

# Create network if it doesn't exist
Write-Host "`nEnsuring network exists..." -ForegroundColor Yellow
$networks = docker network ls --filter name=mycosoft-network --format "{{.Name}}"
if ($networks -notcontains "mycosoft-network") {
    docker network create mycosoft-network
    Write-Host "Created mycosoft-network" -ForegroundColor Green
} else {
    Write-Host "Network already exists" -ForegroundColor Green
}

# Build if requested
if ($Build) {
    Write-Host "`nBuilding MINDEX container..." -ForegroundColor Yellow
    docker-compose -f docker-compose.mindex.yml build --no-cache
}

# Start MINDEX
Write-Host "`nStarting MINDEX..." -ForegroundColor Yellow

if ($Detached) {
    docker-compose -f docker-compose.mindex.yml up -d
    Write-Host "`nMINDEX started in background." -ForegroundColor Green
    Write-Host "`nService endpoints:" -ForegroundColor Cyan
    Write-Host "  API:    http://localhost:8000" -ForegroundColor White
    Write-Host "  Health: http://localhost:8000/health" -ForegroundColor White
    Write-Host "  Stats:  http://localhost:8000/api/mindex/stats" -ForegroundColor White
    Write-Host "`nView logs: .\scripts\start-mindex.ps1 -Logs" -ForegroundColor Gray
    Write-Host "Stop:      .\scripts\start-mindex.ps1 -Stop" -ForegroundColor Gray
} else {
    docker-compose -f docker-compose.mindex.yml up
}


# MINDEX Startup Script
# Starts the MINDEX fungal knowledge service with Docker

param(
    [switch]$Build,
    [switch]$Detached,
    [string]$NasPath = "",
    [switch]$Logs,
    [switch]$Stop
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RootDir = Split-Path -Parent $ScriptDir

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  MINDEX - Mycological Index Service   " -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# Change to root directory
Set-Location $RootDir

# Handle stop command
if ($Stop) {
    Write-Host "`nStopping MINDEX containers..." -ForegroundColor Yellow
    docker-compose -f docker-compose.mindex.yml down
    Write-Host "MINDEX stopped." -ForegroundColor Green
    exit 0
}

# Handle logs command
if ($Logs) {
    Write-Host "`nShowing MINDEX logs..." -ForegroundColor Yellow
    docker-compose -f docker-compose.mindex.yml logs -f mindex
    exit 0
}

# Check if NAS path is set
if ($NasPath) {
    $env:MINDEX_HOST_PATH = $NasPath
    Write-Host "`nUsing NAS path: $NasPath" -ForegroundColor Green
} elseif ($env:MINDEX_HOST_PATH) {
    Write-Host "`nUsing configured NAS path: $env:MINDEX_HOST_PATH" -ForegroundColor Green
} else {
    Write-Host "`nNo NAS path configured, using local data directory" -ForegroundColor Yellow
    $env:MINDEX_HOST_PATH = "$RootDir\data\mindex"
    
    # Create local data directory if it doesn't exist
    if (-not (Test-Path $env:MINDEX_HOST_PATH)) {
        New-Item -ItemType Directory -Path $env:MINDEX_HOST_PATH -Force | Out-Null
        Write-Host "Created: $env:MINDEX_HOST_PATH" -ForegroundColor Gray
    }
}

# Check Docker is running
Write-Host "`nChecking Docker..." -ForegroundColor Yellow
$dockerStatus = docker info 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Docker is not running. Please start Docker Desktop." -ForegroundColor Red
    exit 1
}
Write-Host "Docker is running." -ForegroundColor Green

# Create network if it doesn't exist
Write-Host "`nEnsuring network exists..." -ForegroundColor Yellow
$networks = docker network ls --filter name=mycosoft-network --format "{{.Name}}"
if ($networks -notcontains "mycosoft-network") {
    docker network create mycosoft-network
    Write-Host "Created mycosoft-network" -ForegroundColor Green
} else {
    Write-Host "Network already exists" -ForegroundColor Green
}

# Build if requested
if ($Build) {
    Write-Host "`nBuilding MINDEX container..." -ForegroundColor Yellow
    docker-compose -f docker-compose.mindex.yml build --no-cache
}

# Start MINDEX
Write-Host "`nStarting MINDEX..." -ForegroundColor Yellow

if ($Detached) {
    docker-compose -f docker-compose.mindex.yml up -d
    Write-Host "`nMINDEX started in background." -ForegroundColor Green
    Write-Host "`nService endpoints:" -ForegroundColor Cyan
    Write-Host "  API:    http://localhost:8000" -ForegroundColor White
    Write-Host "  Health: http://localhost:8000/health" -ForegroundColor White
    Write-Host "  Stats:  http://localhost:8000/api/mindex/stats" -ForegroundColor White
    Write-Host "`nView logs: .\scripts\start-mindex.ps1 -Logs" -ForegroundColor Gray
    Write-Host "Stop:      .\scripts\start-mindex.ps1 -Stop" -ForegroundColor Gray
} else {
    docker-compose -f docker-compose.mindex.yml up
}

# MINDEX Startup Script
# Starts the MINDEX fungal knowledge service with Docker

param(
    [switch]$Build,
    [switch]$Detached,
    [string]$NasPath = "",
    [switch]$Logs,
    [switch]$Stop
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RootDir = Split-Path -Parent $ScriptDir

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  MINDEX - Mycological Index Service   " -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# Change to root directory
Set-Location $RootDir

# Handle stop command
if ($Stop) {
    Write-Host "`nStopping MINDEX containers..." -ForegroundColor Yellow
    docker-compose -f docker-compose.mindex.yml down
    Write-Host "MINDEX stopped." -ForegroundColor Green
    exit 0
}

# Handle logs command
if ($Logs) {
    Write-Host "`nShowing MINDEX logs..." -ForegroundColor Yellow
    docker-compose -f docker-compose.mindex.yml logs -f mindex
    exit 0
}

# Check if NAS path is set
if ($NasPath) {
    $env:MINDEX_HOST_PATH = $NasPath
    Write-Host "`nUsing NAS path: $NasPath" -ForegroundColor Green
} elseif ($env:MINDEX_HOST_PATH) {
    Write-Host "`nUsing configured NAS path: $env:MINDEX_HOST_PATH" -ForegroundColor Green
} else {
    Write-Host "`nNo NAS path configured, using local data directory" -ForegroundColor Yellow
    $env:MINDEX_HOST_PATH = "$RootDir\data\mindex"
    
    # Create local data directory if it doesn't exist
    if (-not (Test-Path $env:MINDEX_HOST_PATH)) {
        New-Item -ItemType Directory -Path $env:MINDEX_HOST_PATH -Force | Out-Null
        Write-Host "Created: $env:MINDEX_HOST_PATH" -ForegroundColor Gray
    }
}

# Check Docker is running
Write-Host "`nChecking Docker..." -ForegroundColor Yellow
$dockerStatus = docker info 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Docker is not running. Please start Docker Desktop." -ForegroundColor Red
    exit 1
}
Write-Host "Docker is running." -ForegroundColor Green

# Create network if it doesn't exist
Write-Host "`nEnsuring network exists..." -ForegroundColor Yellow
$networks = docker network ls --filter name=mycosoft-network --format "{{.Name}}"
if ($networks -notcontains "mycosoft-network") {
    docker network create mycosoft-network
    Write-Host "Created mycosoft-network" -ForegroundColor Green
} else {
    Write-Host "Network already exists" -ForegroundColor Green
}

# Build if requested
if ($Build) {
    Write-Host "`nBuilding MINDEX container..." -ForegroundColor Yellow
    docker-compose -f docker-compose.mindex.yml build --no-cache
}

# Start MINDEX
Write-Host "`nStarting MINDEX..." -ForegroundColor Yellow

if ($Detached) {
    docker-compose -f docker-compose.mindex.yml up -d
    Write-Host "`nMINDEX started in background." -ForegroundColor Green
    Write-Host "`nService endpoints:" -ForegroundColor Cyan
    Write-Host "  API:    http://localhost:8000" -ForegroundColor White
    Write-Host "  Health: http://localhost:8000/health" -ForegroundColor White
    Write-Host "  Stats:  http://localhost:8000/api/mindex/stats" -ForegroundColor White
    Write-Host "`nView logs: .\scripts\start-mindex.ps1 -Logs" -ForegroundColor Gray
    Write-Host "Stop:      .\scripts\start-mindex.ps1 -Stop" -ForegroundColor Gray
} else {
    docker-compose -f docker-compose.mindex.yml up
}





# MINDEX Startup Script
# Starts the MINDEX fungal knowledge service with Docker

param(
    [switch]$Build,
    [switch]$Detached,
    [string]$NasPath = "",
    [switch]$Logs,
    [switch]$Stop
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RootDir = Split-Path -Parent $ScriptDir

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  MINDEX - Mycological Index Service   " -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# Change to root directory
Set-Location $RootDir

# Handle stop command
if ($Stop) {
    Write-Host "`nStopping MINDEX containers..." -ForegroundColor Yellow
    docker-compose -f docker-compose.mindex.yml down
    Write-Host "MINDEX stopped." -ForegroundColor Green
    exit 0
}

# Handle logs command
if ($Logs) {
    Write-Host "`nShowing MINDEX logs..." -ForegroundColor Yellow
    docker-compose -f docker-compose.mindex.yml logs -f mindex
    exit 0
}

# Check if NAS path is set
if ($NasPath) {
    $env:MINDEX_HOST_PATH = $NasPath
    Write-Host "`nUsing NAS path: $NasPath" -ForegroundColor Green
} elseif ($env:MINDEX_HOST_PATH) {
    Write-Host "`nUsing configured NAS path: $env:MINDEX_HOST_PATH" -ForegroundColor Green
} else {
    Write-Host "`nNo NAS path configured, using local data directory" -ForegroundColor Yellow
    $env:MINDEX_HOST_PATH = "$RootDir\data\mindex"
    
    # Create local data directory if it doesn't exist
    if (-not (Test-Path $env:MINDEX_HOST_PATH)) {
        New-Item -ItemType Directory -Path $env:MINDEX_HOST_PATH -Force | Out-Null
        Write-Host "Created: $env:MINDEX_HOST_PATH" -ForegroundColor Gray
    }
}

# Check Docker is running
Write-Host "`nChecking Docker..." -ForegroundColor Yellow
$dockerStatus = docker info 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Docker is not running. Please start Docker Desktop." -ForegroundColor Red
    exit 1
}
Write-Host "Docker is running." -ForegroundColor Green

# Create network if it doesn't exist
Write-Host "`nEnsuring network exists..." -ForegroundColor Yellow
$networks = docker network ls --filter name=mycosoft-network --format "{{.Name}}"
if ($networks -notcontains "mycosoft-network") {
    docker network create mycosoft-network
    Write-Host "Created mycosoft-network" -ForegroundColor Green
} else {
    Write-Host "Network already exists" -ForegroundColor Green
}

# Build if requested
if ($Build) {
    Write-Host "`nBuilding MINDEX container..." -ForegroundColor Yellow
    docker-compose -f docker-compose.mindex.yml build --no-cache
}

# Start MINDEX
Write-Host "`nStarting MINDEX..." -ForegroundColor Yellow

if ($Detached) {
    docker-compose -f docker-compose.mindex.yml up -d
    Write-Host "`nMINDEX started in background." -ForegroundColor Green
    Write-Host "`nService endpoints:" -ForegroundColor Cyan
    Write-Host "  API:    http://localhost:8000" -ForegroundColor White
    Write-Host "  Health: http://localhost:8000/health" -ForegroundColor White
    Write-Host "  Stats:  http://localhost:8000/api/mindex/stats" -ForegroundColor White
    Write-Host "`nView logs: .\scripts\start-mindex.ps1 -Logs" -ForegroundColor Gray
    Write-Host "Stop:      .\scripts\start-mindex.ps1 -Stop" -ForegroundColor Gray
} else {
    docker-compose -f docker-compose.mindex.yml up
}

# MINDEX Startup Script
# Starts the MINDEX fungal knowledge service with Docker

param(
    [switch]$Build,
    [switch]$Detached,
    [string]$NasPath = "",
    [switch]$Logs,
    [switch]$Stop
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RootDir = Split-Path -Parent $ScriptDir

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  MINDEX - Mycological Index Service   " -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# Change to root directory
Set-Location $RootDir

# Handle stop command
if ($Stop) {
    Write-Host "`nStopping MINDEX containers..." -ForegroundColor Yellow
    docker-compose -f docker-compose.mindex.yml down
    Write-Host "MINDEX stopped." -ForegroundColor Green
    exit 0
}

# Handle logs command
if ($Logs) {
    Write-Host "`nShowing MINDEX logs..." -ForegroundColor Yellow
    docker-compose -f docker-compose.mindex.yml logs -f mindex
    exit 0
}

# Check if NAS path is set
if ($NasPath) {
    $env:MINDEX_HOST_PATH = $NasPath
    Write-Host "`nUsing NAS path: $NasPath" -ForegroundColor Green
} elseif ($env:MINDEX_HOST_PATH) {
    Write-Host "`nUsing configured NAS path: $env:MINDEX_HOST_PATH" -ForegroundColor Green
} else {
    Write-Host "`nNo NAS path configured, using local data directory" -ForegroundColor Yellow
    $env:MINDEX_HOST_PATH = "$RootDir\data\mindex"
    
    # Create local data directory if it doesn't exist
    if (-not (Test-Path $env:MINDEX_HOST_PATH)) {
        New-Item -ItemType Directory -Path $env:MINDEX_HOST_PATH -Force | Out-Null
        Write-Host "Created: $env:MINDEX_HOST_PATH" -ForegroundColor Gray
    }
}

# Check Docker is running
Write-Host "`nChecking Docker..." -ForegroundColor Yellow
$dockerStatus = docker info 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Docker is not running. Please start Docker Desktop." -ForegroundColor Red
    exit 1
}
Write-Host "Docker is running." -ForegroundColor Green

# Create network if it doesn't exist
Write-Host "`nEnsuring network exists..." -ForegroundColor Yellow
$networks = docker network ls --filter name=mycosoft-network --format "{{.Name}}"
if ($networks -notcontains "mycosoft-network") {
    docker network create mycosoft-network
    Write-Host "Created mycosoft-network" -ForegroundColor Green
} else {
    Write-Host "Network already exists" -ForegroundColor Green
}

# Build if requested
if ($Build) {
    Write-Host "`nBuilding MINDEX container..." -ForegroundColor Yellow
    docker-compose -f docker-compose.mindex.yml build --no-cache
}

# Start MINDEX
Write-Host "`nStarting MINDEX..." -ForegroundColor Yellow

if ($Detached) {
    docker-compose -f docker-compose.mindex.yml up -d
    Write-Host "`nMINDEX started in background." -ForegroundColor Green
    Write-Host "`nService endpoints:" -ForegroundColor Cyan
    Write-Host "  API:    http://localhost:8000" -ForegroundColor White
    Write-Host "  Health: http://localhost:8000/health" -ForegroundColor White
    Write-Host "  Stats:  http://localhost:8000/api/mindex/stats" -ForegroundColor White
    Write-Host "`nView logs: .\scripts\start-mindex.ps1 -Logs" -ForegroundColor Gray
    Write-Host "Stop:      .\scripts\start-mindex.ps1 -Stop" -ForegroundColor Gray
} else {
    docker-compose -f docker-compose.mindex.yml up
}


# MINDEX Startup Script
# Starts the MINDEX fungal knowledge service with Docker

param(
    [switch]$Build,
    [switch]$Detached,
    [string]$NasPath = "",
    [switch]$Logs,
    [switch]$Stop
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RootDir = Split-Path -Parent $ScriptDir

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  MINDEX - Mycological Index Service   " -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# Change to root directory
Set-Location $RootDir

# Handle stop command
if ($Stop) {
    Write-Host "`nStopping MINDEX containers..." -ForegroundColor Yellow
    docker-compose -f docker-compose.mindex.yml down
    Write-Host "MINDEX stopped." -ForegroundColor Green
    exit 0
}

# Handle logs command
if ($Logs) {
    Write-Host "`nShowing MINDEX logs..." -ForegroundColor Yellow
    docker-compose -f docker-compose.mindex.yml logs -f mindex
    exit 0
}

# Check if NAS path is set
if ($NasPath) {
    $env:MINDEX_HOST_PATH = $NasPath
    Write-Host "`nUsing NAS path: $NasPath" -ForegroundColor Green
} elseif ($env:MINDEX_HOST_PATH) {
    Write-Host "`nUsing configured NAS path: $env:MINDEX_HOST_PATH" -ForegroundColor Green
} else {
    Write-Host "`nNo NAS path configured, using local data directory" -ForegroundColor Yellow
    $env:MINDEX_HOST_PATH = "$RootDir\data\mindex"
    
    # Create local data directory if it doesn't exist
    if (-not (Test-Path $env:MINDEX_HOST_PATH)) {
        New-Item -ItemType Directory -Path $env:MINDEX_HOST_PATH -Force | Out-Null
        Write-Host "Created: $env:MINDEX_HOST_PATH" -ForegroundColor Gray
    }
}

# Check Docker is running
Write-Host "`nChecking Docker..." -ForegroundColor Yellow
$dockerStatus = docker info 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Docker is not running. Please start Docker Desktop." -ForegroundColor Red
    exit 1
}
Write-Host "Docker is running." -ForegroundColor Green

# Create network if it doesn't exist
Write-Host "`nEnsuring network exists..." -ForegroundColor Yellow
$networks = docker network ls --filter name=mycosoft-network --format "{{.Name}}"
if ($networks -notcontains "mycosoft-network") {
    docker network create mycosoft-network
    Write-Host "Created mycosoft-network" -ForegroundColor Green
} else {
    Write-Host "Network already exists" -ForegroundColor Green
}

# Build if requested
if ($Build) {
    Write-Host "`nBuilding MINDEX container..." -ForegroundColor Yellow
    docker-compose -f docker-compose.mindex.yml build --no-cache
}

# Start MINDEX
Write-Host "`nStarting MINDEX..." -ForegroundColor Yellow

if ($Detached) {
    docker-compose -f docker-compose.mindex.yml up -d
    Write-Host "`nMINDEX started in background." -ForegroundColor Green
    Write-Host "`nService endpoints:" -ForegroundColor Cyan
    Write-Host "  API:    http://localhost:8000" -ForegroundColor White
    Write-Host "  Health: http://localhost:8000/health" -ForegroundColor White
    Write-Host "  Stats:  http://localhost:8000/api/mindex/stats" -ForegroundColor White
    Write-Host "`nView logs: .\scripts\start-mindex.ps1 -Logs" -ForegroundColor Gray
    Write-Host "Stop:      .\scripts\start-mindex.ps1 -Stop" -ForegroundColor Gray
} else {
    docker-compose -f docker-compose.mindex.yml up
}

# MINDEX Startup Script
# Starts the MINDEX fungal knowledge service with Docker

param(
    [switch]$Build,
    [switch]$Detached,
    [string]$NasPath = "",
    [switch]$Logs,
    [switch]$Stop
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RootDir = Split-Path -Parent $ScriptDir

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  MINDEX - Mycological Index Service   " -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# Change to root directory
Set-Location $RootDir

# Handle stop command
if ($Stop) {
    Write-Host "`nStopping MINDEX containers..." -ForegroundColor Yellow
    docker-compose -f docker-compose.mindex.yml down
    Write-Host "MINDEX stopped." -ForegroundColor Green
    exit 0
}

# Handle logs command
if ($Logs) {
    Write-Host "`nShowing MINDEX logs..." -ForegroundColor Yellow
    docker-compose -f docker-compose.mindex.yml logs -f mindex
    exit 0
}

# Check if NAS path is set
if ($NasPath) {
    $env:MINDEX_HOST_PATH = $NasPath
    Write-Host "`nUsing NAS path: $NasPath" -ForegroundColor Green
} elseif ($env:MINDEX_HOST_PATH) {
    Write-Host "`nUsing configured NAS path: $env:MINDEX_HOST_PATH" -ForegroundColor Green
} else {
    Write-Host "`nNo NAS path configured, using local data directory" -ForegroundColor Yellow
    $env:MINDEX_HOST_PATH = "$RootDir\data\mindex"
    
    # Create local data directory if it doesn't exist
    if (-not (Test-Path $env:MINDEX_HOST_PATH)) {
        New-Item -ItemType Directory -Path $env:MINDEX_HOST_PATH -Force | Out-Null
        Write-Host "Created: $env:MINDEX_HOST_PATH" -ForegroundColor Gray
    }
}

# Check Docker is running
Write-Host "`nChecking Docker..." -ForegroundColor Yellow
$dockerStatus = docker info 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Docker is not running. Please start Docker Desktop." -ForegroundColor Red
    exit 1
}
Write-Host "Docker is running." -ForegroundColor Green

# Create network if it doesn't exist
Write-Host "`nEnsuring network exists..." -ForegroundColor Yellow
$networks = docker network ls --filter name=mycosoft-network --format "{{.Name}}"
if ($networks -notcontains "mycosoft-network") {
    docker network create mycosoft-network
    Write-Host "Created mycosoft-network" -ForegroundColor Green
} else {
    Write-Host "Network already exists" -ForegroundColor Green
}

# Build if requested
if ($Build) {
    Write-Host "`nBuilding MINDEX container..." -ForegroundColor Yellow
    docker-compose -f docker-compose.mindex.yml build --no-cache
}

# Start MINDEX
Write-Host "`nStarting MINDEX..." -ForegroundColor Yellow

if ($Detached) {
    docker-compose -f docker-compose.mindex.yml up -d
    Write-Host "`nMINDEX started in background." -ForegroundColor Green
    Write-Host "`nService endpoints:" -ForegroundColor Cyan
    Write-Host "  API:    http://localhost:8000" -ForegroundColor White
    Write-Host "  Health: http://localhost:8000/health" -ForegroundColor White
    Write-Host "  Stats:  http://localhost:8000/api/mindex/stats" -ForegroundColor White
    Write-Host "`nView logs: .\scripts\start-mindex.ps1 -Logs" -ForegroundColor Gray
    Write-Host "Stop:      .\scripts\start-mindex.ps1 -Stop" -ForegroundColor Gray
} else {
    docker-compose -f docker-compose.mindex.yml up
}





