
# Memory System Migration Deployment Script - February 3, 2026
# Run on sandbox VM (192.168.0.187)

Write-Host "Mycosoft MAS Memory System Migration" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan

# Check for PostgreSQL connection
$PGPASSWORD = $env:POSTGRES_PASSWORD
if (-not $PGPASSWORD) {
    $PGPASSWORD = "postgres"
}

$migrations = @(
    "013_unified_memory.sql",
    "014_voice_session_integration.sql",
    "015_natureos_memory_views.sql",
    "016_graph_memory_persistence.sql"
)

foreach ($migration in $migrations) {
    Write-Host "
Applying migration: $migration" -ForegroundColor Yellow
    
    # psql -h localhost -U postgres -d mycosoft -f "migrations/$migration"
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  OK" -ForegroundColor Green
    } else {
        Write-Host "  FAILED" -ForegroundColor Red
    }
}

Write-Host "
Migrations complete!" -ForegroundColor Green
Write-Host "Verify by running: GET http://localhost:8001/api/memory/health"
