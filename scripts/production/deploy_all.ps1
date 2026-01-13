# MYCA Production Deployment Master Script
# Run from mycocomp to deploy the entire system

param(
    [switch]$DryRun = $false,
    [switch]$SkipVMs = $false,
    [switch]$SkipMigration = $false,
    [switch]$Force = $false
)

$ErrorActionPreference = "Stop"

Write-Host "=================================================="
Write-Host "  MYCA Production Deployment"
Write-Host "=================================================="
Write-Host ""

if ($DryRun) {
    Write-Host "  [DRY RUN MODE - No changes will be made]" -ForegroundColor Yellow
    Write-Host ""
}

# Configuration
$PROXMOX_HOST = "192.168.0.202"  # Build node
$WEBSITE_VM = "192.168.20.11"
$API_VM = "192.168.20.10"
$DB_VM = "192.168.20.12"
$NAS_IP = "192.168.0.1"
$REPO_PATH = "C:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas"

# Check prerequisites
Write-Host "Step 1: Checking prerequisites..." -ForegroundColor Cyan

# Check Git
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Host "  [FAIL] Git not found" -ForegroundColor Red
    exit 1
}
Write-Host "  [OK] Git available" -ForegroundColor Green

# Check SSH
if (-not (Get-Command ssh -ErrorAction SilentlyContinue)) {
    Write-Host "  [FAIL] SSH not found" -ForegroundColor Red
    exit 1
}
Write-Host "  [OK] SSH available" -ForegroundColor Green

# Check Python
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "  [FAIL] Python not found" -ForegroundColor Red
    exit 1
}
Write-Host "  [OK] Python available" -ForegroundColor Green

# Check Proxmox credentials
if (-not $env:PROXMOX_TOKEN_ID -or -not $env:PROXMOX_TOKEN_SECRET) {
    Write-Host "  [WARN] PROXMOX_TOKEN_ID or PROXMOX_TOKEN_SECRET not set" -ForegroundColor Yellow
    Write-Host "         Set these to enable VM creation" -ForegroundColor Yellow
}

Write-Host ""

# Step 2: Commit latest code
Write-Host "Step 2: Committing latest code to GitHub..." -ForegroundColor Cyan
Set-Location $REPO_PATH

$status = git status --porcelain
if ($status) {
    if (-not $DryRun) {
        git add -A
        git commit -m "chore: production deployment preparation"
        git push origin main
        Write-Host "  [OK] Code pushed to GitHub" -ForegroundColor Green
    } else {
        Write-Host "  [DRY RUN] Would commit and push changes" -ForegroundColor Yellow
    }
} else {
    Write-Host "  [OK] No changes to commit" -ForegroundColor Green
}

Write-Host ""

# Step 3: Create VMs
if (-not $SkipVMs) {
    Write-Host "Step 3: Creating production VMs..." -ForegroundColor Cyan
    
    if ($DryRun) {
        python scripts/production/create_all_vms.py --dry-run
    } else {
        if ($env:PROXMOX_TOKEN_ID -and $env:PROXMOX_TOKEN_SECRET) {
            python scripts/production/create_all_vms.py --start
        } else {
            Write-Host "  [SKIP] No Proxmox credentials - VMs must be created manually" -ForegroundColor Yellow
        }
    }
} else {
    Write-Host "Step 3: Skipping VM creation (--SkipVMs)" -ForegroundColor Yellow
}

Write-Host ""

# Step 4: Wait for VMs to be ready
Write-Host "Step 4: Waiting for VMs to be ready..." -ForegroundColor Cyan

$VMs = @($WEBSITE_VM, $API_VM, $DB_VM)
foreach ($vm in $VMs) {
    $attempts = 0
    $maxAttempts = 30
    
    while ($attempts -lt $maxAttempts) {
        if (Test-Connection -ComputerName $vm -Count 1 -Quiet) {
            Write-Host "  [OK] $vm is responding" -ForegroundColor Green
            break
        }
        $attempts++
        if ($attempts -lt $maxAttempts) {
            Write-Host "  Waiting for $vm... ($attempts/$maxAttempts)" -ForegroundColor Gray
            Start-Sleep -Seconds 10
        }
    }
    
    if ($attempts -eq $maxAttempts) {
        Write-Host "  [WARN] $vm not responding after ${maxAttempts} attempts" -ForegroundColor Yellow
    }
}

Write-Host ""

