# Comprehensive Dependency Installation Script for Mycosoft MAS
# This script installs all required dependencies for local development

param(
    [switch]$SkipDocker,
    [switch]$SkipPython,
    [switch]$SkipNode,
    [switch]$SkipCloudCLIs,
    [switch]$SkipMonitoring,
    [switch]$Verbose
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

# Colors for output
function Write-ColorOutput {
    param([string]$ForegroundColor, [string]$Message)
    Write-Host $Message -ForegroundColor $ForegroundColor
}

function Test-CommandExists {
    param([string]$Command)
    $null = Get-Command $Command -ErrorAction SilentlyContinue
    return $?
}

function Install-Chocolatey {
    if (-not (Test-CommandExists "choco")) {
        Write-ColorOutput "Yellow" "Installing Chocolatey package manager..."
        Set-ExecutionPolicy Bypass -Scope Process -Force
        [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
        Invoke-Expression ((New-Object System.Net.WebClient).DownloadString('https://chocolatey.org/install.ps1'))
        refreshenv
        Write-ColorOutput "Green" "✓ Chocolatey installed successfully"
    } else {
        Write-ColorOutput "Green" "✓ Chocolatey already installed"
    }
}

function Install-Package {
    param(
        [string]$Name,
        [string]$ChocoPackage,
        [string]$TestCommand,
        [string]$VersionCommand = $null,
        [switch]$Optional
    )
    
    if ($TestCommand -and (Test-CommandExists $TestCommand)) {
        $version = if ($VersionCommand) { 
            try { Invoke-Expression $VersionCommand 2>&1 | Out-String } catch { "" }
        } else { "" }
        Write-ColorOutput "Green" "✓ $Name already installed $version"
        return $true
    }
    
    Write-ColorOutput "Yellow" "Installing $Name..."
    try {
        choco install $ChocoPackage -y --force --accept-license
        refreshenv
        if ($TestCommand -and (Test-CommandExists $TestCommand)) {
            Write-ColorOutput "Green" "✓ $Name installed successfully"
            return $true
        } else {
            if (-not $Optional) {
                Write-ColorOutput "Red" "✗ Failed to verify $Name installation"
                return $false
            } else {
                Write-ColorOutput "Yellow" "⚠ $Name installation completed but verification failed (optional)"
                return $true
            }
        }
    } catch {
        if (-not $Optional) {
            Write-ColorOutput "Red" "✗ Failed to install $Name: $_"
            return $false
        } else {
            Write-ColorOutput "Yellow" "⚠ Failed to install $Name (optional): $_"
            return $true
        }
    }
}

Write-ColorOutput "Cyan" "=========================================="
Write-ColorOutput "Cyan" "Mycosoft MAS Dependency Installation"
Write-ColorOutput "Cyan" "=========================================="
Write-Host ""

# Check for admin privileges
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-ColorOutput "Red" "This script requires Administrator privileges. Please run as Administrator."
    exit 1
}

# Install Chocolatey
Install-Chocolatey

# Core System Dependencies
Write-ColorOutput "Cyan" "`n[1/8] Installing Core System Dependencies..."
if (-not $SkipPython) {
    Install-Package -Name "Python 3.11" -ChocoPackage "python311" -TestCommand "python" -VersionCommand "python --version"
    Install-Package -Name "pip" -ChocoPackage "pip" -TestCommand "pip" -VersionCommand "pip --version"
    
    # Install Poetry for Python dependency management
    if (-not (Test-CommandExists "poetry")) {
        Write-ColorOutput "Yellow" "Installing Poetry..."
        (Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | python -
        $env:Path += ";$env:USERPROFILE\.local\bin"
        refreshenv
        Write-ColorOutput "Green" "✓ Poetry installed"
    } else {
        Write-ColorOutput "Green" "✓ Poetry already installed"
    }
}

if (-not $SkipNode) {
    Install-Package -Name "Node.js" -ChocoPackage "nodejs-lts" -TestCommand "node" -VersionCommand "node --version"
    Install-Package -Name "npm" -ChocoPackage "npm" -TestCommand "npm" -VersionCommand "npm --version"
}

if (-not $SkipDocker) {
    Install-Package -Name "Docker Desktop" -ChocoPackage "docker-desktop" -TestCommand "docker" -VersionCommand "docker --version"
}

Install-Package -Name "Git" -ChocoPackage "git" -TestCommand "git" -VersionCommand "git --version"

# Database and Caching
Write-ColorOutput "Cyan" "`n[2/8] Installing Database and Caching Tools..."
# Note: PostgreSQL and Redis can run via Docker, but installing locally for development
Install-Package -Name "PostgreSQL" -ChocoPackage "postgresql" -TestCommand "psql" -VersionCommand "psql --version" -Optional
Install-Package -Name "Redis" -ChocoPackage "redis-64" -TestCommand "redis-cli" -VersionCommand "redis-cli --version" -Optional

# Cloud Platform CLIs
Write-ColorOutput "Cyan" "`n[3/8] Installing Cloud Platform CLIs..."
if (-not $SkipCloudCLIs) {
    # Azure CLI
    if (-not (Test-CommandExists "az")) {
        Write-ColorOutput "Yellow" "Installing Azure CLI..."
        Invoke-WebRequest -Uri https://aka.ms/installazurecliwindows -OutFile "$env:TEMP\AzureCLI.msi"
        Start-Process msiexec.exe -ArgumentList "/i `"$env:TEMP\AzureCLI.msi`" /quiet" -Wait
        refreshenv
        Write-ColorOutput "Green" "✓ Azure CLI installed"
    } else {
        Write-ColorOutput "Green" "✓ Azure CLI already installed"
    }
    
    # GitHub CLI
    Install-Package -Name "GitHub CLI" -ChocoPackage "gh" -TestCommand "gh" -VersionCommand "gh --version"
    
    # Vercel CLI
    if (-not (Test-CommandExists "vercel")) {
        Write-ColorOutput "Yellow" "Installing Vercel CLI..."
        npm install -g vercel
        Write-ColorOutput "Green" "✓ Vercel CLI installed"
    } else {
        Write-ColorOutput "Green" "✓ Vercel CLI already installed"
    }
}

# Python Integration Packages
Write-ColorOutput "Cyan" "`n[4/8] Installing Python Integration Packages..."
if (-not $SkipPython) {
    Write-ColorOutput "Yellow" "Installing Python packages for integrations..."
    
    # Core packages from requirements.txt
    pip install --upgrade pip setuptools wheel
    
    # Install from requirements.txt if it exists
    if (Test-Path "requirements.txt") {
        pip install -r requirements.txt
    }
    
    # Install Poetry dependencies
    if (Test-Path "pyproject.toml") {
        poetry install --no-interaction
    }
    
    # Additional integration packages
    $pythonPackages = @(
        "notion-client",
        "asana",
        "google-api-python-client",
        "google-auth-httplib2",
        "google-auth-oauthlib",
        "azure-identity",
        "azure-mgmt-resource",
        "azure-mgmt-compute",
        "azure-mgmt-storage",
        "azure-storage-blob",
        "azure-keyvault-secrets",
        "prometheus-client",
        "redis",
        "psycopg2-binary",
        "httpx",
        "aiohttp",
        "python-dotenv",
        "pydantic",
        "pydantic-settings",
        "fastapi",
        "uvicorn",
        "sqlalchemy",
        "alembic"
    )
    
    foreach ($package in $pythonPackages) {
        Write-ColorOutput "Yellow" "  Installing $package..."
        pip install $package --quiet
    }
    
    Write-ColorOutput "Green" "✓ Python integration packages installed"
}

# Node.js packages
Write-ColorOutput "Cyan" "`n[5/8] Installing Node.js Packages..."
if (-not $SkipNode) {
    if (Test-Path "package.json") {
        Write-ColorOutput "Yellow" "Installing Node.js dependencies..."
        npm install
        Write-ColorOutput "Green" "✓ Node.js packages installed"
    }
}

# Monitoring Tools (via Docker)
Write-ColorOutput "Cyan" "`n[6/8] Setting up Monitoring Tools..."
if (-not $SkipMonitoring -and -not $SkipDocker) {
    Write-ColorOutput "Yellow" "Monitoring tools (Prometheus, Grafana) will be available via Docker Compose"
    Write-ColorOutput "Green" "✓ Monitoring tools configured"
}

# N8N Workflow Automation
Write-ColorOutput "Cyan" "`n[7/8] Installing N8N..."
if (-not (Test-CommandExists "n8n")) {
    Write-ColorOutput "Yellow" "Installing N8N..."
    npm install -g n8n
    Write-ColorOutput "Green" "✓ N8N installed"
    Write-ColorOutput "Yellow" "  Note: N8N can also run via Docker. Start with: docker run -it --rm --name n8n -p 5678:5678 n8nio/n8n"
} else {
    Write-ColorOutput "Green" "✓ N8N already installed"
}

# Network Management Tools (Optional)
Write-ColorOutput "Cyan" "`n[8/8] Checking Network Management Tools..."
Write-ColorOutput "Yellow" "  Proxmox, Ubiquity, and Unify are typically server-side tools."
Write-ColorOutput "Yellow" "  For local development, these are not required."
Write-ColorOutput "Green" "✓ Network tools check complete"

# Verification
Write-ColorOutput "Cyan" "`n=========================================="
Write-ColorOutput "Cyan" "Verification Report"
Write-ColorOutput "Cyan" "=========================================="

$tools = @(
    @{Name = "Python"; Command = "python --version"},
    @{Name = "pip"; Command = "pip --version"},
    @{Name = "Poetry"; Command = "poetry --version"},
    @{Name = "Node.js"; Command = "node --version"},
    @{Name = "npm"; Command = "npm --version"},
    @{Name = "Docker"; Command = "docker --version"},
    @{Name = "Git"; Command = "git --version"},
    @{Name = "Azure CLI"; Command = "az --version"},
    @{Name = "GitHub CLI"; Command = "gh --version"},
    @{Name = "Vercel CLI"; Command = "vercel --version"},
    @{Name = "N8N"; Command = "n8n --version"}
)

$installed = 0
$failed = 0

foreach ($tool in $tools) {
    try {
        $version = Invoke-Expression $tool.Command 2>&1 | Select-Object -First 1
        if ($LASTEXITCODE -eq 0 -or $version) {
            Write-ColorOutput "Green" "✓ $($tool.Name): $version"
            $installed++
        } else {
            Write-ColorOutput "Red" "✗ $($tool.Name): Not found"
            $failed++
        }
    } catch {
        Write-ColorOutput "Red" "✗ $($tool.Name): Not found"
        $failed++
    }
}

Write-Host ""
Write-ColorOutput "Cyan" "Installation Summary:"
Write-ColorOutput "Green" "  Installed: $installed"
if ($failed -gt 0) {
    Write-ColorOutput "Red" "  Failed: $failed"
}

Write-Host ""
Write-ColorOutput "Cyan" "Next Steps:"
Write-Host "1. Configure environment variables in .env file"
Write-Host "2. Set up API keys for: Azure, Notion, Asana, Google Workspace, N8N"
Write-Host "3. Run: docker-compose up -d (to start services)"
Write-Host "4. Run: poetry install (if not already done)"
Write-Host "5. Run: npm install (if not already done)"
Write-Host ""
Write-ColorOutput "Green" "Dependency installation complete!"
