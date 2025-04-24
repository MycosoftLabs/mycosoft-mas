# Main setup script for Mycosoft MAS
Write-Host "Starting complete setup for Mycosoft MAS..."

# Run test environment setup
Write-Host "Setting up test environment..."
.\setup_test.ps1

# Run Docker environment setup
Write-Host "Setting up Docker environment..."
.\setup.ps1

Write-Host "All setup processes completed!"
Write-Host "You can now access your development environment at:"
Write-Host "- MAS Orchestrator: http://localhost:8000"
Write-Host "- Grafana: http://localhost:3000"
Write-Host "- Prometheus: http://localhost:9090"
Write-Host "- AlertManager: http://localhost:9093" 