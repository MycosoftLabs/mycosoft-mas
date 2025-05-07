# Stop and remove existing containers
docker-compose down

# Rebuild images
docker-compose build --no-cache mas-orchestrator mas-agent-manager mas-task-manager mas-integration-manager

# Start services
docker-compose up -d

# Wait for services to be ready
Start-Sleep -Seconds 10

# Check service status
docker-compose ps

# Display logs
Write-Host "Displaying logs..."
docker-compose logs --tail=50 