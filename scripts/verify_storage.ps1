# Verify NAS Storage Configuration
# This script checks that the NAS is properly configured and accessible

param(
    [string]$DriveLetter = "M",
    [string]$NASAddress = "192.168.0.1"
)

$ErrorActionPreference = "Continue"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  MYCA Storage Verification" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$errors = @()
$warnings = @()

# Check 1: Network connectivity
Write-Host "[1/6] Checking network connectivity..." -ForegroundColor Cyan
$ping = Test-NetConnection -ComputerName $NASAddress -WarningAction SilentlyContinue
if ($ping.PingSucceeded) {
    Write-Host "  [OK] NAS is reachable at $NASAddress" -ForegroundColor Green
} else {
    Write-Host "  [FAIL] Cannot reach NAS at $NASAddress" -ForegroundColor Red
    $errors += "NAS not reachable"
}

# Check 2: SMB port
Write-Host "[2/6] Checking SMB port (445)..." -ForegroundColor Cyan
$smb = Test-NetConnection -ComputerName $NASAddress -Port 445 -WarningAction SilentlyContinue
if ($smb.TcpTestSucceeded) {
    Write-Host "  [OK] SMB port is open" -ForegroundColor Green
} else {
    Write-Host "  [FAIL] SMB port is closed" -ForegroundColor Red
    $errors += "SMB port not accessible"
}

# Check 3: Drive mount
Write-Host "[3/6] Checking drive mount..." -ForegroundColor Cyan
$drive = Get-PSDrive -Name $DriveLetter -ErrorAction SilentlyContinue
if ($drive) {
    $freeSpace = [math]::Round($drive.Free / 1TB, 2)
    Write-Host "  [OK] Drive ${DriveLetter}: is mounted (${freeSpace} TB free)" -ForegroundColor Green
} else {
    Write-Host "  [FAIL] Drive ${DriveLetter}: is not mounted" -ForegroundColor Red
    $errors += "Drive not mounted"
}

# Check 4: Directory structure
Write-Host "[4/6] Checking directory structure..." -ForegroundColor Cyan
$requiredDirs = @(
    "databases",
    "knowledge",
    "agents",
    "website",
    "backups",
    "audit",
    "dev",
    "shared"
)

$missingDirs = @()
foreach ($dir in $requiredDirs) {
    $path = "${DriveLetter}:\$dir"
    if (Test-Path $path) {
        Write-Host "  [OK] $dir/" -ForegroundColor Green
    } else {
        Write-Host "  [MISSING] $dir/" -ForegroundColor Yellow
        $missingDirs += $dir
    }
}

if ($missingDirs.Count -gt 0) {
    $warnings += "Missing directories: $($missingDirs -join ', ')"
}

# Check 5: Write access
Write-Host "[5/6] Checking write access..." -ForegroundColor Cyan
$testFile = "${DriveLetter}:\test_write_access_$(Get-Date -Format 'yyyyMMddHHmmss').tmp"
try {
    "test" | Out-File -FilePath $testFile -Force
    Remove-Item $testFile -Force
    Write-Host "  [OK] Write access confirmed" -ForegroundColor Green
} catch {
    Write-Host "  [FAIL] No write access" -ForegroundColor Red
    $errors += "No write access to NAS"
}

# Check 6: Environment variable
Write-Host "[6/6] Checking environment variable..." -ForegroundColor Cyan
$nasPath = $env:NAS_STORAGE_PATH
if ($nasPath) {
    Write-Host "  [OK] NAS_STORAGE_PATH = $nasPath" -ForegroundColor Green
} else {
    Write-Host "  [WARN] NAS_STORAGE_PATH not set" -ForegroundColor Yellow
    $warnings += "NAS_STORAGE_PATH environment variable not set"
}

# Summary
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Verification Summary" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

if ($errors.Count -eq 0 -and $warnings.Count -eq 0) {
    Write-Host ""
    Write-Host "All checks passed!" -ForegroundColor Green
    Write-Host "NAS storage is ready for use." -ForegroundColor White
    exit 0
} else {
    if ($errors.Count -gt 0) {
        Write-Host ""
        Write-Host "ERRORS ($($errors.Count)):" -ForegroundColor Red
        foreach ($err in $errors) {
            Write-Host "  - $err" -ForegroundColor Red
        }
    }
    
    if ($warnings.Count -gt 0) {
        Write-Host ""
        Write-Host "WARNINGS ($($warnings.Count)):" -ForegroundColor Yellow
        foreach ($warn in $warnings) {
            Write-Host "  - $warn" -ForegroundColor Yellow
        }
    }
    
    if ($errors.Count -gt 0) {
        Write-Host ""
        Write-Host "Please fix the errors before proceeding." -ForegroundColor Red
        exit 1
    } else {
        Write-Host ""
        Write-Host "Storage is usable but has warnings." -ForegroundColor Yellow
        exit 0
    }
}
