#Requires -Version 5.1
<#
.SYNOPSIS
  Prepare Legion 4080B (voice): VC++ runtime, Python venv, PyTorch CUDA, and PersonaPlex bridge dependencies from repo requirements.
  Run on ubiquity-gpu-voice (192.168.0.241) after NVIDIA driver works (nvidia-smi). Requires network for pip.

.NOTES
  Clone mycosoft-mas first (e.g. git clone https://github.com/MycosoftLabs/mycosoft-mas.git %USERPROFILE%\mycosoft-mas).
  Nemotron is consumed via MAS/orchestrator OpenAI-compatible endpoints (Ollama/vLLM on LAN); install Ollama separately if you run models on this host.
#>
param(
    [string]$RepoRoot = "",
    [string]$VenvPath = "",
    [string]$CudaIndexUrl = "https://download.pytorch.org/whl/cu124"
)

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'

if (-not $RepoRoot) {
    $RepoRoot = Join-Path $env:USERPROFILE "mycosoft-mas"
}
if (-not $VenvPath) {
    $VenvPath = Join-Path $env:USERPROFILE ".personaplex-venv"
}

$ReqBridge = Join-Path $RepoRoot "services\personaplex-local\requirements-personaplex.txt"
$ReqLocal = Join-Path $RepoRoot "services\personaplex-local\requirements.txt"
if (-not (Test-Path $ReqBridge)) {
    throw "Missing $ReqBridge - clone mycosoft-mas to $RepoRoot first."
}

$Log = Join-Path $env:USERPROFILE "Desktop\personaplex-setup-$(Get-Date -Format yyyyMMdd-HHmmss).log"
function L($m) { Add-Content $Log $m; Write-Host $m }

L "Repo: $RepoRoot"
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
    L "Installing Python 3.12 via winget..."
    winget install -e --id Python.Python.3.12 --accept-package-agreements --accept-source-agreements --silent
    $candidates = @(
        (Join-Path $env:LocalAppData "Programs\Python\Python312\python.exe"),
        "${env:ProgramFiles}\Python312\python.exe"
    )
    foreach ($c in $candidates) {
        if (Test-Path $c) { L "Using: $c"; return @{ Cmd = $c; Args = @() } }
    }
    throw "Python 3.12 not found after winget. Install manually, then re-run."
}

$pyInfo = Ensure-Python312
if ($pyInfo.Cmd -eq 'py') {
    & py -3 -m venv $VenvPath
} else {
    & $pyInfo.Cmd -m venv $VenvPath
}

$pip = Join-Path $VenvPath "Scripts\pip.exe"
$pythonExe = Join-Path $VenvPath "Scripts\python.exe"

cmd /c "`"$pythonExe`" -m pip install --upgrade pip wheel setuptools >> `"$Log`" 2>&1"

L "Installing PyTorch (CUDA) from $CudaIndexUrl ..."
cmd /c "`"$pip`" install torch torchaudio --index-url $CudaIndexUrl >> `"$Log`" 2>&1"

L "Installing PersonaPlex bridge requirements (pinned) ..."
cmd /c "`"$pip`" install -r `"$ReqBridge`" >> `"$Log`" 2>&1"

if (Test-Path $ReqLocal) {
    L "Installing PersonaPlex local server requirements (may upgrade torch; re-pin CUDA if needed) ..."
    cmd /c "`"$pip`" install -r `"$ReqLocal`" >> `"$Log`" 2>&1"
    L "Re-applying CUDA PyTorch build over any CPU-only resolution ..."
    cmd /c "`"$pip`" install --upgrade torch torchaudio --index-url $CudaIndexUrl >> `"$Log`" 2>&1"
}

cmd /c "`"$pythonExe`" -c ""import torch; print('torch', torch.__version__, 'cuda', torch.cuda.is_available())"" >> `"$Log`" 2>&1"
Get-Content $Log -Tail 25 | ForEach-Object { Write-Host $_ }

L "Done. Activate: & `"$VenvPath\Scripts\Activate.ps1`""
L "Run bridge from repo: cd `"$RepoRoot`"; .\.personaplex-venv\Scripts\python.exe services\personaplex-local\bridge_api.py (or start_personaplex.ps1 after adjusting paths)."
