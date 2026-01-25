# Cursor State Database Restore Script
# This restores the "corrupted" 7.75GB database which is actually readable

$ErrorActionPreference = "Stop"

$globalStoragePath = "C:\Users\admin2\AppData\Roaming\Cursor\User\globalStorage"
$corruptedFile = "$globalStoragePath\state.vscdb.corrupted.1769226899189"
$currentFile = "$globalStoragePath\state.vscdb"
$walFile = "$globalStoragePath\state.vscdb-wal"
$shmFile = "$globalStoragePath\state.vscdb-shm"
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"

Write-Host "======================================"
Write-Host "CURSOR STATE DATABASE RESTORE"
Write-Host "======================================"
Write-Host ""

# Check if Cursor is running
$cursorProcess = Get-Process -Name "Cursor" -ErrorAction SilentlyContinue
if ($cursorProcess) {
    Write-Host "WARNING: Cursor is currently running!" -ForegroundColor Yellow
    Write-Host "Please close Cursor completely before running this script."
    Write-Host ""
    Write-Host "Processes found:"
    $cursorProcess | Format-Table Id, ProcessName, StartTime
    
    $response = Read-Host "Do you want to force close Cursor? (yes/no)"
    if ($response -eq "yes") {
        Write-Host "Stopping Cursor processes..."
        Stop-Process -Name "Cursor" -Force
        Start-Sleep -Seconds 3
    } else {
        Write-Host "Please close Cursor manually and run this script again."
        exit 1
    }
}

Write-Host "Step 1: Backing up current state..." -ForegroundColor Cyan
$backupPath = "$currentFile.before_restore_$timestamp"
Copy-Item $currentFile $backupPath -Force
Write-Host "  Backed up to: $backupPath"

if (Test-Path $walFile) {
    Copy-Item $walFile "$walFile.before_restore_$timestamp" -Force
    Write-Host "  Backed up WAL file"
}

Write-Host ""
Write-Host "Step 2: Restoring from corrupted file..." -ForegroundColor Cyan
Write-Host "  Source: $corruptedFile"
Write-Host "  Size: $([math]::Round((Get-Item $corruptedFile).Length / 1GB, 2)) GB"

# Remove current state files
if (Test-Path $shmFile) { Remove-Item $shmFile -Force }
if (Test-Path $walFile) { Remove-Item $walFile -Force }
Remove-Item $currentFile -Force

# Copy the "corrupted" file as the new state
Copy-Item $corruptedFile $currentFile -Force

Write-Host "  RESTORED!" -ForegroundColor Green

Write-Host ""
Write-Host "Step 3: Verification..." -ForegroundColor Cyan
$newSize = [math]::Round((Get-Item $currentFile).Length / 1GB, 2)
Write-Host "  New state.vscdb size: $newSize GB"

Write-Host ""
Write-Host "======================================"
Write-Host "RESTORE COMPLETE!" -ForegroundColor Green
Write-Host "======================================"
Write-Host ""
Write-Host "Please restart Cursor now."
Write-Host "Your chat history and settings should be restored."
Write-Host ""
Write-Host "If issues persist, you can rollback using:"
Write-Host "  Copy-Item '$backupPath' '$currentFile' -Force"
