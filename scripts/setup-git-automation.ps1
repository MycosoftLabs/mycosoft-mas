# Mycosoft MAS - Git Automation Setup Script
# This script sets up git identity and GitHub CLI authentication for automated workflows

Write-Host "=== Mycosoft MAS Git Automation Setup ===" -ForegroundColor Cyan
Write-Host ""

# Check if git is available
try {
    $gitVersion = git --version
    Write-Host "Git found: $gitVersion" -ForegroundColor Green
} catch {
    Write-Host "Error: Git not found. Please install Git first." -ForegroundColor Red
    exit 1
}

# Check current git config
Write-Host "`nCurrent Git Configuration:" -ForegroundColor Cyan
$currentName = git config --global user.name 2>$null
$currentEmail = git config --global user.email 2>$null

if ($currentName) {
    Write-Host "  Name: $currentName" -ForegroundColor Yellow
} else {
    Write-Host "  Name: (not set)" -ForegroundColor Yellow
}

if ($currentEmail) {
    Write-Host "  Email: $currentEmail" -ForegroundColor Yellow
} else {
    Write-Host "  Email: (not set)" -ForegroundColor Yellow
}

Write-Host ""
$updateConfig = Read-Host "Do you want to update git user.name and user.email? (y/n)"
if ($updateConfig -eq "y" -or $updateConfig -eq "Y") {
    $newName = Read-Host "Enter your name (or press Enter to keep current)"
    if ($newName -and $newName -ne $currentName) {
        git config --global user.name $newName
        Write-Host "Set user.name to: $newName" -ForegroundColor Green
    }
    
    $newEmail = Read-Host "Enter your email (or press Enter to keep current)"
    if ($newEmail -and $newEmail -ne $currentEmail) {
        git config --global user.email $newEmail
        Write-Host "Set user.email to: $newEmail" -ForegroundColor Green
    }
}

# Refresh PATH to include GitHub CLI
$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")

# Check if GitHub CLI is installed
Write-Host "`nChecking GitHub CLI..." -ForegroundColor Cyan
try {
    $ghVersion = gh --version 2>&1
    Write-Host "GitHub CLI found: $ghVersion" -ForegroundColor Green
} catch {
    Write-Host "GitHub CLI not found. Installing..." -ForegroundColor Yellow
    Write-Host "This may require administrator privileges." -ForegroundColor Yellow
    
    $install = Read-Host "Install GitHub CLI now? (y/n)"
    if ($install -eq "y" -or $install -eq "Y") {
        winget install --id GitHub.cli -e --source winget
        if ($LASTEXITCODE -eq 0) {
            Write-Host "GitHub CLI installed successfully!" -ForegroundColor Green
            Write-Host "Please restart your terminal for PATH changes to take effect." -ForegroundColor Yellow
        } else {
            Write-Host "Installation failed. Please install manually." -ForegroundColor Red
            exit 1
        }
    } else {
        Write-Host "Skipping GitHub CLI installation." -ForegroundColor Yellow
        exit 0
    }
}

# Check GitHub CLI authentication
Write-Host "`nChecking GitHub CLI authentication..." -ForegroundColor Cyan
try {
    gh auth status 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "GitHub CLI is authenticated!" -ForegroundColor Green
        gh auth status
    } else {
        Write-Host "GitHub CLI is not authenticated." -ForegroundColor Yellow
        $auth = Read-Host "Authenticate now? (y/n)"
        if ($auth -eq "y" -or $auth -eq "Y") {
            Write-Host "This will open a browser for authentication..." -ForegroundColor Cyan
            gh auth login
        }
    }
} catch {
    Write-Host "Error checking authentication status." -ForegroundColor Red
}

Write-Host "`n=== Setup Complete ===" -ForegroundColor Green
Write-Host ""
Write-Host "You can now use the PR automation script:" -ForegroundColor Cyan
Write-Host "  .\scripts\create-and-merge-pr.ps1 -BranchName 'feature/my-feature' -Title 'Add feature' -Body 'Description' -AutoMerge" -ForegroundColor Yellow
Write-Host ""
