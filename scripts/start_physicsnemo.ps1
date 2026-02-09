$ErrorActionPreference = "Stop"

$image = "nvcr.io/nvidia/physicsnemo/physicsnemo:25.06"
$containerName = "physicsnemo-service"
$repoRoot = Split-Path -Parent $PSScriptRoot
$serviceScript = Join-Path $PSScriptRoot "physicsnemo_service.py"
$dataDir = Join-Path $repoRoot "data\physicsnemo"

if (!(Test-Path $serviceScript)) {
    throw "Missing service script: $serviceScript"
}

if (!(Test-Path $dataDir)) {
    New-Item -ItemType Directory -Path $dataDir | Out-Null
}

Write-Host "[*] Pulling PhysicsNeMo image ($image)..."
docker pull $image

$existing = docker ps -a --filter "name=^$containerName$" --format "{{.Names}}"
if ($existing -eq $containerName) {
    Write-Host "[*] Removing existing container $containerName..."
    docker rm -f $containerName | Out-Null
}

Write-Host "[*] Starting PhysicsNeMo service on port 8400..."
docker run --gpus all `
  --shm-size=1g `
  --ulimit memlock=-1 `
  --ulimit stack=67108864 `
  --runtime nvidia `
  -p 8400:8400 `
  -v "${serviceScript}:/workspace/service.py" `
  -v "${dataDir}:/workspace/data" `
  --name $containerName `
  -e PHYSICSNEMO_API_PORT=8400 `
  -e PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:512 `
  -d $image `
  python /workspace/service.py | Out-Null

Write-Host "[+] PhysicsNeMo service started: http://localhost:8400"
Write-Host "[+] Health: http://localhost:8400/health"
