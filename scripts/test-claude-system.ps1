# Test Claude Code System
# Verifies all components are working

$RepoRoot = Split-Path $PSScriptRoot -Parent

Write-Host "=== Testing Claude Code Autonomous System ===" -ForegroundColor Cyan

# Test 1: Claude CLI
Write-Host "`n[Test 1/5] Claude CLI..." -ForegroundColor Yellow
try {
    $version = claude --version 2>&1
    Write-Host "[OK] Claude CLI: $version" -ForegroundColor Green
} catch {
    Write-Host "[FAIL] Claude CLI not found" -ForegroundColor Red
    exit 1
}

# Test 2: API Key
Write-Host "`n[Test 2/5] API Key..." -ForegroundColor Yellow
if ($env:ANTHROPIC_API_KEY) {
    $keyPrefix = $env:ANTHROPIC_API_KEY.Substring(0, [Math]::Min(10, $env:ANTHROPIC_API_KEY.Length))
    Write-Host "[OK] ANTHROPIC_API_KEY set: $keyPrefix..." -ForegroundColor Green
} else {
    Write-Host "[FAIL] ANTHROPIC_API_KEY not set" -ForegroundColor Red
    exit 1
}

# Test 3: Queue Database
Write-Host "`n[Test 3/5] Queue Database..." -ForegroundColor Yellow
$dbPath = Join-Path $RepoRoot "data\claude_code_queue.db"
if (Test-Path $dbPath) {
    Write-Host "[OK] Queue database exists: $dbPath" -ForegroundColor Green
} else {
    Write-Host "[FAIL] Queue database not found. Run: python scripts/init-claude-queue.py" -ForegroundColor Red
    exit 1
}

# Test 4: API Bridge
Write-Host "`n[Test 4/5] API Bridge..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "http://localhost:8350/health" -TimeoutSec 5
    Write-Host "[OK] API Bridge running. Queue size: $($response.queue_size)" -ForegroundColor Green
} catch {
    Write-Host "[WARN] API Bridge not running. Start with: .\scripts\start-claude-system.ps1" -ForegroundColor Yellow
}

# Test 5: Configuration Sync
Write-Host "`n[Test 5/5] Configuration..." -ForegroundColor Yellow
$cursorAgents = Get-ChildItem "$RepoRoot\.cursor\agents" -File -ErrorAction SilentlyContinue | Measure-Object | Select-Object -ExpandProperty Count
$claudeAgents = Get-ChildItem "$RepoRoot\.claude\agents" -File -ErrorAction SilentlyContinue | Measure-Object | Select-Object -ExpandProperty Count

if ($cursorAgents -gt 0 -and $claudeAgents -gt 0) {
    Write-Host "[OK] Configuration synced. Cursor: $cursorAgents agents, Claude: $claudeAgents agents" -ForegroundColor Green
} else {
    Write-Host "[WARN] Configuration may need sync. Run: .\scripts\sync-claude-config.ps1" -ForegroundColor Yellow
}

Write-Host "`n=== Test Complete ===" -ForegroundColor Magenta
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "1. Start system: .\scripts\start-claude-system.ps1" -ForegroundColor White
Write-Host "2. Queue a test task: python scripts/queue-claude-task.py ""List first 5 lines of README.md""" -ForegroundColor White
Write-Host "3. Check task status: curl http://localhost:8350/tasks/recent" -ForegroundColor White
Write-Host "4. Register with MAS: python scripts/register-local-claude-with-mas.py" -ForegroundColor White
