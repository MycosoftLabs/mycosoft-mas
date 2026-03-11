# CTO Guest Bootstrap — Fresh-Clone Cursor Workstation
# Date: March 8, 2026
# Run AFTER bootstrap_openclaw_windows.ps1 and apply_role_manifest.ps1 when role is cto.
# Stages: Python, workspace clone, Cursor sync, env scaffold, validation.
# Usage: .\bootstrap_cto_guest.ps1 [-ConfigPath path] [-SkipClone]

param(
    [string]$ConfigPath = "",
    [switch]$SkipClone
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

# --- Config from role_config or proxmox202_csuite ---
$CodeRoot = $env:CTO_CODE_ROOT
$GitOrg = $env:CTO_GIT_ORG
$MasUrl = $env:MAS_API_URL
$MindexUrl = $env:MINDEX_API_URL

if (-not $MasUrl) { $MasUrl = "http://192.168.0.188:8001" }
if (-not $MindexUrl) { $MindexUrl = "http://192.168.0.189:8000" }
if (-not $CodeRoot) { $CodeRoot = "C:\Users\$env:USERNAME\Mycosoft\CODE" }
if (-not $GitOrg) { $GitOrg = "MycosoftLabs" }

$Repos = @(
    @{ Path = "MAS\mycosoft-mas"; Repo = "mycosoft-mas" },
    @{ Path = "WEBSITE\website"; Repo = "website" }
)
$Branch = "main"

if ($ConfigPath -and (Test-Path $ConfigPath)) {
    try {
        $yaml = Get-Content $ConfigPath -Raw
        if ($yaml -match "cto_workspace:") {
            # Simple inline parse for code_root, git_org, repos
            if ($yaml -match "code_root:\s*`"([^`"]+)`"") { $CodeRoot = $matches[1].Trim() }
            if ($yaml -match "git_org:\s*`"([^`"]+)`"") { $GitOrg = $matches[1].Trim() }
        }
    } catch {
        Write-Host "[CTO Bootstrap] Config parse skipped: $_" -ForegroundColor Yellow
    }
}

Write-Host "[CTO Bootstrap] Code root: $CodeRoot, Git org: $GitOrg" -ForegroundColor Cyan

# --- 1. Python ---
$pyOk = $false
try {
    $py = Get-Command python -ErrorAction SilentlyContinue
    if ($py) {
        $v = & python --version 2>&1
        if ($v -match "3\.(1[1-9]|[2-9][0-9])") { $pyOk = $true }
    }
} catch {}
if (-not $pyOk) {
    Write-Host "[CTO Bootstrap] Installing Python 3.11 via winget..." -ForegroundColor Cyan
    winget install Python.Python.3.11 --accept-package-agreements --accept-source-agreements 2>$null
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")
    $py = Get-Command python -ErrorAction SilentlyContinue
    if (-not $py) {
        Write-Host "[CTO Bootstrap] Python installed. Restart PowerShell and re-run." -ForegroundColor Yellow
        exit 1
    }
}
Write-Host "[CTO Bootstrap] Python: $(python --version 2>&1)" -ForegroundColor Green

# --- 2. Node ---
$nodeOk = $false
try {
    $v = (node --version 2>$null) -replace 'v', ''
    $major = [int]($v.Split('.')[0])
    if ($major -ge 18) { $nodeOk = $true }
} catch {}
if (-not $nodeOk) {
    Write-Host "[CTO Bootstrap] Node.js not found or too old. Run bootstrap_openclaw_windows.ps1 first." -ForegroundColor Yellow
}
if ($nodeOk) { Write-Host "[CTO Bootstrap] Node: $(node --version)" -ForegroundColor Green }

# --- 3. Workspace clone ---
if (-not $SkipClone) {
    New-Item -ItemType Directory -Path $CodeRoot -Force | Out-Null
    foreach ($r in $Repos) {
        $fullPath = Join-Path $CodeRoot $r.Path
        $parentDir = Split-Path $fullPath -Parent
        $repoName = Split-Path $fullPath -Leaf
        $url = "https://github.com/$GitOrg/$($r.Repo).git"
        if (-not (Test-Path $fullPath)) {
            Write-Host "[CTO Bootstrap] Cloning $($r.Repo) to $fullPath..." -ForegroundColor Cyan
            New-Item -ItemType Directory -Path $parentDir -Force | Out-Null
            git clone -b $Branch --single-branch $url $fullPath 2>&1 | Out-Null
            if (-not (Test-Path (Join-Path $fullPath ".git"))) {
                Write-Host "[CTO Bootstrap] Clone failed for $($r.Repo). Check network and gh/auth." -ForegroundColor Yellow
            } else {
                Write-Host "[CTO Bootstrap] Cloned $($r.Repo)" -ForegroundColor Green
            }
        } else {
            Write-Host "[CTO Bootstrap] Repo exists: $fullPath — pulling..." -ForegroundColor Gray
            Push-Location $fullPath
            git pull origin $Branch 2>&1 | Out-Null
            Pop-Location
        }
    }
} else {
    Write-Host "[CTO Bootstrap] SkipClone — using existing workspace" -ForegroundColor Gray
}

# --- 4. Cursor sync ---
$MasRepo = Join-Path $CodeRoot "MAS\mycosoft-mas"
$SyncScript = Join-Path $MasRepo "scripts\sync_cursor_system.py"
if ((Test-Path $SyncScript) -and (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "[CTO Bootstrap] Running Cursor system sync..." -ForegroundColor Cyan
    $env:CODE_ROOT = $CodeRoot
    Push-Location $MasRepo
    try {
        python $SyncScript 2>&1
        Write-Host "[CTO Bootstrap] Cursor sync complete" -ForegroundColor Green
    } catch {
        Write-Host "[CTO Bootstrap] Sync error: $_" -ForegroundColor Yellow
    }
    Pop-Location
} else {
    Write-Host "[CTO Bootstrap] sync_cursor_system.py not found at $SyncScript" -ForegroundColor Yellow
}

# --- 5. Env scaffold (placeholders only — no real secrets) ---
$CredsPath = Join-Path $MasRepo ".credentials.local"
$EnvLocalPath = Join-Path $MasRepo ".env.local"
if (Test-Path $MasRepo) {
    if (-not (Test-Path $CredsPath)) {
        @"
# CTO VM credentials — add real values locally. Never commit.
VM_PASSWORD=
VM_SSH_PASSWORD=
CSUITE_GUEST_PASSWORD=
MAS_API_URL=$MasUrl
MINDEX_API_URL=$MindexUrl
"@ | Out-File -FilePath $CredsPath -Encoding utf8
        Write-Host "[CTO Bootstrap] Created .credentials.local scaffold (add values manually)" -ForegroundColor Green
    }
    $websiteRepo = Join-Path $CodeRoot "WEBSITE\website"
    if (Test-Path $websiteRepo) {
        $websiteEnv = Join-Path $websiteRepo ".env.local"
        if (-not (Test-Path $websiteEnv)) {
            @"
MAS_API_URL=$MasUrl
NEXT_PUBLIC_MAS_API_URL=$MasUrl
MINDEX_API_URL=$MindexUrl
MINDEX_API_BASE_URL=$MindexUrl
"@ | Out-File -FilePath $websiteEnv -Encoding utf8
            Write-Host "[CTO Bootstrap] Created website .env.local scaffold" -ForegroundColor Green
        }
    }
}

# --- 6. gh auth check ---
$ghOk = $false
try {
    $status = gh auth status 2>&1
    if ($LASTEXITCODE -eq 0) { $ghOk = $true }
} catch {}
if (-not $ghOk) {
    Write-Host "[CTO Bootstrap] GitHub CLI not authenticated. Run: gh auth login" -ForegroundColor Yellow
} else {
    Write-Host "[CTO Bootstrap] gh auth OK" -ForegroundColor Green
}

# --- 7. Validation ---
$cursorUser = Join-Path $env:USERPROFILE ".cursor"
$rulesDir = Join-Path $cursorUser "rules"
$agentsDir = Join-Path $cursorUser "agents"
$rulesCount = 0
$agentsCount = 0
if (Test-Path $rulesDir) { $rulesCount = (Get-ChildItem $rulesDir -Filter "*.mdc" -ErrorAction SilentlyContinue).Count }
if (Test-Path $agentsDir) { $agentsCount = (Get-ChildItem $agentsDir -Filter "*.md" -ErrorAction SilentlyContinue).Count }

Write-Host "[CTO Bootstrap] Validation: rules=$rulesCount, agents=$agentsCount in $cursorUser" -ForegroundColor Cyan
if ($rulesCount -gt 0 -and $agentsCount -gt 0) {
    Write-Host "[CTO Bootstrap] Cursor assets present — clone can load subagents/rules/skills" -ForegroundColor Green
} else {
    Write-Host "[CTO Bootstrap] Few or no rules/agents. Ensure MAS repo cloned and sync ran." -ForegroundColor Yellow
}

Write-Host "[CTO Bootstrap] Complete. Next: Open Cursor with workspace, run Forge bridge/watchdog." -ForegroundColor Green
