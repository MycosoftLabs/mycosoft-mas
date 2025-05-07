# Add Docker to PATH
$env:Path += ";C:\Program Files\Docker\Docker\resources\bin;C:\Program Files\Docker\Docker"

# Start Docker Desktop if not running
$dockerProcess = Get-Process "Docker Desktop" -ErrorAction SilentlyContinue
if (-not $dockerProcess) {
    Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe"
    Write-Host "Starting Docker Desktop..."
}

# Wait for Docker to be ready
$maxAttempts = 30
$attempt = 0
$dockerReady = $false

Write-Host "Waiting for Docker to be ready..."
while (-not $dockerReady -and $attempt -lt $maxAttempts) {
    try {
        $null = & "C:\Program Files\Docker\Docker\resources\bin\docker.exe" ps 2>&1
        if ($LASTEXITCODE -eq 0) {
            $dockerReady = $true
            Write-Host "Docker is ready!"
        }
    } catch {
        Start-Sleep -Seconds 10
        $attempt++
        Write-Host "Waiting for Docker to initialize... Attempt $attempt of $maxAttempts"
    }
}

if (-not $dockerReady) {
    Write-Host "Docker failed to initialize after $maxAttempts attempts. Please check Docker Desktop status."
    exit 1
}

# Activate Python virtual environment
.\venv\Scripts\activate

# Start MAS services using docker compose
& "C:\Program Files\Docker\Docker\resources\bin\docker.exe" compose up -d

Write-Host "MAS services are starting up. Please wait a few minutes for all services to be ready."
Write-Host "You can check the status using: docker compose ps" 