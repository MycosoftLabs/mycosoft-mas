# Quick Test Script for Document Knowledge Base
# PowerShell script to quickly verify everything is working

$ErrorActionPreference = "Continue"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "MYCOSOFT MAS - QUICK DOCUMENT KNOWLEDGE BASE TEST" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# Test 1: Check if Python script exists
Write-Host "Test 1: Checking test script..." -ForegroundColor Yellow
if (Test-Path "scripts\test_document_knowledge_base.py") {
    Write-Host "[OK] Test script found" -ForegroundColor Green
} else {
    Write-Host "[FAIL] Test script not found" -ForegroundColor Red
    exit 1
}

# Test 2: Check if services are running
Write-Host ""
Write-Host "Test 2: Checking services..." -ForegroundColor Yellow

# Check Qdrant
try {
    $response = Invoke-WebRequest -Uri "http://localhost:6333/health" -TimeoutSec 2 -ErrorAction Stop
    Write-Host "[OK] Qdrant is running" -ForegroundColor Green
} catch {
    Write-Host "[WARN] Qdrant not accessible (may still work)" -ForegroundColor Yellow
    Write-Host "       Start with: docker compose up -d qdrant" -ForegroundColor Gray
}

# Check Redis
try {
    $response = Invoke-WebRequest -Uri "http://localhost:6379" -TimeoutSec 2 -ErrorAction Stop
    Write-Host "[OK] Redis is running" -ForegroundColor Green
} catch {
    Write-Host "[WARN] Redis not accessible (may still work)" -ForegroundColor Yellow
    Write-Host "       Start with: docker compose up -d redis" -ForegroundColor Gray
}

# Check API
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -TimeoutSec 2 -ErrorAction Stop
    Write-Host "[OK] API server is running" -ForegroundColor Green
} catch {
    Write-Host "[WARN] API server not running" -ForegroundColor Yellow
    Write-Host "       Start with: uvicorn mycosoft_mas.core.myca_main:app --reload" -ForegroundColor Gray
}

# Test 3: Run Python test
Write-Host ""
Write-Host "Test 3: Running comprehensive tests..." -ForegroundColor Yellow
Write-Host ""

python scripts/test_document_knowledge_base.py

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "============================================================" -ForegroundColor Green
    Write-Host "ALL TESTS PASSED!" -ForegroundColor Green
    Write-Host "============================================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Document knowledge base is working correctly." -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Yellow
    Write-Host "  1. Test in Cursor: Ask about your documentation" -ForegroundColor White
    Write-Host "  2. Test with MYCA: Query the knowledge base" -ForegroundColor White
    Write-Host "  3. Create a new .md file and verify auto-indexing" -ForegroundColor White
} else {
    Write-Host ""
    Write-Host "============================================================" -ForegroundColor Red
    Write-Host "SOME TESTS FAILED" -ForegroundColor Red
    Write-Host "============================================================" -ForegroundColor Red
    Write-Host ""
    Write-Host "Check the output above for details." -ForegroundColor Yellow
    Write-Host "Common issues:" -ForegroundColor Yellow
    Write-Host "  - Qdrant not running: docker compose up -d qdrant" -ForegroundColor White
    Write-Host "  - Redis not running: docker compose up -d redis" -ForegroundColor White
    Write-Host "  - Documents not indexed: python scripts/index_documents.py" -ForegroundColor White
}


