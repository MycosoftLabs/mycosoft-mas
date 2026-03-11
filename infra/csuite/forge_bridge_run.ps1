# Forge Bridge Run — Enriched Heartbeat to MAS
# Date: March 8, 2026
# Runs on CTO VM 194. Sends cursor_status, openclaw_status, workspace_status to C-Suite API.
# Called by ensure-cto-vm-watchdog.ps1 or as a standalone scheduled task.
# Config: MAS_API_URL, CTO_VM_IP (default 192.168.0.194)

param([switch]$Silent)

$ErrorActionPreference = "SilentlyContinue"
$MasUrl = $env:MAS_API_URL; if (-not $MasUrl) { $MasUrl = "http://192.168.0.188:8001" }
$CtoIp = $env:CTO_VM_IP; if (-not $CtoIp) { $CtoIp = "192.168.0.194" }
$CodeRoot = $env:CTO_CODE_ROOT; if (-not $CodeRoot) { $CodeRoot = "C:\Users\$env:USERNAME\Mycosoft\CODE" }

# --- Detect Cursor ---
$cursorStatus = "unknown"
$cursorProc = Get-Process -Name "Cursor" -ErrorAction SilentlyContinue
if (-not $cursorProc) { $cursorProc = Get-Process -Name "Code" -ErrorAction SilentlyContinue }
if ($cursorProc) { $cursorStatus = "running" } else { $cursorStatus = "not_running" }

# --- Detect OpenClaw ---
$openclawStatus = "unknown"
$ocProc = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -match "openclaw" }
if ($ocProc) { $openclawStatus = "running" } else {
    $ocProc = Get-Process -Name "node" -ErrorAction SilentlyContinue
    if ($ocProc) { $openclawStatus = "ready" } else { $openclawStatus = "not_running" }
}

# --- Workspace status ---
$workspaceStatus = "unknown"
$MasRepo = Join-Path $CodeRoot "MAS\mycosoft-mas"
if (Test-Path (Join-Path $MasRepo ".git")) {
    try {
        Push-Location $MasRepo
        $branch = git rev-parse --abbrev-ref HEAD 2>$null
        $dirty = git status --porcelain 2>$null
        Pop-Location
        if ($branch) {
            $workspaceStatus = if ($dirty) { "dirty" } else { "synced" }
        } else { $workspaceStatus = "invalid" }
    } catch { $workspaceStatus = "error" }
} else { $workspaceStatus = "missing" }

# --- POST enriched heartbeat ---
$body = @{
    role = "CTO"
    assistant_name = "Forge"
    ip = $CtoIp
    status = "healthy"
    primary_tool = "Cursor"
    extra = @{
        cursor_status = $cursorStatus
        openclaw_status = $openclawStatus
        workspace_status = $workspaceStatus
        source = "forge_bridge_run"
    }
} | ConvertTo-Json -Depth 5

try {
    $r = Invoke-RestMethod -Uri "$MasUrl/api/csuite/heartbeat" -Method POST -Body $body -ContentType "application/json" -TimeoutSec 10
    if (-not $Silent) { Write-Host "[Forge] Enriched heartbeat OK (cursor=$cursorStatus, openclaw=$openclawStatus, workspace=$workspaceStatus)" -ForegroundColor Green }
} catch {
    if (-not $Silent) { Write-Warning "[Forge] Heartbeat failed: $_" }
}
