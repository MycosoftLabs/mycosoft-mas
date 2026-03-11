# C-Suite Executive Assistant — Heartbeat to MAS
# Date: March 7, 2026
# Run on each C-Suite VM (CEO, CFO, CTO, COO) via Task Scheduler
# Usage: .\csuite_heartbeat.ps1
#        .\csuite_heartbeat.ps1 -RegisterTask   # Register as scheduled task (every 1 min)
# Config: role_config.json or emit_role_config.py; env CSUITE_ROLE, MAS_API_URL override
# Heartbeat interval from config/csuite_openclaw_defaults.yaml (default 60s)

param(
    [switch]$Once,
    [switch]$RegisterTask
)

$ErrorActionPreference = "Stop"
$Role = if ($env:CSUITE_ROLE) { $env:CSUITE_ROLE.ToLower() } else { "ceo" }

$Manifests = @{
    ceo = @{ Role = "CEO"; Name = "Atlas"; Tool = "MYCAOS"; IP = "192.168.0.192" }
    cfo = @{ Role = "CFO"; Name = "Meridian"; Tool = "Perplexity"; IP = "192.168.0.193" }
    cto = @{ Role = "CTO"; Name = "Forge"; Tool = "Cursor"; IP = "192.168.0.194" }
    coo = @{ Role = "COO"; Name = "Nexus"; Tool = "Claude Cowork"; IP = "192.168.0.195" }
}

$cfg = $null
$heartbeatUrl = $null
$intervalSec = 60
$configPaths = @(
    "$env:CSUITE_ROOT\config\role_config.json",
    "$env:ProgramData\Mycosoft\C-Suite\role_config.json",
    (Join-Path $PSScriptRoot "..\..\config\role_config.json")
)

foreach ($p in $configPaths) {
    if ($p -and (Test-Path $p)) {
        try {
            $json = Get-Content $p -Raw | ConvertFrom-Json
            if ($json.role_key -eq $Role -or $json.role -eq $Role) {
                $cfg = @{
                    Role = $json.role
                    Name = $json.assistant_name
                    Tool = $json.primary_tool
                    IP = $json.ip
                }
                $heartbeatUrl = $json.heartbeat_endpoint
                $intervalSec = $json.heartbeat_interval_sec
                break
            }
        } catch {}
    }
}

if (-not $cfg) {
    $emitScript = Join-Path $PSScriptRoot "emit_role_config.py"
    $tempConfig = "$env:TEMP\csuite_role_config_$Role.json"
    if ((Test-Path $emitScript) -and (Get-Command python -ErrorAction SilentlyContinue)) {
        try {
            python $emitScript -r $Role -o $tempConfig 2>$null
            if (Test-Path $tempConfig) {
                $json = Get-Content $tempConfig -Raw | ConvertFrom-Json
                $cfg = @{ Role = $json.role; Name = $json.assistant_name; Tool = $json.primary_tool; IP = $json.ip }
                $heartbeatUrl = $json.heartbeat_endpoint
                $intervalSec = $json.heartbeat_interval_sec
                Remove-Item $tempConfig -Force -ErrorAction SilentlyContinue
            }
        } catch {}
    }
}

if (-not $cfg) {
    $cfg = $Manifests[$Role]
    Write-Warning "[C-Suite] Using fallback config for $Role. Place role_config.json for authoritative config."
}
if (-not $heartbeatUrl) {
    $MasUrl = $env:MAS_API_URL; if (-not $MasUrl) { $MasUrl = "http://192.168.0.188:8001" }
    $heartbeatUrl = "$MasUrl/api/csuite/heartbeat"
}

$body = @{
    role = $cfg.Role
    assistant_name = $cfg.Name
    ip = $cfg.IP
    status = "healthy"
    primary_tool = $cfg.Tool
} | ConvertTo-Json

if ($RegisterTask) {
    $scriptPath = $MyInvocation.MyCommand.Path
    if (-not $scriptPath) { $scriptPath = Join-Path $PSScriptRoot "csuite_heartbeat.ps1" }
    $taskName = "Mycosoft-CSuite-Heartbeat"
    $action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-ExecutionPolicy Bypass -NoProfile -File `"$scriptPath`" -Once"
    $trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Minutes 1) -RepetitionDuration (New-TimeSpan -Days 9999)
    $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
    Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -Force | Out-Null
    Write-Host "[C-Suite] Scheduled task registered: $taskName (every 1 min)" -ForegroundColor Green
    exit 0
}

try {
    $r = Invoke-RestMethod -Uri $heartbeatUrl -Method POST -Body $body -ContentType "application/json" -TimeoutSec 5
    if ($Once) { Write-Host "[C-Suite] $($cfg.Role) heartbeat OK" }
} catch {
    if ($Once) { Write-Warning "[C-Suite] $($cfg.Role) heartbeat failed: $_" }
}

if (-not $Once) {
    while ($true) {
        Start-Sleep -Seconds $intervalSec
        try {
            Invoke-RestMethod -Uri $heartbeatUrl -Method POST -Body $body -ContentType "application/json" -TimeoutSec 5 | Out-Null
        } catch { }
    }
}
