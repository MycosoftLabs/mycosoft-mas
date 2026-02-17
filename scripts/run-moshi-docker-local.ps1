# Run Moshi Voice Server - RTX 5090 Full GPU
# Updated: February 17, 2026
#
# Always uses --gpus all + CUDA. Never CPU.
# Model cache in Docker volume "moshi-model-cache" - persists across rebuilds.
#
# Usage:
#   .\scripts\run-moshi-docker-local.ps1              # build if needed, run GPU
#   .\scripts\run-moshi-docker-local.ps1 -Rebuild     # force full rebuild
#   .\scripts\run-moshi-docker-local.ps1 -SkipBuild   # skip build, just restart

param(
    [switch]$SkipBuild,
    [switch]$Rebuild
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$imageName   = "mycosoft/moshi-voice:latest"
$containerName = "moshi-voice"
$dockerfile  = Join-Path $repoRoot "services\personaplex-local\Dockerfile.moshi"
$context     = Join-Path $repoRoot "services\personaplex-local"
$volumeName  = "moshi-model-cache"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Moshi Voice - RTX 5090 GPU (sm_120)    " -ForegroundColor Cyan
Write-Host "CUDA 12.8 / PyTorch cu128              " -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Verify Docker
Write-Host "[1] Docker..." -ForegroundColor Yellow
docker version --format "    Server: {{.Server.Version}}" 2>&1
if ($LASTEXITCODE -ne 0) { Write-Host "[ERROR] Docker not running." -ForegroundColor Red; exit 1 }

# Verify GPU passthrough
Write-Host "[2] NVIDIA GPU in Docker..." -ForegroundColor Yellow
$gpuOut = docker run --rm --gpus all "nvidia/cuda:12.8.0-base-ubuntu22.04" nvidia-smi --query-gpu=name,memory.total --format=csv,noheader 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "    $gpuOut" -ForegroundColor Green
} else {
    Write-Host "    [WARN] GPU check failed - continuing anyway (Docker may still pass GPU)" -ForegroundColor Yellow
}

# Build
$imageExists = docker images -q $imageName 2>$null
if ($SkipBuild -and $imageExists) {
    Write-Host "[3] Using existing image: $imageName" -ForegroundColor Green
} else {
    Write-Host "[3] Building Moshi image (CUDA 12.8 + cu128)..." -ForegroundColor Cyan
    Write-Host "    This takes ~20-25 min on first run (PyTorch download + Moshi deps)" -ForegroundColor Gray
    Write-Host "    Subsequent builds use Docker layer cache (~2-3 min)." -ForegroundColor Gray
    Write-Host ""
    $buildArgs = @("build", "-t", $imageName, "-f", $dockerfile)
    if ($Rebuild) { $buildArgs += "--no-cache" }
    $buildArgs += $context
    $buildStart = Get-Date
    docker @buildArgs
    if ($LASTEXITCODE -ne 0) { Write-Host "[ERROR] Build failed." -ForegroundColor Red; exit 1 }
    $mins = [Math]::Round(((Get-Date) - $buildStart).TotalMinutes, 1)
    Write-Host "[OK] Built in ${mins} min" -ForegroundColor Green
}

# Stop and remove existing container
Write-Host "[4] Stopping existing container..." -ForegroundColor Yellow
docker rm -f $containerName 2>$null | Out-Null

# Create volume if it doesn't exist
docker volume inspect $volumeName 2>$null | Out-Null
if ($LASTEXITCODE -ne 0) {
    docker volume create $volumeName | Out-Null
    Write-Host "    Created volume: $volumeName" -ForegroundColor Green
} else {
    Write-Host "    Using existing volume: $volumeName (model cache preserved)" -ForegroundColor Green
}

# Run with GPU + cache volume
Write-Host "[5] Starting container with GPU..." -ForegroundColor Cyan
docker run -d `
    --name $containerName `
    --restart unless-stopped `
    --gpus all `
    -p 8998:8998 `
    -v "${volumeName}:/root/.cache" `
    -e MOSHI_DEVICE=cuda `
    -e TORCHDYNAMO_DISABLE=1 `
    $imageName

if ($LASTEXITCODE -ne 0) { Write-Host "[ERROR] Failed to start." -ForegroundColor Red; exit 1 }

Write-Host ""
Write-Host "[6] Waiting for Moshi to load (60-90s on GPU)..." -ForegroundColor Yellow
Write-Host "    Model cached in volume '$volumeName' - next start is same speed." -ForegroundColor Gray
Write-Host ""

# Poll until WebSocket port responds
$deadline = (Get-Date).AddSeconds(180)
while ((Get-Date) -lt $deadline) {
    Start-Sleep -Seconds 5
    $status = docker inspect $containerName --format "{{.State.Status}}" 2>$null
    if ($status -ne "running") {
        Write-Host "[ERROR] Container stopped. Last logs:" -ForegroundColor Red
        docker logs $containerName --tail 30 2>&1
        exit 1
    }
    try {
        $t = New-Object System.Net.Sockets.TcpClient
        $t.Connect("localhost", 8998)
        $t.Close()
        $elapsed = [int]((Get-Date) - (Get-Date)).TotalSeconds
        Write-Host ""
        Write-Host "========================================" -ForegroundColor Green
        Write-Host "Moshi is ONLINE on port 8998 (GPU)     " -ForegroundColor Green
        Write-Host "========================================" -ForegroundColor Green
        Write-Host ""
        Write-Host "  WS endpoint : ws://localhost:8998/api/chat" -ForegroundColor White
        Write-Host "  Remote (gpu01 bridge via tunnel): ws://127.0.0.1:19198/api/chat" -ForegroundColor White
        Write-Host ""
        Write-Host "Next steps:" -ForegroundColor Cyan
        Write-Host "  1. Run tunnel: ssh -N -R 19198:127.0.0.1:8998 mycosoft@192.168.0.190" -ForegroundColor Gray
        Write-Host "  2. Start bridge on gpu01 (MOSHI_HOST=127.0.0.1 MOSHI_PORT=19198)" -ForegroundColor Gray
        Write-Host "  3. Open http://localhost:3010/test-voice" -ForegroundColor Gray
        exit 0
    } catch {
        $elapsed = [int]((Get-Date) - (Get-Date)).TotalSeconds
        Write-Host "  Loading..." -ForegroundColor Gray
    }
}

Write-Host "[WARN] Moshi still loading after 3 minutes. Check:" -ForegroundColor Yellow
Write-Host "  docker logs $containerName --tail 30" -ForegroundColor White
