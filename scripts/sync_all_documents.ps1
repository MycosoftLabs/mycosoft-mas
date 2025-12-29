# Mycosoft MAS - Complete Document Sync (PowerShell)
# Orchestrates document inventory, Notion sync, and NAS sync

param(
    [switch]$SkipNotion,
    [switch]$SkipNAS,
    [string]$NASPath = $env:NAS_DOCS_PATH
)

$ErrorActionPreference = "Stop"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "MYCOSOFT MAS - COMPLETE DOCUMENT SYNC" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Started: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -ForegroundColor Gray
Write-Host ""

$scriptsDir = Join-Path $PSScriptRoot "."
$rootDir = Split-Path $PSScriptRoot -Parent

# Step 1: Scan and inventory documents
Write-Host "============================================================" -ForegroundColor Yellow
Write-Host "Step 1: Scanning and inventorying all documents" -ForegroundColor Yellow
Write-Host "============================================================" -ForegroundColor Yellow
Write-Host ""

try {
    python "$scriptsDir\document_inventory.py"
    if ($LASTEXITCODE -ne 0) {
        throw "Inventory scan failed"
    }
    Write-Host "[OK] Inventory scan completed" -ForegroundColor Green
} catch {
    Write-Host "[ERROR] Inventory scan failed: $_" -ForegroundColor Red
    exit 1
}

# Step 2: Sync to Notion (optional)
if (-not $SkipNotion) {
    $notionApiKey = $env:NOTION_API_KEY
    $notionDbId = $env:NOTION_DATABASE_ID
    
    if ($notionApiKey -and $notionDbId) {
        Write-Host ""
        Write-Host "============================================================" -ForegroundColor Yellow
        Write-Host "Step 2: Syncing documents to Notion knowledge base" -ForegroundColor Yellow
        Write-Host "============================================================" -ForegroundColor Yellow
        Write-Host ""
        
        try {
            python "$scriptsDir\sync_to_notion.py"
            if ($LASTEXITCODE -ne 0) {
                throw "Notion sync failed"
            }
            Write-Host "[OK] Notion sync completed" -ForegroundColor Green
        } catch {
            Write-Host "[WARNING] Notion sync failed: $_" -ForegroundColor Yellow
        }
    } else {
        Write-Host ""
        Write-Host "[SKIP] Notion sync skipped (NOTION_API_KEY or NOTION_DATABASE_ID not set)" -ForegroundColor Gray
    }
} else {
    Write-Host ""
    Write-Host "[SKIP] Notion sync skipped (--SkipNotion flag)" -ForegroundColor Gray
}

# Step 3: Sync to NAS (optional)
if (-not $SkipNAS) {
    if (-not $NASPath) {
        # Try to detect common NAS paths
        $commonPaths = @(
            "\\M-Y-C-A-L\docs",
            "\\M-Y-C-A-L\shared\docs",
            "Z:\docs",
            "Y:\docs"
        )
        
        foreach ($path in $commonPaths) {
            if (Test-Path $path) {
                $NASPath = $path
                Write-Host "[INFO] Detected NAS path: $NASPath" -ForegroundColor Cyan
                break
            }
        }
    }
    
    if ($NASPath) {
        Write-Host ""
        Write-Host "============================================================" -ForegroundColor Yellow
        Write-Host "Step 3: Syncing documents to NAS shared drive" -ForegroundColor Yellow
        Write-Host "============================================================" -ForegroundColor Yellow
        Write-Host ""
        
        $env:NAS_DOCS_PATH = $NASPath
        
        try {
            python "$scriptsDir\sync_to_nas.py"
            if ($LASTEXITCODE -ne 0) {
                throw "NAS sync failed"
            }
            Write-Host "[OK] NAS sync completed" -ForegroundColor Green
        } catch {
            Write-Host "[WARNING] NAS sync failed: $_" -ForegroundColor Yellow
        }
    } else {
        Write-Host ""
        Write-Host "[SKIP] NAS sync skipped (NAS path not found or NAS_DOCS_PATH not set)" -ForegroundColor Gray
        Write-Host "       Set NAS_DOCS_PATH environment variable or use -NASPath parameter" -ForegroundColor Gray
    }
} else {
    Write-Host ""
    Write-Host "[SKIP] NAS sync skipped (--SkipNAS flag)" -ForegroundColor Gray
}

# Summary
Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "SYNC SUMMARY" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Inventory: [OK]" -ForegroundColor Green
Write-Host "Notion: $($(if ($SkipNotion -or (-not $env:NOTION_API_KEY)) { '[SKIP]' } else { '[OK]' }))" -ForegroundColor $(if ($SkipNotion -or (-not $env:NOTION_API_KEY)) { 'Gray' } else { 'Green' })
Write-Host "NAS: $($(if ($SkipNAS -or (-not $NASPath)) { '[SKIP]' } else { '[OK]' }))" -ForegroundColor $(if ($SkipNAS -or (-not $NASPath)) { 'Gray' } else { 'Green' })
Write-Host "============================================================" -ForegroundColor Cyan

# Check output files
$inventoryFile = Join-Path $rootDir "docs\document_inventory.json"
$indexFile = Join-Path $rootDir "DOCUMENT_INDEX.md"

if (Test-Path $inventoryFile) {
    Write-Host ""
    Write-Host "Full inventory available at: $inventoryFile" -ForegroundColor Cyan
}

if (Test-Path $indexFile) {
    Write-Host "Document index available at: $indexFile" -ForegroundColor Cyan
}

Write-Host ""
Write-Host "Completed: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -ForegroundColor Gray

