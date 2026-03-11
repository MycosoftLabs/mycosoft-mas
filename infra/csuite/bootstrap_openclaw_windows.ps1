# C-Suite OpenClaw Golden Image Bootstrap — Windows
# Date: March 7, 2026
# Run after Windows install, before role-specific customization.
# Usage: .\bootstrap_openclaw_windows.ps1 [-Role ceo|cfo|cto|coo] [-SkipOpenClawInstall]

param(
    [ValidateSet("ceo", "cfo", "cto", "coo")]
    [string]$Role = "ceo",
    [switch]$SkipOpenClawInstall,
    [switch]$NoRestart
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

# --- Paths ---
$CsuiteRoot = "$env:LOCALAPPDATA\Mycosoft\C-Suite"
$OpenClawHome = "$env:LOCALAPPDATA\OpenClaw"
$Dirs = @(
    "$CsuiteRoot\memory",
    "$CsuiteRoot\skills",
    "$CsuiteRoot\logs",
    "$CsuiteRoot\role_prompts",
    "$CsuiteRoot\persona_seeds",
    "$CsuiteRoot\config"
)

Write-Host "[Bootstrap] Creating C-Suite directories..." -ForegroundColor Cyan
foreach ($d in $Dirs) {
    if (-not (Test-Path $d)) {
        New-Item -ItemType Directory -Path $d -Force | Out-Null
        Write-Host "  Created: $d"
    }
}

# --- Role config from shared YAML (authoritative manifests) ---
$MasUrlDefault = "http://192.168.0.188:8001"
$configPath = Join-Path $CsuiteRoot "config\role_config.json"
if (Test-Path $configPath) {
    try {
        $cfg = Get-Content $configPath -Raw | ConvertFrom-Json
        $MasUrl = $cfg.mas_api_url
        if ($MasUrl) { $MasUrlDefault = $MasUrl }
        Write-Host "[Bootstrap] Role config from host: $configPath" -ForegroundColor Green
    } catch {
        Write-Host "[Bootstrap] Failed to parse role_config.json, using defaults: $_" -ForegroundColor Yellow
    }
} else {
    $emitScript = $null
    if ($PSScriptRoot) { $emitScript = Join-Path $PSScriptRoot "emit_role_config.py" }
    if ($emitScript -and (Test-Path $emitScript)) {
        $py = Get-Command python -ErrorAction SilentlyContinue
        if ($py) {
            try {
                $outPath = $configPath
                & python $emitScript -r $Role -o $outPath 2>$null
                if (Test-Path $outPath) {
                    $cfg = Get-Content $outPath -Raw | ConvertFrom-Json
                    $MasUrl = $cfg.mas_api_url
                    if ($MasUrl) { $MasUrlDefault = $MasUrl }
                    Write-Host "[Bootstrap] Role config from manifests: $outPath" -ForegroundColor Green
                }
            } catch {
                Write-Host "[Bootstrap] emit_role_config failed, using defaults: $_" -ForegroundColor Yellow
            }
        }
    }
}
[System.Environment]::SetEnvironmentVariable("MAS_API_URL", $MasUrlDefault, "User")
$env:MAS_API_URL = $MasUrlDefault
if ($cfg) {
    if ($cfg.proxmox_api_token) {
        [System.Environment]::SetEnvironmentVariable("PROXMOX_API_TOKEN", $cfg.proxmox_api_token, "User")
        $env:PROXMOX_API_TOKEN = $cfg.proxmox_api_token
        Write-Host "[Bootstrap] Set PROXMOX_API_TOKEN (PVEAPIToken format)" -ForegroundColor Green
    }
    if ($cfg.proxmox_host) {
        [System.Environment]::SetEnvironmentVariable("PROXMOX_HOST", $cfg.proxmox_host, "User")
        $env:PROXMOX_HOST = $cfg.proxmox_host
        Write-Host "[Bootstrap] Set PROXMOX_HOST = $($cfg.proxmox_host)" -ForegroundColor Green
    }
}

# --- Node.js 22+ ---
$nodeOk = $false
try {
    $v = (node --version 2>$null) -replace 'v', ''
    $major = [int]($v.Split('.')[0])
    if ($major -ge 22) { $nodeOk = $true }
} catch {}
if (-not $nodeOk) {
    Write-Host "[Bootstrap] Installing Node.js 22 LTS via winget..." -ForegroundColor Cyan
    winget install OpenJS.NodeJS.LTS --accept-package-agreements --accept-source-agreements
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")
    # Refreshed PATH; node may need new shell
    $nodeCheck = Get-Command node -ErrorAction SilentlyContinue
    if (-not $nodeCheck) {
        Write-Host "[Bootstrap] Node installed. Restart PowerShell and re-run to continue."
        if (-not $NoRestart) { exit 0 }
    }
}
Write-Host "[Bootstrap] Node: $(node --version)" -ForegroundColor Green

# --- OpenClaw ---
if (-not $SkipOpenClawInstall) {
    Write-Host "[Bootstrap] Installing OpenClaw (no onboard for automation)..." -ForegroundColor Cyan
    try {
        $installScript = [scriptblock]::Create((Invoke-WebRequest -Uri "https://openclaw.ai/install.ps1" -UseBasicParsing).Content)
        & $installScript -NoOnboard
    } catch {
        Write-Host "[Bootstrap] Install script failed, trying npm install -g openclaw..." -ForegroundColor Yellow
        npm install -g openclaw@latest
        npx --yes openclaw onboard --install-daemon 2>$null
    }
    $oc = Get-Command openclaw -ErrorAction SilentlyContinue
    if ($oc) { Write-Host "[Bootstrap] OpenClaw installed." -ForegroundColor Green } else { Write-Host "[Bootstrap] OpenClaw may need new shell; verify with: openclaw doctor" -ForegroundColor Yellow }
}

# --- Browser automation (Playwright) ---
Write-Host "[Bootstrap] Installing Playwright browsers..." -ForegroundColor Cyan
npx --yes playwright install chromium 2>$null
Write-Host "[Bootstrap] Playwright chromium ready." -ForegroundColor Green

# --- Environment for OpenClaw ---
$env:OPENCLAW_HOME = $OpenClawHome
$env:OPENCLAW_STATE_DIR = "$OpenClawHome\state"
[System.Environment]::SetEnvironmentVariable("OPENCLAW_HOME", $OpenClawHome, "User")
[System.Environment]::SetEnvironmentVariable("OPENCLAW_STATE_DIR", "$OpenClawHome\state", "User")
[System.Environment]::SetEnvironmentVariable("CSUITE_ROOT", $CsuiteRoot, "User")
[System.Environment]::SetEnvironmentVariable("CSUITE_ROLE", $Role, "User")

# --- Persona seed stub (role-specific overlay applied later) ---
$personaSeed = @"
# C-Suite assistant — $Role
# Bounded autonomy: propose and execute within policy; escalate decisions to Morgan.
# Reporting path: MYCA VM 191, MAS VM 188.
# Role: $Role — See config/csuite_role_manifests.yaml for full manifest.
"@
$personaPath = "$CsuiteRoot\persona_seeds\${Role}_default.md"
$personaSeed | Out-File -FilePath $personaPath -Encoding utf8
Write-Host "[Bootstrap] Persona seed: $personaPath" -ForegroundColor Green

# --- Remote access: ensure RDP enabled (optional) ---
# Enable-NetFirewallRule -DisplayGroup "Remote Desktop" 2>$null

Write-Host "[Bootstrap] Golden image bootstrap complete for role: $Role" -ForegroundColor Green
Write-Host "  CSUITE_ROOT: $CsuiteRoot"
Write-Host "  OPENCLAW_HOME: $OpenClawHome"
Write-Host "  CSUITE_ROLE=$Role, MAS_API_URL=$MasUrlDefault"
Write-Host "  Next: .\apply_role_manifest.ps1 -Role $Role"
Write-Host "  Heartbeat: Register csuite_heartbeat.ps1 as scheduled task (every 1 min)"
