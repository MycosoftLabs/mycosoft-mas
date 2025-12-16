# Install Node.js packages and global tools
Write-Host "Installing Node.js packages..." -ForegroundColor Cyan

# Check if npm is available
if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
    Write-Host "npm not found. Please install Node.js first." -ForegroundColor Red
    exit 1
}

# Install local project dependencies
if (Test-Path "package.json") {
    Write-Host "Installing project dependencies from package.json..." -ForegroundColor Yellow
    npm install
    Write-Host "✓ Project dependencies installed" -ForegroundColor Green
}

# Install global tools
Write-Host "`nInstalling global tools..." -ForegroundColor Yellow

$globalTools = @(
    @{Name = "Vercel CLI"; Package = "vercel"},
    @{Name = "N8N"; Package = "n8n"}
)

foreach ($tool in $globalTools) {
    Write-Host "Checking $($tool.Name)..." -ForegroundColor Yellow
    $installed = npm list -g $tool.Package --depth=0 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ $($tool.Name) already installed" -ForegroundColor Green
    } else {
        Write-Host "Installing $($tool.Name)..." -ForegroundColor Yellow
        npm install -g $tool.Package
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✓ $($tool.Name) installed successfully" -ForegroundColor Green
        } else {
            Write-Host "✗ Failed to install $($tool.Name)" -ForegroundColor Red
        }
    }
}

Write-Host "`nNode.js package installation complete!" -ForegroundColor Green
