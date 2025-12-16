# Mycosoft MAS - Automated PR Creation and Merge Script
# Usage: .\scripts\create-and-merge-pr.ps1 -BranchName "feature/my-feature" -Title "Add feature" -Body "Description"

param(
    [Parameter(Mandatory=$true)]
    [string]$BranchName,
    
    [Parameter(Mandatory=$true)]
    [string]$Title,
    
    [Parameter(Mandatory=$false)]
    [string]$Body = "Automated PR from script",
    
    [Parameter(Mandatory=$false)]
    [string]$BaseBranch = "main",
    
    [Parameter(Mandatory=$false)]
    [switch]$AutoMerge = $false,
    
    [Parameter(Mandatory=$false)]
    [switch]$DeleteBranch = $false
)

# Refresh PATH to include GitHub CLI
$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")

# Check if gh is available
try {
    $ghVersion = gh --version 2>&1
    Write-Host "GitHub CLI found: $ghVersion" -ForegroundColor Green
} catch {
    Write-Host "Error: GitHub CLI (gh) not found. Please install it first." -ForegroundColor Red
    Write-Host "Install via: winget install --id GitHub.cli -e --source winget" -ForegroundColor Yellow
    exit 1
}

# Check if authenticated
try {
    gh auth status 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "GitHub CLI not authenticated. Please run: gh auth login" -ForegroundColor Yellow
        Write-Host "This will open a browser for authentication." -ForegroundColor Yellow
        exit 1
    }
} catch {
    Write-Host "Error checking GitHub CLI authentication." -ForegroundColor Red
    exit 1
}

# Get current branch
$currentBranch = git rev-parse --abbrev-ref HEAD
Write-Host "Current branch: $currentBranch" -ForegroundColor Cyan

# Check if branch exists
$branchExists = git show-ref --verify --quiet "refs/heads/$BranchName"
if (-not $branchExists) {
    Write-Host "Branch '$BranchName' does not exist locally. Creating it..." -ForegroundColor Yellow
    git checkout -b $BranchName
} else {
    Write-Host "Switching to branch '$BranchName'..." -ForegroundColor Cyan
    git checkout $BranchName
}

# Check if there are uncommitted changes
$status = git status --porcelain
if ($status) {
    Write-Host "Warning: You have uncommitted changes. Stashing them..." -ForegroundColor Yellow
    git stash push -u -m "wip: auto-stash before PR creation"
    $stashed = $true
} else {
    $stashed = $false
}

# Push branch to origin
Write-Host "Pushing branch '$BranchName' to origin..." -ForegroundColor Cyan
git push -u origin $BranchName
if ($LASTEXITCODE -ne 0) {
    Write-Host "Error pushing branch. Aborting." -ForegroundColor Red
    if ($stashed) {
        git stash pop
    }
    exit 1
}

# Create PR
Write-Host "Creating pull request..." -ForegroundColor Cyan
$prOutput = gh pr create --base $BaseBranch --head $BranchName --title $Title --body $Body 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "Error creating PR: $prOutput" -ForegroundColor Red
    if ($stashed) {
        git stash pop
    }
    exit 1
}

Write-Host "PR created successfully!" -ForegroundColor Green
Write-Host $prOutput -ForegroundColor Cyan

# Extract PR number from output
$prNumber = ($prOutput | Select-String -Pattern 'pull/(\d+)').Matches.Groups[1].Value

if ($AutoMerge) {
    Write-Host "Auto-merging PR #$prNumber..." -ForegroundColor Cyan
    gh pr merge $prNumber --merge --delete-branch
    if ($LASTEXITCODE -eq 0) {
        Write-Host "PR merged successfully!" -ForegroundColor Green
        
        # Switch back to base branch and pull
        git checkout $BaseBranch
        git pull
        
        # Delete local branch if requested
        if ($DeleteBranch) {
            git branch -D $BranchName
            Write-Host "Deleted local branch '$BranchName'" -ForegroundColor Green
        }
    } else {
        Write-Host "Error merging PR. You may need to merge manually." -ForegroundColor Yellow
    }
} else {
    Write-Host "PR created but not merged. Merge manually or use -AutoMerge flag." -ForegroundColor Yellow
    Write-Host "PR URL: $prOutput" -ForegroundColor Cyan
}

# Restore stashed changes if any
if ($stashed) {
    Write-Host "Restoring stashed changes..." -ForegroundColor Cyan
    git stash pop
}

Write-Host "Done!" -ForegroundColor Green
