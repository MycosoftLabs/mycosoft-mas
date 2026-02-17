# Moshi GPU Build Watcher + Auto-Launch (Feb 17, 2026)
# Waits for the GPU image build to finish, then auto-starts the container.
# Run this once while the build is in progress.

$imageName     = "mycosoft/moshi-voice:latest"
$containerName = "moshi-voice"
$volumeName    = "moshi-model-cache"
$buildTarget   = "18eb00e66"  # commit that contains the CUDA 12.8 fix

Write-Host ""
Write-Host "=== Moshi GPU Build Watcher ===" -ForegroundColor Cyan
Write-Host "Waiting for new image (CUDA 12.8 / cu128 / sm_120)..." -ForegroundColor Yellow
Write-Host "Build running in separate window. Check progress there." -ForegroundColor Gray
Write-Host ""

$deadline = (Get-Date).AddMinutes(40)
$oldSize  = (docker images $imageName --format "{{.Size}}" 2>$null)

while ((Get-Date) -lt $deadline) {
    Start-Sleep -Seconds 30
    $newSize = (docker images $imageName --format "{{.Size}}" 2>$null)
    $created = (docker images $imageName --format "{{.CreatedAt}}" 2>$null)
    
    # Image is new if size changed or created time is recent (< 5 min)
    $isNew = $false
    if ($created) {
        try {
            $age = (Get-Date) - [datetime]$created
            if ($age.TotalMinutes -lt 5) { $isNew = $true }
        } catch {}
    }
    
    if ($isNew -or ($newSize -and $newSize -ne $oldSize)) {
        Write-Host ""
        Write-Host "[OK] New image detected: $newSize" -ForegroundColor Green
        break
    }
    
    $remaining = [int]($deadline - (Get-Date)).TotalMinutes
    Write-Host "  [$(Get-Date -Format 'HH:mm:ss')] Still building... (~${remaining}m remaining)" -ForegroundColor Gray
}

if ((Get-Date) -ge $deadline) {
    Write-Host "[TIMEOUT] Build took too long. Run manually:" -ForegroundColor Red
    Write-Host "  docker build -t mycosoft/moshi-voice:latest -f services/personaplex-local/Dockerfile.moshi services/personaplex-local/" -ForegroundColor White
    exit 1
}

# Remove any stale container
Write-Host ""
Write-Host "Stopping any existing moshi-voice container..." -ForegroundColor Yellow
docker rm -f $containerName 2>$null | Out-Null

# Ensure volume
docker volume inspect $volumeName 2>$null | Out-Null
if ($LASTEXITCODE -ne 0) { docker volume create $volumeName | Out-Null }

# Launch with GPU + persistent cache
Write-Host "Starting GPU container..." -ForegroundColor Cyan
docker run -d `
    --name $containerName `
    --restart unless-stopped `
    --gpus all `
    -p 8998:8998 `
    -v "${volumeName}:/root/.cache" `
    -e MOSHI_DEVICE=cuda `
    -e TORCHDYNAMO_DISABLE=1 `
    $imageName

if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Container failed to start" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Waiting for Moshi GPU to load model (60-90s)..." -ForegroundColor Yellow
$deadline2 = (Get-Date).AddSeconds(180)
while ((Get-Date) -lt $deadline2) {
    Start-Sleep -Seconds 5
    try {
        $t = New-Object System.Net.Sockets.TcpClient
        $t.Connect("localhost", 8998)
        $t.Close()
        Write-Host ""
        Write-Host "======================================" -ForegroundColor Green
        Write-Host "MOSHI GPU ONLINE - port 8998 ready   " -ForegroundColor Green
        Write-Host "======================================" -ForegroundColor Green
        Write-Host ""
        Write-Host "Open http://localhost:3010/test-voice and click Start MYCA Voice" -ForegroundColor Cyan
        Write-Host "(Tunnel must be running: ssh -N -R 19198:127.0.0.1:8998 mycosoft@192.168.0.190)" -ForegroundColor Gray
        exit 0
    } catch {}
    Write-Host "  Loading..." -ForegroundColor Gray
}

Write-Host "[WARN] Still loading. Check: docker logs $containerName --tail 20" -ForegroundColor Yellow
