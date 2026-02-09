# Cursor Recovery Script - Feb 6, 2026
# Restores chats, MCP servers, tools, agent settings after memory overload crash
# RUN THIS ONLY AFTER CLOSING CURSOR COMPLETELY (File > Exit or close all windows)

$ErrorActionPreference = "Stop"
$cursorAppData = "$env:APPDATA\Cursor"
$globalStorage = "$cursorAppData\User\globalStorage"

Write-Host "=== Cursor Recovery Script ===" -ForegroundColor Cyan
Write-Host ""

# Check if Cursor is running
$cursorProc = Get-Process -Name "Cursor" -ErrorAction SilentlyContinue
if ($cursorProc) {
    Write-Host "WARNING: Cursor is still running! Close Cursor (File > Exit), then run again." -ForegroundColor Red
    exit 1
}

Write-Host "Cursor is not running. Proceeding with recovery..." -ForegroundColor Green
Write-Host ""

# 1. Backup current (corrupted) state
$stateFile = "$globalStorage\state.vscdb"
$backupFile = "$globalStorage\state.vscdb.backup"
$restoreFile = "$globalStorage\state.vscdb.corrupted.1770426189579"  # Most recent pre-crash

if (Test-Path $stateFile) {
    $timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $savedCorrupt = "$globalStorage\state.vscdb.corrupted.$timestamp"
    Copy-Item $stateFile $savedCorrupt -Force
    Write-Host "[1] Saved current state to: $savedCorrupt" -ForegroundColor Gray
}

# 2. Restore from backup - prefer .backup (Cursor's auto-backup) or most recent corrupted snapshot
if (Test-Path $backupFile) {
    Copy-Item $backupFile $stateFile -Force
    Write-Host "[2] Restored state from state.vscdb.backup" -ForegroundColor Green
} elseif (Test-Path $restoreFile) {
    Copy-Item $restoreFile $stateFile -Force
    Write-Host "[2] Restored state from most recent pre-crash snapshot" -ForegroundColor Green
} else {
    Write-Host "[2] No backup found - cannot restore state.vscdb" -ForegroundColor Red
}

# 3. Remove stale lock file (can block startup)
$lockFile = "$cursorAppData\code.lock"
if (Test-Path $lockFile) {
    Remove-Item $lockFile -Force
    Write-Host "[3] Removed stale code.lock" -ForegroundColor Green
} else {
    Write-Host "[3] No stale lock file" -ForegroundColor Gray
}

# 4. Clear heavy caches to prevent future memory overload (optional but recommended)
$cachesToClear = @(
    "$cursorAppData\Cache",
    "$cursorAppData\Code Cache",
    "$cursorAppData\CachedData",
    "$cursorAppData\GPUCache"
)
foreach ($cache in $cachesToClear) {
    if (Test-Path $cache) {
        try {
            Remove-Item "$cache\*" -Recurse -Force -ErrorAction SilentlyContinue
            Write-Host "[4] Cleared cache: $(Split-Path $cache -Leaf)" -ForegroundColor Gray
        } catch { /* ignore */ }
    }
}

# 5. Verify MCP config still exists
$mcpConfig = "$env:USERPROFILE\.cursor\mcp.json"
if (Test-Path $mcpConfig) {
    Write-Host "[5] MCP config exists: $mcpConfig" -ForegroundColor Green
    $mcp = Get-Content $mcpConfig -Raw | ConvertFrom-Json
    $servers = ($mcp.mcpServers | Get-Member -MemberType NoteProperty).Name
    Write-Host "    MCP servers configured: $($servers -join ', ')" -ForegroundColor Gray
} else {
    Write-Host "[5] MCP config not found at $mcpConfig" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "=== Recovery complete ===" -ForegroundColor Cyan
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. Start Cursor" -ForegroundColor White
Write-Host "  2. If MCP still shows disconnected: Settings (Ctrl+,) > Tools & Integrations > MCP Servers - toggle or restart servers" -ForegroundColor White
Write-Host "  3. Chats should reappear in the chat panel" -ForegroundColor White
Write-Host ""
Write-Host "To avoid future memory overload: use 'npm run dev:next-only' when you don't need GPU/voice." -ForegroundColor Gray
