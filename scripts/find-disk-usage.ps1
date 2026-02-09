# Find what's using disk space - Feb 6, 2026
# Run in normal PowerShell (not as Administrator) to avoid sandbox errors.
# Usage: .\find-disk-usage.ps1
# Optional: .\find-disk-usage.ps1 -Quick   (skip slow full recurses for Cursor/Docker)

param([switch]$Quick)

$ErrorActionPreference = 'SilentlyContinue'

function Get-FolderSizeGB {
    param([string]$Path, [int]$MaxDepth = -1)
    if (-not (Test-Path -LiteralPath $Path -PathType Container)) { return $null }
    $sum = 0
    try {
        $files = Get-ChildItem -LiteralPath $Path -File -Recurse -ErrorAction SilentlyContinue
        foreach ($f in $files) {
            if ($MaxDepth -ge 0) {
                $rel = $f.FullName.Substring($Path.Length)
                $d = ($rel -split [IO.Path]::DirectorySeparatorChar).Count - 1
                if ($d -gt $MaxDepth) { continue }
            }
            $sum += $f.Length
        }
    } catch { return $null }
    return [math]::Round($sum / 1GB, 2)
}

# One-level only (fast): only immediate files and immediate dir names, no recurse
function Get-FolderSizeOneLevelGB {
    param([string]$Path)
    if (-not (Test-Path -LiteralPath $Path -PathType Container)) { return $null }
    $sum = 0
    try {
        Get-ChildItem -LiteralPath $Path -File -ErrorAction SilentlyContinue | ForEach-Object { $sum += $_.Length }
    } catch { return $null }
    return [math]::Round($sum / 1GB, 2)
}

function Get-FileSizeGB {
    param([string]$Path)
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { return $null }
    return [math]::Round((Get-Item -LiteralPath $Path).Length / 1GB, 2)
}

# Paths that often consume a lot of space
$workspaceRoot = "C:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas"
$cursorRoaming = "$env:APPDATA\Cursor"
$cursorLocal   = "$env:LOCALAPPDATA\Cursor"
$dockerLocal   = "$env:LOCALAPPDATA\Docker"
$wslPath       = "$env:LOCALAPPDATA\Packages"
# WSL vhdx paths (often hundreds of GB; does not auto-shrink)
$wslVhdxChecks = @(
    "$env:LOCALAPPDATA\Docker\wsl\data\ext4.vhdx",
    "$env:LOCALAPPDATA\Packages\CanonicalGroupLimited.Ubuntu22.04LTS\LocalState\ext4.vhdx",
    "$env:LOCALAPPDATA\Packages\CanonicalGroupLimited.Ubuntu\LocalState\ext4.vhdx"
)
# Also any ext4.vhdx under Packages
$wslVhdxExtra = Get-ChildItem -Path "$wslPath" -Filter "ext4.vhdx" -Recurse -ErrorAction SilentlyContinue -Depth 4 | Select-Object -First 3

Write-Host "`n=== Disk usage report (Feb 6, 2026) ===" -ForegroundColor Cyan
Write-Host "Run without -Quick for full Cursor/Docker folder sizes (slower).`n" -ForegroundColor Gray

# 1. Drive space
Write-Host "--- Drives ---" -ForegroundColor Yellow
Get-PSDrive -PSProvider FileSystem | Where-Object { $_.Used -ne $null } | ForEach-Object {
    $usedGB = [math]::Round($_.Used / 1GB, 2)
    $freeGB = [math]::Round($_.Free / 1GB, 2)
    $totalGB = [math]::Round(($_.Used + $_.Free) / 1GB, 2)
    $pct = if ($totalGB -gt 0) { [math]::Round(100 * $_.Used / ($_.Used + $_.Free), 1) } else { 0 }
    Write-Host ("  {0}:  Used {1} GB  Free {2} GB  Total {3} GB  ({4}% used)" -f $_.Root, $usedGB, $freeGB, $totalGB, $pct)
}

# 2. Workspace: first-level folder sizes (fast)
Write-Host "`n--- Workspace (first-level folders): $workspaceRoot ---" -ForegroundColor Yellow
if (Test-Path -LiteralPath $workspaceRoot -PathType Container) {
    Get-ChildItem -LiteralPath $workspaceRoot -Directory -ErrorAction SilentlyContinue | ForEach-Object {
        $gb = Get-FolderSizeGB -Path $_.FullName -MaxDepth 2
        if ($null -ne $gb) {
            $name = $_.Name
            if ($gb -gt 0.01) { Write-Host ("  {0,8} GB  {1}" -f $gb, $name) }
        }
    }
    # Also try total workspace size if not -Quick (can be slow)
    if (-not $Quick) {
        Write-Host "  (computing total workspace size - may take a few minutes...)" -ForegroundColor Gray
        $totalWorkspace = Get-FolderSizeGB -Path $workspaceRoot
        if ($null -ne $totalWorkspace) { Write-Host ("  TOTAL workspace: {0} GB" -f $totalWorkspace) -ForegroundColor Cyan }
    }
} else {
    Write-Host "  Workspace path not found." -ForegroundColor Red
}

