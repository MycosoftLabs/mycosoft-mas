#Requires -Version 5.1
<#
.SYNOPSIS
  Create a single canonical directory tree on a Legion (or dev PC) for models, weights, caches, data, and local memory artifacts.

.DESCRIPTION
  Creates %MYCOSOFT_DATA_ROOT% (default: ~\MycosoftData) with subfolders for:
  Hugging Face, PyTorch, Ollama, Earth2 checkpoints, voice weights, datasets, scratch, logs, and optional local embedding/working stores.

  Sets **User** environment variables so HF, torch, Ollama, and MAS tooling resolve to real paths (no mock data).

.PARAMETER RootPath
  Root folder. Use a fast large drive when available, e.g. D:\MycosoftData

.PARAMETER Role
  Tags a small README for Earth2 vs Voice host; all directories are still created for a consistent layout.

.EXAMPLE
  .\Initialize-MycosoftDataLayout.ps1 -RootPath "D:\MycosoftData" -Role Earth2
#>
param(
    [string]$RootPath = "",
    [ValidateSet('Earth2', 'Voice', 'All')]
    [string]$Role = 'All'
)

$ErrorActionPreference = 'Stop'

if (-not $RootPath) {
    $RootPath = Join-Path $env:USERPROFILE "MycosoftData"
}

$RootPath = $RootPath.TrimEnd('\')
Write-Host "`n=== Mycosoft data layout ===" -ForegroundColor Cyan
Write-Host "Root: $RootPath" -ForegroundColor Green
Write-Host "Role tag: $Role" -ForegroundColor Gray

$subdirs = @(
    "models\earth2",
    "models\voice",
    "models\shared",
    "weights",
    "cache\huggingface",
    "cache\huggingface\hub",
    "cache\huggingface\datasets",
    "cache\huggingface\transformers",
    "cache\torch",
    "cache\pip",
    "ollama",
    "data",
    "data\datasets",
    "memory\embeddings",
    "memory\working",
    "scratch",
    "logs"
)

foreach ($rel in $subdirs) {
    $full = Join-Path $RootPath $rel
    if (-not (Test-Path $full)) {
        New-Item -ItemType Directory -Force -Path $full | Out-Null
    }
}

$readme = @"
Mycosoft data root (created $(Get-Date -Format o))
Host role tag: $Role

Subfolders:
  models/earth2   - Earth-2 / earth2studio checkpoints (configure paths in Earth2 API / NVIDIA docs)
  models/voice    - Moshi, TTS, STT weights not using HF hub cache
  models/shared   - Shared large artifacts
  weights         - Extra weight files / symlinks as needed
  cache/huggingface - HF_HOME (Hub + default cache)
  cache/torch     - TORCH_HOME
  cache/pip       - PIP_CACHE_DIR (optional)
  ollama          - OLLAMA_MODELS when set (see Ollama docs)
  data/           - Datasets, audio, NetCDF/Zarr inputs (real data only)
  memory/embeddings - Local embedding / vector working files (not system RAM)
  memory/working    - Session or RAG scratch bound to this host
  scratch/        - Ephemeral processing
  logs/           - Service logs

Environment variables are set at User scope to point here. Restart terminals/apps after running.
"@
Set-Content -Path (Join-Path $RootPath "README-MYCOSOFT-DATA.txt") -Value $readme -Encoding UTF8

# --- User environment variables (persistent) ---
function Set-UserEnv([string]$Name, [string]$Value) {
    [Environment]::SetEnvironmentVariable($Name, $Value, 'User')
    Write-Host "  $Name = $Value" -ForegroundColor DarkGray
}

Set-UserEnv 'MYCOSOFT_DATA_ROOT' $RootPath
Set-UserEnv 'HF_HOME' (Join-Path $RootPath 'cache\huggingface')
Set-UserEnv 'HF_HUB_CACHE' (Join-Path $RootPath 'cache\huggingface\hub')
Set-UserEnv 'HUGGINGFACE_HUB_CACHE' (Join-Path $RootPath 'cache\huggingface\hub')
Set-UserEnv 'HF_DATASETS_CACHE' (Join-Path $RootPath 'cache\huggingface\datasets')
Set-UserEnv 'TRANSFORMERS_CACHE' (Join-Path $RootPath 'cache\huggingface\transformers')
Set-UserEnv 'TORCH_HOME' (Join-Path $RootPath 'cache\torch')
Set-UserEnv 'PIP_CACHE_DIR' (Join-Path $RootPath 'cache\pip')
Set-UserEnv 'XDG_CACHE_HOME' (Join-Path $RootPath 'cache')
Set-UserEnv 'OLLAMA_MODELS' (Join-Path $RootPath 'ollama')
Set-UserEnv 'MYCOSOFT_EARTH2_CHECKPOINTS' (Join-Path $RootPath 'models\earth2')
Set-UserEnv 'MYCOSOFT_VOICE_MODELS' (Join-Path $RootPath 'models\voice')
Set-UserEnv 'MYCOSOFT_LOCAL_MEMORY' (Join-Path $RootPath 'memory')

Write-Host ""
Write-Host "User environment variables updated. Open a new PowerShell or reboot apps (Cursor, Docker, Ollama)." -ForegroundColor Yellow
Write-Host "Optional: migrate Ollama data to ollama folder under MycosoftData; see Ollama docs." -ForegroundColor Gray
Write-Host "Done." -ForegroundColor Green
Write-Host ""
