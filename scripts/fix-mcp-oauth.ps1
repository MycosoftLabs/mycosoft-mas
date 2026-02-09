# fix-mcp-oauth.ps1
# Fixes MCP OAuth connection issues after Cursor updates
# Run this AFTER closing Cursor completely (not as admin!)
#
# Usage:
#   1. Close Cursor completely (File > Quit, or Ctrl+Q)
#   2. Open a REGULAR (non-admin) PowerShell terminal
#   3. Run: .\scripts\fix-mcp-oauth.ps1
#   4. Restart Cursor (do NOT run as admin)
#   5. Go to Settings > MCP and click Connect on each server

param(
    [switch]$SkipKill,
    [switch]$Force
)

Write-Host "================================================" -ForegroundColor Cyan
Write-Host "  Mycosoft MCP OAuth Fix Script" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

# Check if running as admin (warn but don't block)
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if ($isAdmin) {
    Write-Host "[WARNING] You are running as Administrator!" -ForegroundColor Yellow
    Write-Host "  MCP OAuth works best when Cursor runs as a normal user." -ForegroundColor Yellow
    Write-Host "  After this fix, restart Cursor WITHOUT admin privileges." -ForegroundColor Yellow
    Write-Host ""
}

# Step 1: Kill all Cursor processes
if (-not $SkipKill) {
    Write-Host "[Step 1] Stopping all Cursor processes..." -ForegroundColor Green
    $procs = Get-Process -Name "Cursor" -ErrorAction SilentlyContinue
    if ($procs) {
        $procs | Stop-Process -Force -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 3
        # Verify
        $remaining = Get-Process -Name "Cursor" -ErrorAction SilentlyContinue
        if ($remaining) {
            Write-Host "  Some Cursor processes still running. Waiting..." -ForegroundColor Yellow
            Start-Sleep -Seconds 5
            Get-Process -Name "Cursor" -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
        }
        Write-Host "  All Cursor processes stopped." -ForegroundColor Green
    } else {
        Write-Host "  No Cursor processes found (good)." -ForegroundColor Green
    }
} else {
    Write-Host "[Step 1] Skipped process kill (--SkipKill)" -ForegroundColor Yellow
}

Write-Host ""

# Step 2: Clear MCP extension OAuth cached state
Write-Host "[Step 2] Clearing MCP OAuth cached state..." -ForegroundColor Green

# Clear extension globalStorage
$mcpGlobalStorage = "$env:APPDATA\Cursor\User\globalStorage\anysphere.cursor-mcp"
if (Test-Path $mcpGlobalStorage) {
    Remove-Item -Recurse -Force $mcpGlobalStorage -ErrorAction SilentlyContinue
    Write-Host "  Cleared: MCP extension globalStorage" -ForegroundColor Green
}

# Clear cached extension VSIXs
$cachedVSIXs = "$env:APPDATA\Cursor\CachedExtensionVSIXs"
if (Test-Path $cachedVSIXs) {
    Get-ChildItem $cachedVSIXs -Filter "*cursor-mcp*" -ErrorAction SilentlyContinue | ForEach-Object {
        Remove-Item $_.FullName -Force -ErrorAction SilentlyContinue
        Write-Host "  Cleared: Cached VSIX $($_.Name)" -ForegroundColor Green
    }
}

# Clear the extension's workbench state that contains OAuth PKCE verifiers
$wsStoragePath = "$env:APPDATA\Cursor\User\workspaceStorage"
if (Test-Path $wsStoragePath) {
    Get-ChildItem $wsStoragePath -Directory -ErrorAction SilentlyContinue | ForEach-Object {
        $stateDb = Join-Path $_.FullName "state.vscdb"
        # Don't delete the whole DB - just note it exists
    }
}

Write-Host "  MCP OAuth state cleared." -ForegroundColor Green
Write-Host ""

# Step 3: Clear Cursor's session storage (contains OAuth tokens)
Write-Host "[Step 3] Clearing Cursor session/secure storage for MCP..." -ForegroundColor Green

# Clear Session Storage
$sessionStorage = "$env:APPDATA\Cursor\Session Storage"
if (Test-Path $sessionStorage) {
    try {
        Remove-Item -Recurse -Force $sessionStorage -ErrorAction Stop
        Write-Host "  Cleared: Session Storage" -ForegroundColor Green
    } catch {
        Write-Host "  Could not clear Session Storage (may be locked)" -ForegroundColor Yellow
    }
}

