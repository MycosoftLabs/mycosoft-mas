# Final Integration Test
Write-Host "`n=== MYCA MAS + Speech Integration Test ===" -ForegroundColor Cyan

# Test MAS API
Write-Host "`n1. Testing MAS API..." -ForegroundColor Yellow
try {
    $health = Invoke-RestMethod -Uri "http://localhost:8001/health" -TimeoutSec 5
    Write-Host "   MAS Health: PASS" -ForegroundColor Green
} catch {
    Write-Host "   MAS Health: FAIL" -ForegroundColor Red
}

# Test Speech Gateway
Write-Host "`n2. Testing Speech Gateway..." -ForegroundColor Yellow
try {
    $sg = Invoke-RestMethod -Uri "http://localhost:8002/health" -TimeoutSec 5
    Write-Host "   Speech Gateway: PASS" -ForegroundColor Green
} catch {
    Write-Host "   Speech Gateway: FAIL" -ForegroundColor Red
}

# Test n8n
Write-Host "`n3. Testing n8n..." -ForegroundColor Yellow
try {
    $n8n = Invoke-WebRequest -Uri "http://localhost:5678/" -UseBasicParsing -TimeoutSec 5
    Write-Host "   n8n: PASS" -ForegroundColor Green
} catch {
    Write-Host "   n8n: FAIL" -ForegroundColor Red
}

# Test Voice UI
Write-Host "`n4. Testing Voice UI..." -ForegroundColor Yellow
try {
    $ui = Invoke-WebRequest -Uri "http://localhost:8090/" -UseBasicParsing -TimeoutSec 5
    Write-Host "   Voice UI: PASS" -ForegroundColor Green
} catch {
    Write-Host "   Voice UI: FAIL" -ForegroundColor Red
}

# Container Status
Write-Host "`n5. Container Status:" -ForegroundColor Yellow
docker ps --filter "name=mas-orchestrator" --format "   {{.Names}}: {{.Status}}" | ForEach-Object { Write-Host $_ -ForegroundColor Green }
docker ps --filter "name=speech-gateway" --format "   {{.Names}}: {{.Status}}" | ForEach-Object { Write-Host $_ -ForegroundColor Green }
docker ps --filter "name=n8n" --format "   {{.Names}}: {{.Status}}" | ForEach-Object { Write-Host $_ -ForegroundColor Green }

Write-Host "`n=== Test Complete ===" -ForegroundColor Cyan
Write-Host "`nEndpoints:" -ForegroundColor White
Write-Host "  MAS API: http://localhost:8001" -ForegroundColor Gray
Write-Host "  Speech Gateway: http://localhost:8002" -ForegroundColor Gray
Write-Host "  n8n: http://localhost:5678" -ForegroundColor Gray
Write-Host "  Voice UI: http://localhost:8090" -ForegroundColor Gray
