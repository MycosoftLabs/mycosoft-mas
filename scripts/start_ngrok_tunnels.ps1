# ============================================================================
# Mycosoft MAS - Ngrok Tunnel Manager
# ============================================================================
# This script exposes your local MAS services to the internet via ngrok
# Share the generated URLs with Claude Desktop, Garret, or anyone else!
# ============================================================================

param(
    [switch]$All,           # Start all tunnels
    [switch]$Website,       # Website only (port 3002)
    [switch]$Dashboard,     # Dashboard (port 3100)
    [switch]$MAS,           # MAS Orchestrator (port 8001)
    [switch]$MycoBrain,     # MycoBrain Service (port 8003)
    [switch]$N8n,           # n8n Workflows (port 5678)
    [switch]$MINDEX,        # MINDEX Search (port 8000)
    [string]$AuthToken,     # Your ngrok auth token
    [switch]$Status,        # Show current tunnel status
    [switch]$Stop           # Stop all tunnels
)

$ErrorActionPreference = "Continue"

# Service configurations
$services = @{
    "website"   = @{ Port = 3002; Name = "MAS Website"; Description = "Main web interface" }
    "dashboard" = @{ Port = 3100; Name = "MYCA Dashboard"; Description = "UniFi-style agent dashboard" }
    "mas"       = @{ Port = 8001; Name = "MAS Orchestrator"; Description = "Core orchestration API" }
    "mycobrain" = @{ Port = 8003; Name = "MycoBrain Service"; Description = "ESP32 device management" }
    "n8n"       = @{ Port = 5678; Name = "n8n Workflows"; Description = "Automation workflows" }
    "mindex"    = @{ Port = 8000; Name = "MINDEX Search"; Description = "Species/taxonomy search" }
}

function Write-Banner {
    Write-Host ""
    Write-Host "================================================================" -ForegroundColor Cyan
    Write-Host "       MYCOSOFT MAS - NGROK TUNNEL MANAGER                     " -ForegroundColor Cyan
    Write-Host "                                                                " -ForegroundColor Cyan
    Write-Host "   Share your local MAS with Claude Desktop & collaborators    " -ForegroundColor Cyan
    Write-Host "================================================================" -ForegroundColor Cyan
    Write-Host ""
}

function Test-NgrokInstalled {
    try {
        $version = ngrok version 2>&1
        return $true
    } catch {
        Write-Host "[X] ngrok is not installed. Install with: winget install ngrok.ngrok" -ForegroundColor Red
        return $false
    }
}

function Test-NgrokAuth {
    $configPath = "$env:USERPROFILE\.ngrok2\ngrok.yml"
    $configPath2 = "$env:USERPROFILE\AppData\Local\ngrok\ngrok.yml"
    
    if (Test-Path $configPath) {
        return $true
    }
    if (Test-Path $configPath2) {
        $content = Get-Content $configPath2 -Raw
        if ($content -match "authtoken") {
            return $true
        }
    }
    return $false
}

function Set-NgrokAuth {
    param([string]$Token)
    
    if ([string]::IsNullOrEmpty($Token)) {
        Write-Host ""
        Write-Host "[!] ngrok requires authentication for tunnels." -ForegroundColor Yellow
        Write-Host ""
        Write-Host "To get your auth token:" -ForegroundColor White
        Write-Host "  1. Sign up at https://ngrok.com (free)" -ForegroundColor Gray
        Write-Host "  2. Go to https://dashboard.ngrok.com/get-started/your-authtoken" -ForegroundColor Gray
        Write-Host "  3. Copy your authtoken" -ForegroundColor Gray
        Write-Host ""
        $Token = Read-Host "Enter your ngrok auth token"
    }
    
    if (-not [string]::IsNullOrEmpty($Token)) {
        ngrok config add-authtoken $Token
        Write-Host "[OK] Auth token configured!" -ForegroundColor Green
        return $true
    }
    return $false
}

