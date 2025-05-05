# Main setup script for Mycosoft MAS
Write-Host "Starting complete setup for Mycosoft MAS..."

# Check if running as administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "Please run this script as Administrator" -ForegroundColor Red
    exit 1
}

# Set execution policy
Set-ExecutionPolicy Bypass -Scope Process -Force
Set-ExecutionPolicy Bypass -Scope CurrentUser -Force

# Function to check if a command exists
function Test-CommandExists {
    param ($command)
    $oldPreference = $ErrorActionPreference
    $ErrorActionPreference = 'stop'
    try {
        if (Get-Command $command) { return $true }
    } catch {
        return $false
    } finally {
        $ErrorActionPreference = $oldPreference
    }
}

# Function to install package with retries
function Install-PackageWithRetry {
    param (
        [string]$PackageName,
        [string]$InstallCommand
    )
    $maxRetries = 3
    $retryCount = 0
    $success = $false

    while (-not $success -and $retryCount -lt $maxRetries) {
        try {
            Write-Host "Installing $PackageName (Attempt $($retryCount + 1))..."
            Invoke-Expression $InstallCommand
            $success = $true
        } catch {
            $retryCount++
            Write-Host "Failed to install $PackageName. Retrying in 5 seconds..."
            Start-Sleep -Seconds 5
        }
    }

    if (-not $success) {
        Write-Host "Failed to install $PackageName after $maxRetries attempts" -ForegroundColor Red
        exit 1
    }
}

# Install Chocolatey if not present
if (-not (Test-CommandExists choco)) {
    Write-Host "Installing Chocolatey package manager..."
    [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
    Invoke-Expression ((New-Object System.Net.WebClient).DownloadString('https://chocolatey.org/install.ps1'))
    refreshenv
}

# Install all required packages
$packages = @(
    @{Name = "Python 3.11"; Command = "choco install python311 -y --force"},
    @{Name = "Node.js"; Command = "choco install nodejs -y --force"},
    @{Name = "Rust"; Command = "choco install rust -y --force"},
    @{Name = "Docker Desktop"; Command = "choco install docker-desktop -y --force"},
    @{Name = "Git"; Command = "choco install git -y --force"},
    @{Name = "Visual Studio Build Tools"; Command = "choco install visualstudio2019buildtools visualstudio2019-workload-vctools -y --force"},
    @{Name = "PostgreSQL"; Command = "choco install postgresql -y --force"},
    @{Name = "Redis"; Command = "choco install redis-64 -y --force"}
)

foreach ($package in $packages) {
    Install-PackageWithRetry -PackageName $package.Name -InstallCommand $package.Command
    refreshenv
}

# Install Poetry
Write-Host "Installing Poetry..."
(Invoke-WebRequest -Uri https://raw.githubusercontent.com/python-poetry/poetry/master/get-poetry.py -UseBasicParsing).Content | python -
refreshenv

# Install WSL2
Write-Host "Installing WSL2..."
dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart
dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart
wsl --install --no-distribution
wsl --set-default-version 2

# Verify installations
Write-Host "Verifying installations..."
$tools = @(
    @{Name = "Python"; Command = "python --version"},
    @{Name = "Node.js"; Command = "node --version"},
    @{Name = "npm"; Command = "npm --version"},
    @{Name = "Rust"; Command = "rustc --version"},
    @{Name = "Docker"; Command = "docker --version"},
    @{Name = "Poetry"; Command = "poetry --version"},
    @{Name = "Git"; Command = "git --version"},
    @{Name = "PostgreSQL"; Command = "psql --version"},
    @{Name = "Redis"; Command = "redis-cli --version"}
)

foreach ($tool in $tools) {
    try {
        $version = Invoke-Expression $tool.Command
        Write-Host "$($tool.Name) installed successfully: $version" -ForegroundColor Green
    } catch {
        Write-Host "$($tool.Name) installation failed" -ForegroundColor Red
    }
}

# Run test environment setup
Write-Host "Setting up test environment..."
.\setup_test.ps1

# Run Docker environment setup
Write-Host "Setting up Docker environment..."
.\setup.ps1

Write-Host "All setup processes completed!"
Write-Host "You can now access your development environment at:"
Write-Host "- MAS Orchestrator: http://localhost:8000"
Write-Host "- Grafana: http://localhost:3000"
Write-Host "- Prometheus: http://localhost:9090"
Write-Host "- AlertManager: http://localhost:9093"

Write-Host "`nPlease restart your computer to ensure all installations are properly configured." 