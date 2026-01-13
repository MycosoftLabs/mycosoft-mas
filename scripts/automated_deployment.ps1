# MYCA Automated Production Deployment
# This script automates as much as possible and prompts for manual steps

param(
    [switch]$SkipProxmox,
    [switch]$SkipUniFi,
    [switch]$SkipDomain,
    [switch]$Interactive
)

$ErrorActionPreference = "Continue"

Write-Host @"
==============================================================================
                    MYCA AUTOMATED PRODUCTION DEPLOYMENT
==============================================================================

This script will:
1. Configure Proxmox VMs for production
2. Enable UniFi NAS storage (SMB)
3. Set up domain DNS (GoDaddy -> Cloudflare)
4. Deploy all services
5. Verify go-live readiness

"@ -ForegroundColor Cyan

# ============================================================================
# STEP 1: PROXMOX CONFIGURATION
# ============================================================================

if (-not $SkipProxmox) {
    Write-Host "STEP 1: PROXMOX VM CREATION" -ForegroundColor Yellow
    Write-Host "=" * 60
    
    # Check for existing credentials
    if ($env:PROXMOX_TOKEN_ID -and $env:PROXMOX_TOKEN_SECRET) {
        Write-Host "[OK] Proxmox credentials found in environment" -ForegroundColor Green
        
        # Run VM creation
        Write-Host "Creating production VMs..." -ForegroundColor Gray
        python scripts/production/create_all_vms.py --start
        
    } else {
        Write-Host ""
        Write-Host "[ACTION REQUIRED] Proxmox API Token needed" -ForegroundColor Red
        Write-Host ""
        Write-Host "Please create an API token in Proxmox:" -ForegroundColor White
        Write-Host "  1. Open: https://192.168.0.202:8006" -ForegroundColor Gray
        Write-Host "  2. Go to: Datacenter -> Permissions -> API Tokens" -ForegroundColor Gray
        Write-Host "  3. Add: User=myca@pve, Token ID=mas" -ForegroundColor Gray
        Write-Host "  4. Copy the secret (shown only once)" -ForegroundColor Gray
        Write-Host ""
        
        if ($Interactive) {
            $tokenId = Read-Host "Enter Token ID (e.g., myca@pve!mas)"
            $tokenSecret = Read-Host "Enter Token Secret"
            
            $env:PROXMOX_TOKEN_ID = $tokenId
            $env:PROXMOX_TOKEN_SECRET = $tokenSecret
            
            Write-Host "Creating production VMs..." -ForegroundColor Gray
            python scripts/production/create_all_vms.py --start
        } else {
            Write-Host "Run with -Interactive to enter credentials now," -ForegroundColor Yellow
            Write-Host "or set environment variables:" -ForegroundColor Yellow
            Write-Host '  $env:PROXMOX_TOKEN_ID = "myca@pve!mas"' -ForegroundColor Gray
            Write-Host '  $env:PROXMOX_TOKEN_SECRET = "your-secret"' -ForegroundColor Gray
        }
    }
    Write-Host ""
}

# ============================================================================
# STEP 2: UNIFI NAS CONFIGURATION
# ============================================================================

if (-not $SkipUniFi) {
    Write-Host "STEP 2: UNIFI NAS STORAGE" -ForegroundColor Yellow
    Write-Host "=" * 60
    
    # Test SMB connectivity
    $smbTest = Test-NetConnection -ComputerName 192.168.0.1 -Port 445 -WarningAction SilentlyContinue
    
    if ($smbTest.TcpTestSucceeded) {
        Write-Host "[OK] SMB port is open on Dream Machine" -ForegroundColor Green
    } else {
        Write-Host ""
        Write-Host "[ACTION REQUIRED] Enable SMB on UniFi Dream Machine" -ForegroundColor Red
        Write-Host ""
        Write-Host "Please enable SMB file sharing:" -ForegroundColor White
        Write-Host "  1. Open: https://192.168.0.1" -ForegroundColor Gray
        Write-Host "  2. Login to UniFi OS" -ForegroundColor Gray
        Write-Host "  3. Go to: Storage -> Settings" -ForegroundColor Gray
        Write-Host "  4. Enable 'Windows File Sharing (SMB)'" -ForegroundColor Gray
        Write-Host "  5. Create share: mycosoft (path: /)" -ForegroundColor Gray
        Write-Host "  6. Set permissions (read/write for myca user)" -ForegroundColor Gray
        Write-Host ""
        
        if ($Interactive) {
            Write-Host "Press Enter after enabling SMB..." -ForegroundColor Yellow
            Read-Host
            
            # Re-test
            $smbTest = Test-NetConnection -ComputerName 192.168.0.1 -Port 445 -WarningAction SilentlyContinue
            if ($smbTest.TcpTestSucceeded) {
                Write-Host "[OK] SMB is now accessible!" -ForegroundColor Green
            }
        }
    }
    
    # Try to mount if SMB is available
    if ($smbTest.TcpTestSucceeded) {
        Write-Host "Attempting to mount NAS..." -ForegroundColor Gray
        & .\scripts\mount_nas.ps1
    }
    Write-Host ""
}

