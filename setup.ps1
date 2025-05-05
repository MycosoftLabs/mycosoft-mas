# Docker environment setup script for Mycosoft MAS
Write-Host "Setting up Docker environment..."

# Check if Docker is running
try {
    docker info | Out-Null
    Write-Host "Docker is running" -ForegroundColor Green
} catch {
    Write-Host "Docker is not running. Please start Docker Desktop and try again." -ForegroundColor Red
    exit 1
}

# Build Docker images
Write-Host "Building Docker images..."
docker-compose build

# Start Docker containers
Write-Host "Starting Docker containers..."
docker-compose up -d

# Wait for services to be ready
Write-Host "Waiting for services to be ready..."
Start-Sleep -Seconds 30

# Verify services are running
$services = @(
    @{Name = "MAS Orchestrator"; Port = 8000},
    @{Name = "Grafana"; Port = 3000},
    @{Name = "Prometheus"; Port = 9090},
    @{Name = "AlertManager"; Port = 9093}
)

foreach ($service in $services) {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:$($service.Port)" -UseBasicParsing
        Write-Host "$($service.Name) is running" -ForegroundColor Green
    } catch {
        Write-Host "$($service.Name) is not responding" -ForegroundColor Red
    }
}

Write-Host "Docker environment setup completed!" 