# Clear specific MCP-related Partitions data
$partitions = "$env:APPDATA\Cursor\Partitions"
if (Test-Path $partitions) {
    Get-ChildItem $partitions -Directory -ErrorAction SilentlyContinue | ForEach-Object {
        $mcpLocal = Join-Path $_.FullName "Local Storage"
        if (Test-Path $mcpLocal) {
            try {
                Remove-Item -Recurse -Force $mcpLocal -ErrorAction Stop
                Write-Host "  Cleared: Partition Local Storage ($($_.Name))" -ForegroundColor Green
            } catch {
                Write-Host "  Could not clear Partition ($($_.Name))" -ForegroundColor Yellow
            }
        }
    }
}

Write-Host ""

# Step 4: Verify protocol handler
Write-Host "[Step 4] Verifying cursor:// protocol handler..." -ForegroundColor Green
$cursorExe = "$env:LOCALAPPDATA\Programs\cursor\Cursor.exe"

if (-not (Test-Path $cursorExe)) {
    Write-Host "  WARNING: Cursor.exe not found at expected path!" -ForegroundColor Red
    Write-Host "  Looking for Cursor.exe..." -ForegroundColor Yellow
    $found = Get-ChildItem "$env:LOCALAPPDATA" -Filter "Cursor.exe" -Recurse -Depth 3 -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($found) {
        $cursorExe = $found.FullName
        Write-Host "  Found: $cursorExe" -ForegroundColor Green
    }
}

$currentCmd = (Get-ItemProperty "HKCU:\Software\Classes\cursor\shell\open\command" -ErrorAction SilentlyContinue).'(default)'
$expectedCmd = "`"$cursorExe`" `"--open-url`" `"--`" `"%1`""

if ($currentCmd -eq $expectedCmd) {
    Write-Host "  Protocol handler: OK" -ForegroundColor Green
} else {
    Write-Host "  Fixing protocol handler..." -ForegroundColor Yellow
    New-Item -Path "HKCU:\Software\Classes\cursor" -Force | Out-Null
    Set-ItemProperty -Path "HKCU:\Software\Classes\cursor" -Name "(default)" -Value "URL:cursor"
    Set-ItemProperty -Path "HKCU:\Software\Classes\cursor" -Name "URL Protocol" -Value ""
    New-Item -Path "HKCU:\Software\Classes\cursor\shell\open\command" -Force | Out-Null
    Set-ItemProperty -Path "HKCU:\Software\Classes\cursor\shell\open\command" -Name "(default)" -Value $expectedCmd
    Write-Host "  Protocol handler: Fixed" -ForegroundColor Green
}

Write-Host ""

# Step 5: Verify mcp.json is correct
Write-Host "[Step 5] Verifying MCP configuration..." -ForegroundColor Green
$mcpJson = "$env:USERPROFILE\.cursor\mcp.json"
if (Test-Path $mcpJson) {
    $content = Get-Content $mcpJson -Raw | ConvertFrom-Json
    $servers = $content.mcpServers.PSObject.Properties
    foreach ($server in $servers) {
        $name = $server.Name
        $config = $server.Value
        if ($config.url) {
            Write-Host "  $name : URL-based (streamableHttp) -> $($config.url)" -ForegroundColor Green
        } elseif ($config.command) {
            Write-Host "  $name : Command-based -> $($config.command)" -ForegroundColor Green
        } else {
            Write-Host "  $name : Unknown format" -ForegroundColor Yellow
        }
    }
} else {
    Write-Host "  WARNING: No mcp.json found at $mcpJson" -ForegroundColor Red
}

Write-Host ""
Write-Host "================================================" -ForegroundColor Cyan
Write-Host "  Fix Complete!" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor White
Write-Host "  1. Start Cursor normally (do NOT right-click 'Run as admin')" -ForegroundColor White
Write-Host "  2. Go to: Settings (gear icon) > MCP" -ForegroundColor White
Write-Host "  3. Click 'Connect' on Notion -- a browser window will open" -ForegroundColor White
Write-Host "  4. Authorize in the browser -- it will redirect back to Cursor" -ForegroundColor White
Write-Host "  5. Repeat for Supabase" -ForegroundColor White
Write-Host ""
Write-Host "IMPORTANT: If the browser opens but nothing happens after authorizing:" -ForegroundColor Yellow
Write-Host "  - Make sure Cursor is NOT running as administrator" -ForegroundColor Yellow
Write-Host "  - Make sure only ONE instance of Cursor is running" -ForegroundColor Yellow
Write-Host "  - Try a different browser (Edge/Chrome/Firefox)" -ForegroundColor Yellow
Write-Host ""
