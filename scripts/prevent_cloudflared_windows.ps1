# Prevent cloudflared from running on Windows
# This should be added to Windows Task Scheduler to run at startup

Write-Host "Checking for cloudflared processes..."

# Kill any running cloudflared processes
$processes = Get-Process -Name "cloudflared" -ErrorAction SilentlyContinue
if ($processes) {
    Write-Host "Stopping cloudflared processes..."
    Stop-Process -Name "cloudflared" -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2
}

# Disable cloudflared service if it exists
$service = Get-Service -Name "cloudflared" -ErrorAction SilentlyContinue
if ($service) {
    Write-Host "Disabling cloudflared service..."
    Stop-Service -Name "cloudflared" -Force -ErrorAction SilentlyContinue
    Set-Service -Name "cloudflared" -StartupType Disabled -ErrorAction SilentlyContinue
    Write-Host "Service disabled successfully"
} else {
    Write-Host "cloudflared service not found (this is OK)"
}

# Also disable via sc.exe (more reliable)
$scResult = sc.exe config cloudflared start= disabled 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "Service disabled via sc.exe"
} else {
    Write-Host "Service may not exist (this is OK)"
}

Write-Host "`nVerification:"
$remaining = Get-Process -Name "cloudflared" -ErrorAction SilentlyContinue
if ($remaining) {
    Write-Host "WARNING: cloudflared is still running!" -ForegroundColor Red
} else {
    Write-Host "SUCCESS: No cloudflared processes running" -ForegroundColor Green
}

$svcStatus = Get-Service -Name "cloudflared" -ErrorAction SilentlyContinue
if ($svcStatus) {
    Write-Host "Service status: $($svcStatus.Status), Startup: $($svcStatus.StartType)"
}
