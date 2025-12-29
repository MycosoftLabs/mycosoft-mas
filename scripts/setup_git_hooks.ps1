# Setup Git Hooks for Auto-Indexing Documents
# PowerShell script to set up git hooks on Windows

$ErrorActionPreference = "Stop"

Write-Host "Setting up Git hooks for auto-indexing documents..." -ForegroundColor Cyan

$repoRoot = git rev-parse --show-toplevel
$hooksDir = Join-Path $repoRoot ".git\hooks"
$hookFile = Join-Path $hooksDir "post-commit"

# Create hooks directory if it doesn't exist
if (-not (Test-Path $hooksDir)) {
    New-Item -ItemType Directory -Path $hooksDir -Force | Out-Null
}

# Copy post-commit hook
$sourceHook = Join-Path $repoRoot "scripts\git_hooks\post-commit"
if (Test-Path $sourceHook) {
    Copy-Item $sourceHook $hookFile -Force
    Write-Host "✓ Copied post-commit hook" -ForegroundColor Green
} else {
    # Create hook from template
    $hookContent = @"
#!/bin/bash
# Git post-commit hook to auto-index new documents

REPO_ROOT=`$(git rev-parse --show-toplevel)
CHANGED_FILES=`$(git diff-tree --no-commit-id --name-only -r HEAD | grep -E '\.(md|MD)$|^README')

if [ -n "`$CHANGED_FILES" ]; then
    echo "Detected markdown/README file changes, auto-indexing..."
    cd "`$REPO_ROOT"
    python scripts/auto_index_new_documents.py > /dev/null 2>&1 &
    echo "Document indexing started in background"
fi
"@
    
    # For Windows, we'll create a PowerShell version
    $psHookContent = @"
# Git post-commit hook to auto-index new documents (PowerShell)

`$REPO_ROOT = git rev-parse --show-toplevel
`$CHANGED_FILES = git diff-tree --no-commit-id --name-only -r HEAD | Select-String -Pattern '\.(md|MD)$|^README'

if (`$CHANGED_FILES) {
    Write-Host "Detected markdown/README file changes, auto-indexing..."
    Set-Location `$REPO_ROOT
    Start-Process -NoNewWindow python -ArgumentList "scripts\auto_index_new_documents.py" -WindowStyle Hidden
    Write-Host "Document indexing started in background"
}
"@
    
    $psHookFile = Join-Path $hooksDir "post-commit.ps1"
    Set-Content -Path $psHookFile -Value $psHookContent
    Write-Host "✓ Created PowerShell post-commit hook" -ForegroundColor Green
}

Write-Host ""
Write-Host "Git hooks setup complete!" -ForegroundColor Green
Write-Host "New markdown/README files will be automatically indexed on commit." -ForegroundColor Cyan