function Test-ServiceRunning {
    param([int]$Port)
    
    try {
        $connection = Test-NetConnection -ComputerName localhost -Port $Port -WarningAction SilentlyContinue -InformationLevel Quiet
        return $connection
    } catch {
        return $false
    }
}

function Get-RunningServices {
    $running = @()
    foreach ($key in $services.Keys) {
        $svc = $services[$key]
        if (Test-ServiceRunning -Port $svc.Port) {
            $running += @{
                Key = $key
                Port = $svc.Port
                Name = $svc.Name
                Description = $svc.Description
            }
        }
    }
    return $running
}

function Show-ServiceStatus {
    Write-Host "Service Status:" -ForegroundColor Cyan
    Write-Host ""
    
    foreach ($key in $services.Keys | Sort-Object) {
        $svc = $services[$key]
        $isRunning = Test-ServiceRunning -Port $svc.Port
        $status = if ($isRunning) { "[OK] Running" } else { "[X] Not Running" }
        $color = if ($isRunning) { "Green" } else { "Red" }
        
        Write-Host ("  {0,-12} Port {1,-5} {2,-15} - {3}" -f $svc.Name, $svc.Port, $status, $svc.Description) -ForegroundColor $color
    }
    Write-Host ""
}

function Start-AllTunnels {
    param([array]$ServicesToStart)
    
    if ($ServicesToStart.Count -eq 0) {
        Write-Host "[X] No services are currently running!" -ForegroundColor Red
        Write-Host "   Start your MAS services first, then run this script again." -ForegroundColor Yellow
        return
    }
    
    Write-Host ""
    Write-Host "Starting ngrok tunnels for $($ServicesToStart.Count) service(s)..." -ForegroundColor Cyan
    Write-Host ""
    
    # For multiple tunnels, we need ngrok config file
    $configContent = @"
version: "2"
tunnels:
"@
    
    foreach ($svc in $ServicesToStart) {
        $configContent += @"

  $($svc.Key):
    addr: $($svc.Port)
    proto: http
"@
    }
    
    $configPath = "$env:TEMP\ngrok_mas_tunnels.yml"
    $configContent | Out-File -FilePath $configPath -Encoding UTF8
    
    # Start ngrok with all tunnels
    Write-Host "Launching ngrok with multi-tunnel configuration..." -ForegroundColor Yellow
    Start-Process -FilePath "ngrok" -ArgumentList "start", "--all", "--config", $configPath -WindowStyle Normal
    
    # Wait for tunnels to establish
    Write-Host "Waiting for tunnels to establish..." -ForegroundColor Gray
    Start-Sleep -Seconds 5
    
    # Get tunnel URLs
    Write-Host ""
    Write-Host "================================================================" -ForegroundColor Cyan
    Write-Host "                    TUNNELS ARE LIVE!                           " -ForegroundColor Green
    Write-Host "================================================================" -ForegroundColor Cyan
    Write-Host ""
    
    try {
        $tunnels = Invoke-RestMethod -Uri "http://localhost:4040/api/tunnels" -ErrorAction Stop
        
        foreach ($tunnel in $tunnels.tunnels) {
            $port = $tunnel.config.addr -replace '.*:', ''
            $svc = $ServicesToStart | Where-Object { $_.Port -eq [int]$port } | Select-Object -First 1
            
            if ($svc) {
                Write-Host "  $($svc.Name)" -ForegroundColor White
                Write-Host "     Local:  http://localhost:$($svc.Port)" -ForegroundColor Gray
                Write-Host "     Public: $($tunnel.public_url)" -ForegroundColor Cyan
                Write-Host ""
            }
        }
        
        Write-Host "================================================================" -ForegroundColor Cyan
        Write-Host ""
        Write-Host "Share these URLs with Claude Desktop, Garret, or anyone!" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "ngrok Dashboard: http://localhost:4040" -ForegroundColor Magenta
        Write-Host ""
        Write-Host "[!] Note: Free ngrok URLs change each time you restart." -ForegroundColor Gray
        Write-Host "   For permanent URLs, upgrade to ngrok Pro." -ForegroundColor Gray
        Write-Host ""
        
    } catch {
        Write-Host "[!] Tunnels started but could not retrieve URLs." -ForegroundColor Yellow
        Write-Host "   Open http://localhost:4040 to see your tunnel URLs." -ForegroundColor Yellow
    }
}

