#Requires -Version 5.1
<#
.SYNOPSIS
  Create a dedicated Python venv and install PyTorch (CUDA) + Earth2 API dependencies for scripts/earth2_api_server.py.
  Run on the Earth-2 Legion (4080A) after NVIDIA driver works (nvidia-smi). Requires network for pip.

.NOTES
  Model weights are not bundled; Earth2Studio loads real checkpoints per NVIDIA / earth2studio docs when you configure them.
#>
param(
    [string]$VenvPath = "",
    [string]$CudaIndexUrl = "https://download.pytorch.org/whl/cu124"
)

$ErrorActionPreference = 'Stop'
# pip writes progress to stderr; do not treat as terminating errors
$ProgressPreference = 'SilentlyContinue'
if (-not $VenvPath) {
    $VenvPath = Join-Path $env:USERPROFILE ".earth2studio-venv"
}

$Log = Join-Path $env:USERPROFILE "Desktop\scripts\earth2-setup-$(Get-Date -Format yyyyMMdd-HHmmss).log"
function L($m) { Add-Content $Log $m; Write-Host $m }

L "Venv: $VenvPath"
L "Log: $Log"

$wingetExe = Get-Command winget -ErrorAction SilentlyContinue
if ($wingetExe) {
    L "Ensuring MSVC runtime (VC++ 2015-2022 x64) for PyTorch DLLs..."
    cmd /c "winget install -e --id Microsoft.VCRedist.2015+.x64 --accept-package-agreements --accept-source-agreements --silent >> `"$Log`" 2>&1"
}

function Ensure-Python312 {
    $py = Get-Command py -ErrorAction SilentlyContinue
    if ($py) {
        $ver = & py -3 -c "import sys; print(sys.version)" 2>$null
        if ($LASTEXITCODE -eq 0) { L "Using Python Launcher: $ver"; return @{ Cmd = 'py'; Args = @('-3') } }
    }
    $python = Get-Command python -ErrorAction SilentlyContinue
    if ($python -and $python.Source -notmatch 'WindowsApps') {
        try {
            $v = & $python.Source --version 2>&1
            if ($?) { L "Using python on PATH: $v"; return @{ Cmd = $python.Source; Args = @() } }
        } catch { }
    }
    L "Installing Python 3.12 via winget (Python.Python.3.12)..."
    $winget = Get-Command winget -ErrorAction SilentlyContinue
    if (-not $winget) { throw "Python not found and winget missing. Install Python 3.10+ from https://www.python.org/downloads/ then re-run." }
    winget install -e --id Python.Python.3.12 --accept-package-agreements --accept-source-agreements --silent
    $candidates = @(
        (Join-Path $env:LocalAppData "Programs\Python\Python312\python.exe"),
        "${env:ProgramFiles}\Python312\python.exe",
        "C:\Python312\python.exe"
    )
    $pyExe = $null
    foreach ($c in $candidates) {
        if (Test-Path $c) { $pyExe = $c; break }
    }
    if (-not $pyExe) {
        throw "winget finished but python.exe not found under common paths. Install Python 3.12 manually, then re-run."
    }
    L "Using: $pyExe"
    return @{ Cmd = $pyExe; Args = @() }
}

$pyInfo = Ensure-Python312
if ($pyInfo.Cmd -eq 'py') {
    & py -3 -m venv $VenvPath
} else {
    & $pyInfo.Cmd -m venv $VenvPath
}

$pip = Join-Path $VenvPath "Scripts\pip.exe"
$pythonExe = Join-Path $VenvPath "Scripts\python.exe"

function Pip-Log([string[]]$PipArguments) {
    # Use cmd so pip's stderr (progress) does not surface as PowerShell errors
    $escaped = $PipArguments | ForEach-Object {
        if ($_ -match '[\s"\[\]]') { '"' + ($_ -replace '"', '\"') + '"' } else { $_ }
    }
    $argLine = $escaped -join ' '
    $batch = "`"$pip`" $argLine"
    cmd /c "$batch >> `"$Log`" 2>&1"
    Get-Content $Log -Tail 40 | ForEach-Object { Write-Host $_ }
}

cmd /c "`"$pythonExe`" -m pip install --upgrade pip wheel setuptools >> `"$Log`" 2>&1"

# PyTorch CUDA (adjust cu124 if driver stack differs)
L "Installing PyTorch from $CudaIndexUrl ..."
Pip-Log -PipArguments @('install', 'torch', 'torchvision', '--index-url', $CudaIndexUrl)

# API stack first; earth2studio often needs Linux/WSL for full deps (e.g. pygrib)
L "Installing fastapi, uvicorn ..."
Pip-Log -PipArguments @('install', 'fastapi', 'uvicorn[standard]')
L "Installing earth2studio (optional - may fail on pure Windows; use WSL Ubuntu if needed)..."
cmd /c "`"$pip`" install earth2studio >> `"$Log`" 2>&1"
if ($LASTEXITCODE -ne 0) {
    L "earth2studio pip install did not complete on Windows (common). Use WSL2 + Linux venv or NVIDIA Earth-2 install docs."
}

cmd /c "`"$pythonExe`" -c ""import torch; print('torch', torch.__version__, 'cuda', torch.cuda.is_available())"" >> `"$Log`" 2>&1"
cmd /c "`"$pythonExe`" -c ""import earth2studio; print('earth2studio', earth2studio.__version__)"" >> `"$Log`" 2>&1"
Get-Content $Log -Tail 15 | ForEach-Object { Write-Host $_ }

L "Done. Activate: & `"$VenvPath\Scripts\Activate.ps1`""