# Step 5: Deploy to VMs
Write-Host "Step 5: Deploying to VMs..." -ForegroundColor Cyan

$deployScript = @"
#!/bin/bash
cd /opt/myca
git pull origin main
./scripts/production/vm_setup_common.sh
"@

foreach ($vm in $VMs) {
    Write-Host "  Deploying to $vm..." -ForegroundColor Gray
    
    if (-not $DryRun) {
        # Copy setup scripts
        scp -o StrictHostKeyChecking=no -r scripts/production/* myca@${vm}:/opt/myca/scripts/production/
        
        # Run setup
        ssh -o StrictHostKeyChecking=no myca@$vm "chmod +x /opt/myca/scripts/production/*.sh && /opt/myca/scripts/production/vm_setup_common.sh"
    } else {
        Write-Host "    [DRY RUN] Would deploy to $vm" -ForegroundColor Yellow
    }
}

Write-Host ""

# Step 6: Setup Database VM
Write-Host "Step 6: Setting up Database VM..." -ForegroundColor Cyan

if (-not $DryRun) {
    ssh -o StrictHostKeyChecking=no myca@$DB_VM "/opt/myca/scripts/production/setup_database_vm.sh"
    Write-Host "  [OK] Database VM configured" -ForegroundColor Green
} else {
    Write-Host "  [DRY RUN] Would configure database VM" -ForegroundColor Yellow
}

Write-Host ""

# Step 7: Setup API VM
Write-Host "Step 7: Setting up API VM..." -ForegroundColor Cyan

if (-not $DryRun) {
    ssh -o StrictHostKeyChecking=no myca@$API_VM "/opt/myca/scripts/production/setup_api_vm.sh"
    Write-Host "  [OK] API VM configured" -ForegroundColor Green
} else {
    Write-Host "  [DRY RUN] Would configure API VM" -ForegroundColor Yellow
}

Write-Host ""

# Step 8: Setup Website VM
Write-Host "Step 8: Setting up Website VM..." -ForegroundColor Cyan

if (-not $DryRun) {
    ssh -o StrictHostKeyChecking=no myca@$WEBSITE_VM "/opt/myca/scripts/production/setup_website_vm.sh"
    Write-Host "  [OK] Website VM configured" -ForegroundColor Green
} else {
    Write-Host "  [DRY RUN] Would configure website VM" -ForegroundColor Yellow
}

Write-Host ""

# Step 9: Migrate databases
if (-not $SkipMigration) {
    Write-Host "Step 9: Migrating databases..." -ForegroundColor Cyan
    
    if (-not $DryRun) {
        & bash scripts/production/migrate_databases.sh
        Write-Host "  [OK] Database migration complete" -ForegroundColor Green
    } else {
        Write-Host "  [DRY RUN] Would migrate databases" -ForegroundColor Yellow
    }
} else {
    Write-Host "Step 9: Skipping database migration (--SkipMigration)" -ForegroundColor Yellow
}

Write-Host ""

# Step 10: Setup Cloudflare Tunnel
Write-Host "Step 10: Setting up Cloudflare Tunnel..." -ForegroundColor Cyan

if (-not $DryRun) {
    Write-Host "  Run manually on API VM:" -ForegroundColor Yellow
    Write-Host "    ssh myca@$API_VM" -ForegroundColor Gray
    Write-Host "    /opt/myca/scripts/production/setup_cloudflare_tunnel.sh" -ForegroundColor Gray
} else {
    Write-Host "  [DRY RUN] Cloudflare tunnel requires manual setup" -ForegroundColor Yellow
}

Write-Host ""

# Step 11: Run go-live checklist
Write-Host "Step 11: Running go-live verification..." -ForegroundColor Cyan

if (-not $DryRun) {
    ssh -o StrictHostKeyChecking=no myca@$API_VM "/opt/myca/scripts/production/go_live_checklist.sh"
} else {
    Write-Host "  [DRY RUN] Would run go-live checklist" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "=================================================="
Write-Host "  Deployment Complete!"
Write-Host "=================================================="
Write-Host ""
Write-Host "  Next steps:"
Write-Host "  1. Configure Cloudflare tunnel on API VM"
Write-Host "  2. Update /etc/myca/*.env with real credentials"
Write-Host "  3. Create staff accounts: npx ts-node scripts/production/create_staff_accounts.ts"
Write-Host "  4. Configure Cloudflare Access policies"
Write-Host "  5. Test: https://mycosoft.com"
Write-Host ""