function Stop-AllTunnels {
    Write-Host "Stopping all ngrok tunnels..." -ForegroundColor Yellow
    Get-Process -Name "ngrok" -ErrorAction SilentlyContinue | Stop-Process -Force
    Write-Host "[OK] All tunnels stopped." -ForegroundColor Green
}

function Show-TunnelStatus {
    Write-Host ""
    Write-Host "Current Tunnel Status:" -ForegroundColor Cyan
    Write-Host ""
    
    try {
        $tunnels = Invoke-RestMethod -Uri "http://localhost:4040/api/tunnels" -ErrorAction Stop
        
        if ($tunnels.tunnels.Count -eq 0) {
            Write-Host "  No active tunnels." -ForegroundColor Gray
        } else {
            foreach ($tunnel in $tunnels.tunnels) {
                $port = $tunnel.config.addr -replace '.*:', ''
                Write-Host "  [OK] Port $port -> $($tunnel.public_url)" -ForegroundColor Green
            }
        }
    } catch {
        Write-Host "  No ngrok instance running." -ForegroundColor Gray
    }
    Write-Host ""
}

# ============================================================================
# Main Execution
# ============================================================================

Write-Banner

if (-not (Test-NgrokInstalled)) {
    exit 1
}

# Handle stop command
if ($Stop) {
    Stop-AllTunnels
    exit 0
}

# Handle status command
if ($Status) {
    Show-ServiceStatus
    Show-TunnelStatus
    exit 0
}

# Check auth
if (-not (Test-NgrokAuth)) {
    if (-not (Set-NgrokAuth -Token $AuthToken)) {
        Write-Host "[X] ngrok authentication required. Please provide an auth token." -ForegroundColor Red
        exit 1
    }
}

# Show current service status
Show-ServiceStatus

# Determine which services to tunnel
$servicesToStart = @()

if ($All) {
    $servicesToStart = Get-RunningServices
} else {
    if ($Website)   { if (Test-ServiceRunning -Port 3002) { $servicesToStart += @{ Key="website"; Port=3002; Name="MAS Website"; Description="Main web interface" } } }
    if ($Dashboard) { if (Test-ServiceRunning -Port 3100) { $servicesToStart += @{ Key="dashboard"; Port=3100; Name="MYCA Dashboard"; Description="UniFi-style agent dashboard" } } }
    if ($MAS)       { if (Test-ServiceRunning -Port 8001) { $servicesToStart += @{ Key="mas"; Port=8001; Name="MAS Orchestrator"; Description="Core orchestration API" } } }
    if ($MycoBrain) { if (Test-ServiceRunning -Port 8003) { $servicesToStart += @{ Key="mycobrain"; Port=8003; Name="MycoBrain Service"; Description="ESP32 device management" } } }
    if ($N8n)       { if (Test-ServiceRunning -Port 5678) { $servicesToStart += @{ Key="n8n"; Port=5678; Name="n8n Workflows"; Description="Automation workflows" } } }
    if ($MINDEX)    { if (Test-ServiceRunning -Port 8000) { $servicesToStart += @{ Key="mindex"; Port=8000; Name="MINDEX Search"; Description="Species/taxonomy search" } } }
    
    # If no specific service selected, default to all running services
    if ($servicesToStart.Count -eq 0 -and -not ($Website -or $Dashboard -or $MAS -or $MycoBrain -or $N8n -or $MINDEX)) {
        $servicesToStart = Get-RunningServices
    }
}

Start-AllTunnels -ServicesToStart $servicesToStart

Write-Host "Press Ctrl+C in the ngrok window to stop tunnels." -ForegroundColor Gray
Write-Host ""