# 3. Cursor AppData (Roaming) - chat history lives under User\workspaceStorage
Write-Host "`n--- Cursor (chat history & cache) ---" -ForegroundColor Yellow
Write-Host "  Roaming (chat/data): $cursorRoaming" -ForegroundColor Gray
if (Test-Path -LiteralPath $cursorRoaming -PathType Container) {
    if ($Quick) {
        $cursorRoamingSize = Get-FolderSizeOneLevelGB -Path $cursorRoaming
        if ($null -ne $cursorRoamingSize) { Write-Host ("  ~{0} GB (root only; run without -Quick for full size)" -f $cursorRoamingSize) }
    } else {
        $cursorRoamingSize = Get-FolderSizeGB -Path $cursorRoaming
        if ($null -ne $cursorRoamingSize) { Write-Host ("  {0} GB" -f $cursorRoamingSize) -ForegroundColor Cyan }
    }
    $wsStorage = Join-Path $cursorRoaming "User\workspaceStorage"
    if (Test-Path -LiteralPath $wsStorage -PathType Container) {
        Write-Host "  workspaceStorage (chats): $wsStorage" -ForegroundColor Gray
    }
} else {
    Write-Host "  Not found." -ForegroundColor Gray
}
Write-Host "  Local (cache): $cursorLocal" -ForegroundColor Gray
if (Test-Path -LiteralPath $cursorLocal -PathType Container) {
    if ($Quick) {
        $cursorLocalSize = Get-FolderSizeOneLevelGB -Path $cursorLocal
        if ($null -ne $cursorLocalSize) { Write-Host ("  ~{0} GB (root only; run without -Quick for full size)" -f $cursorLocalSize) }
    } else {
        $cursorLocalSize = Get-FolderSizeGB -Path $cursorLocal
        if ($null -ne $cursorLocalSize) { Write-Host ("  {0} GB" -f $cursorLocalSize) -ForegroundColor Cyan }
    }
} else {
    Write-Host "  Not found." -ForegroundColor Gray
}

# 4. WSL vhdx (often hundreds of GB and does not auto-shrink)
Write-Host "`n--- WSL2 virtual disk (ext4.vhdx) ---" -ForegroundColor Yellow
foreach ($p in $wslVhdxChecks) {
    if (Test-Path -LiteralPath $p -PathType Leaf) {
        $gb = Get-FileSizeGB -Path $p
        if ($null -ne $gb) { Write-Host ("  {0} GB  {1}" -f $gb, $p) -ForegroundColor Cyan }
    }
}
foreach ($f in $wslVhdxExtra) {
    $gb = Get-FileSizeGB -Path $f.FullName
    if ($null -ne $gb) { Write-Host ("  {0} GB  {1}" -f $gb, $f.FullName) -ForegroundColor Cyan }
}

# 5. Docker Desktop
Write-Host "`n--- Docker Desktop ---" -ForegroundColor Yellow
Write-Host "  $dockerLocal" -ForegroundColor Gray
if (Test-Path -LiteralPath $dockerLocal -PathType Container) {
    if ($Quick) {
        $dockerSize = Get-FolderSizeOneLevelGB -Path $dockerLocal
        if ($null -ne $dockerSize) { Write-Host ("  ~{0} GB (root only; run without -Quick for full size)" -f $dockerSize) }
    } else {
        $dockerSize = Get-FolderSizeGB -Path $dockerLocal
        if ($null -ne $dockerSize) { Write-Host ("  {0} GB" -f $dockerSize) -ForegroundColor Cyan }
    }
} else {
    Write-Host "  Not found." -ForegroundColor Gray
}

Write-Host "`n--- Next steps ---" -ForegroundColor Green
Write-Host "  1. See docs\DATA_LOSS_AND_DRIVE_FULL_RECOVERY_FEB06_2026.md for chat recovery and cleanup."
Write-Host "  2. To free space: WSL -> wsl --shutdown then compact vhdx; Docker -> docker system prune -a --volumes."
Write-Host "  3. Back up Cursor chat: copy %APPDATA%\Cursor\User\workspaceStorage to a safe location.`n"
