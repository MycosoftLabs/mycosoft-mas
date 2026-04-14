#Requires -Version 5.1
<#
.SYNOPSIS
  Start Ollama (Nemorton/OpenAI-compatible), PersonaPlex Moshi (8998), and PersonaPlex bridge (8999) on the voice Legion.
  Intended for Task Scheduler at startup or manual run after login.

.NOTES
  Prerequisites on this host:
  - mycosoft-mas cloned (see $RepoRoot candidates)
  - Setup-PersonaPlex-VoiceHost.ps1 completed (.personaplex-venv)
  - personaplex-repo + models/personaplex-7b-v1 (real assets; no mocks)
  - Ollama installed (Windows service or WSL); pull your Nemotron/GGUF model before relying on MYCA.

  Firewall: allows LAN 192.168.0.0/24 to 8998, 8999, 11434 (idempotent rules).

  Env:
    MYCOSOFT_MAS_ROOT      - override repo path
    MAS_ORCHESTRATOR_URL   - default http://192.168.0.188:8001
#>
param(
    [string]$RepoRoot = "",
    [string]$VenvPath = "",
    [string]$MasOrchestratorUrl = "http://192.168.0.188:8001",
    [switch]$SkipFirewall,
    [switch]$SkipIfRunning
)

$ErrorActionPreference = 'Stop'
$LogDir = Join-Path $env:USERPROFILE "MycosoftData\logs"
if (-not (Test-Path $LogDir)) { New-Item -ItemType Directory -Force -Path $LogDir | Out-Null }
$Ts = Get-Date -Format "yyyyMMdd-HHmmss"
$Log = Join-Path $LogDir "voice-24x7-$Ts.log"

function L([string]$m) {
    $line = "$(Get-Date -Format o) $m"
    Add-Content -Path $Log -Value $line
    Write-Host $line
}

if (-not $RepoRoot) {
    foreach ($c in @(
            $env:MYCOSOFT_MAS_ROOT,
            (Join-Path $env:USERPROFILE "mycosoft-mas"),
            (Join-Path $env:USERPROFILE "Desktop\mycosoft-gpu-node"),
            (Join-Path $env:USERPROFILE "Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas")
        )) {
        if ($c -and (Test-Path (Join-Path $c "start_personaplex.py"))) {
            $RepoRoot = $c
            break
        }
    }
}
if (-not $RepoRoot -or -not (Test-Path $RepoRoot)) {
    throw "mycosoft-mas repo not found. Clone it or set MYCOSOFT_MAS_ROOT."
}

if (-not $VenvPath) {
    $VenvPath = Join-Path $env:USERPROFILE ".personaplex-venv"
}
$Py = Join-Path $VenvPath "Scripts\python.exe"
if (-not (Test-Path $Py)) {
    throw "Voice venv missing at $VenvPath. Run Setup-PersonaPlex-VoiceHost.ps1."
}

function Test-Listen([int]$Port) {
    try {
        $c = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
        return $null -ne $c
    } catch { return $false }
}

if (-not $SkipFirewall) {
    $fwName = "Mycosoft-Voice-LAN"
    foreach ($port in @(8998, 8999, 11434)) {
        $existing = Get-NetFirewallRule -DisplayName "$fwName-$port" -ErrorAction SilentlyContinue
        if (-not $existing) {
            New-NetFirewallRule -DisplayName "$fwName-$port" -Direction Inbound `
                -LocalPort $port -Protocol TCP -Action Allow `
                -RemoteAddress 192.168.0.0/24 -Profile Private,Domain | Out-Null
            L "Firewall: allowed LAN -> TCP $port"
        }
    }
}

if ($SkipIfRunning -and (Test-Listen 8998) -and (Test-Listen 8999)) {
    L "Moshi and bridge already listening; exit."
    exit 0
}

# Ollama (Windows install: default service; ensure port 11434)
if (-not (Test-Listen 11434)) {
    $ollama = Get-Command ollama -ErrorAction SilentlyContinue
    if ($ollama) {
        L "Starting ollama serve in background..."
        Start-Process -FilePath $ollama.Source -ArgumentList "serve" -WindowStyle Hidden `
            -RedirectStandardOutput (Join-Path $LogDir "ollama-stdout.log") `
            -RedirectStandardError (Join-Path $LogDir "ollama-stderr.log")
        Start-Sleep -Seconds 3
    } else {
        L "WARN: ollama not on PATH; start Ollama app or WSL ollama manually."
    }
} else {
    L "Port 11434 already listening (Ollama)."
}

$env:MAS_ORCHESTRATOR_URL = $MasOrchestratorUrl
$env:MOSHI_HOST = "127.0.0.1"
$env:MOSHI_PORT = "8998"

if (-not (Test-Listen 8998)) {
    L "Starting Moshi (PersonaPlex)..."
    Start-Process -FilePath $Py -ArgumentList "`"$RepoRoot\start_personaplex.py`"" -WorkingDirectory $RepoRoot `
        -WindowStyle Minimized `
        -RedirectStandardOutput (Join-Path $LogDir "moshi-stdout.log") `
        -RedirectStandardError (Join-Path $LogDir "moshi-stderr.log")
} else {
    L "Port 8998 already listening; skip Moshi start."
}

Start-Sleep -Seconds 5

if (-not (Test-Listen 8999)) {
    L "Starting PersonaPlex bridge..."
    $bridge = Join-Path $RepoRoot "services\personaplex-local\personaplex_bridge_nvidia.py"
    if (-not (Test-Path $bridge)) { throw "Missing $bridge" }
    Start-Process -FilePath $Py -ArgumentList "`"$bridge`"" -WorkingDirectory $RepoRoot `
        -WindowStyle Minimized `
        -RedirectStandardOutput (Join-Path $LogDir "bridge-stdout.log") `
        -RedirectStandardError (Join-Path $LogDir "bridge-stderr.log")
} else {
    L "Port 8999 already listening; skip bridge start."
}

L "Done. Logs under $LogDir. Health: http://127.0.0.1:8999/health"