# ============================================================================
# STEP 3: DOMAIN CONFIGURATION
# ============================================================================

if (-not $SkipDomain) {
    Write-Host "STEP 3: DOMAIN DNS CONFIGURATION" -ForegroundColor Yellow
    Write-Host "=" * 60
    
    # Check current DNS
    Write-Host "Checking mycosoft.com DNS..." -ForegroundColor Gray
    try {
        $dns = Resolve-DnsName -Name mycosoft.com -Type A -ErrorAction Stop
        Write-Host "  Current DNS: $($dns.IPAddress)" -ForegroundColor Gray
    } catch {
        Write-Host "  DNS lookup failed or domain not configured" -ForegroundColor Yellow
    }
    
    Write-Host ""
    Write-Host "[ACTION REQUIRED] Configure Domain DNS" -ForegroundColor Red
    Write-Host ""
    Write-Host "Option A - Use Cloudflare (Recommended):" -ForegroundColor White
    Write-Host "  1. Login to Cloudflare: https://dash.cloudflare.com" -ForegroundColor Gray
    Write-Host "  2. Add site: mycosoft.com" -ForegroundColor Gray
    Write-Host "  3. Copy the nameservers provided" -ForegroundColor Gray
    Write-Host "  4. In GoDaddy: Update nameservers to Cloudflare's" -ForegroundColor Gray
    Write-Host "  5. Wait for propagation (up to 48h, usually 1-2h)" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Option B - Direct DNS in GoDaddy:" -ForegroundColor White
    Write-Host "  1. Login to GoDaddy: https://dcc.godaddy.com" -ForegroundColor Gray
    Write-Host "  2. Manage DNS for mycosoft.com" -ForegroundColor Gray
    Write-Host "  3. Add A record: @ -> your public IP" -ForegroundColor Gray
    Write-Host "  4. Add CNAME: www -> mycosoft.com" -ForegroundColor Gray
    Write-Host ""
    
    if ($Interactive) {
        Write-Host "Which option did you choose? (A/B/skip)" -ForegroundColor Yellow
        $choice = Read-Host
        
        if ($choice -eq "A") {
            Write-Host "Great! After Cloudflare is configured, run:" -ForegroundColor Green
            Write-Host "  cloudflared tunnel create mycosoft-tunnel" -ForegroundColor Gray
            Write-Host "  cloudflared tunnel route dns mycosoft-tunnel mycosoft.com" -ForegroundColor Gray
        }
    }
    Write-Host ""
}

# ============================================================================
# STEP 4: DEPLOYMENT STATUS
# ============================================================================

Write-Host "STEP 4: DEPLOYMENT STATUS" -ForegroundColor Yellow
Write-Host "=" * 60
Write-Host ""

# Check VMs
Write-Host "Production VMs:" -ForegroundColor Gray
$vms = @(
    @{Name="myca-website"; IP="192.168.20.11"},
    @{Name="myca-api"; IP="192.168.20.10"},
    @{Name="myca-database"; IP="192.168.20.12"}
)

foreach ($vm in $vms) {
    $ping = Test-Connection -ComputerName $vm.IP -Count 1 -Quiet -ErrorAction SilentlyContinue
    if ($ping) {
        Write-Host "  [OK] $($vm.Name) ($($vm.IP)) - Online" -ForegroundColor Green
    } else {
        Write-Host "  [--] $($vm.Name) ($($vm.IP)) - Not created yet" -ForegroundColor Gray
    }
}

Write-Host ""
Write-Host "Local Services:" -ForegroundColor Gray
$services = @(
    @{Name="Website"; Port=3000},
    @{Name="MINDEX API"; Port=8000},
    @{Name="MAS Orchestrator"; Port=8001},
    @{Name="Dashboard"; Port=3100},
    @{Name="n8n"; Port=5678}
)

foreach ($svc in $services) {
    $conn = Test-NetConnection -ComputerName localhost -Port $svc.Port -WarningAction SilentlyContinue
    if ($conn.TcpTestSucceeded) {
        Write-Host "  [OK] $($svc.Name) (:$($svc.Port)) - Running" -ForegroundColor Green
    } else {
        Write-Host "  [--] $($svc.Name) (:$($svc.Port)) - Not running" -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "=" * 60
Write-Host "NEXT STEPS:" -ForegroundColor Yellow
Write-Host "=" * 60
Write-Host ""
Write-Host "1. Complete any ACTION REQUIRED items above" -ForegroundColor White
Write-Host "2. Power on DC1 and DC2 Proxmox nodes if needed" -ForegroundColor White
Write-Host "3. Create Proxmox API token" -ForegroundColor White
Write-Host "4. Enable SMB on Dream Machine NAS" -ForegroundColor White
Write-Host "5. Configure domain DNS (GoDaddy -> Cloudflare)" -ForegroundColor White
Write-Host "6. Re-run this script with -Interactive" -ForegroundColor White
Write-Host ""
Write-Host "Quick commands:" -ForegroundColor Gray
Write-Host '  .\scripts\automated_deployment.ps1 -Interactive' -ForegroundColor Cyan
Write-Host '  python scripts/production/create_all_vms.py --dry-run' -ForegroundColor Cyan
Write-Host ""
