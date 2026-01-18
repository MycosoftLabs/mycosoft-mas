# Deploy to Sandbox via SSH with auto-password
# Uses .NET to handle interactive SSH

$vmHost = "192.168.0.187"
$vmUser = "mycosoft"
$vmPass = "Mushroom1!Mushroom1!"

Write-Host "================================================" -ForegroundColor Cyan
Write-Host "  MYCOSOFT SANDBOX DEPLOYMENT" -ForegroundColor Cyan
Write-Host "  Target: $vmUser@$vmHost (VM 103)" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan

# First, let's set up SSH key auth by copying the public key
$pubKey = Get-Content "$env:USERPROFILE\.ssh\id_rsa.pub" -ErrorAction SilentlyContinue

if ($pubKey) {
    Write-Host "`n[1] Setting up SSH key authentication..." -ForegroundColor Yellow
    
    # Create a temporary script to run on the server
    $setupScript = @"
mkdir -p ~/.ssh
echo '$pubKey' >> ~/.ssh/authorized_keys
chmod 700 ~/.ssh
chmod 600 ~/.ssh/authorized_keys
sort -u ~/.ssh/authorized_keys -o ~/.ssh/authorized_keys
echo 'SSH key added successfully'
"@
    
    # Write setup script to temp file
    $tempScript = [System.IO.Path]::GetTempFileName()
    $setupScript | Out-File -FilePath $tempScript -Encoding ASCII
    
    Write-Host "  Copying SSH public key to server..." -ForegroundColor Gray
    Write-Host "  You will be prompted for password: $vmPass" -ForegroundColor Magenta
    
    # Use ssh-copy-id equivalent
    Get-Content "$env:USERPROFILE\.ssh\id_rsa.pub" | ssh -o StrictHostKeyChecking=no $vmUser@$vmHost "mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys && chmod 700 ~/.ssh && chmod 600 ~/.ssh/authorized_keys"
    
} else {
    Write-Host "No SSH key found. Please run: ssh-keygen" -ForegroundColor Red
    exit 1
}

Write-Host "`n[2] Testing SSH key authentication..." -ForegroundColor Yellow
$test = ssh -o BatchMode=yes -o ConnectTimeout=5 $vmUser@$vmHost "echo 'SSH_KEY_AUTH_SUCCESS'" 2>$null

if ($test -eq "SSH_KEY_AUTH_SUCCESS") {
    Write-Host "  SSH key authentication successful!" -ForegroundColor Green
    
    Write-Host "`n[3] Running deployment commands..." -ForegroundColor Yellow
    
    # Deployment commands
    $commands = @(
        "echo '=== Pulling latest code ===' && cd /opt/mycosoft/website && git pull origin main",
        "echo '=== Rebuilding website container ===' && cd /opt/mycosoft/website && docker-compose -f docker-compose.always-on.yml build mycosoft-website --no-cache",
        "echo '=== Starting website container ===' && cd /opt/mycosoft/website && docker-compose -f docker-compose.always-on.yml up -d mycosoft-website",
        "echo '=== Checking PostGIS ===' && docker exec mindex-postgres psql -U mindex -c 'CREATE EXTENSION IF NOT EXISTS postgis;' 2>/dev/null || echo 'PostGIS skipped'",
        "echo '=== Restarting MINDEX ===' && cd /opt/mycosoft/website && docker-compose -f docker-compose.always-on.yml restart mindex-api 2>/dev/null || echo 'MINDEX restart skipped'",
        "echo '=== Restarting Cloudflare tunnel ===' && sudo systemctl restart cloudflared",
        "echo '=== Container Status ===' && docker ps --format 'table {{.Names}}\t{{.Status}}'"
    )
    
    foreach ($cmd in $commands) {
        Write-Host "`n>>> $cmd" -ForegroundColor Cyan
        ssh -o BatchMode=yes $vmUser@$vmHost $cmd
    }
    
    Write-Host "`n================================================" -ForegroundColor Green
    Write-Host "  DEPLOYMENT COMPLETE!" -ForegroundColor Green
    Write-Host "================================================" -ForegroundColor Green
    Write-Host "`nTest URLs:"
    Write-Host "  - https://sandbox.mycosoft.com"
    Write-Host "  - https://sandbox.mycosoft.com/admin"
    Write-Host "  - https://sandbox.mycosoft.com/natureos/devices"
    
} else {
    Write-Host "  SSH key authentication failed. Manual password entry required." -ForegroundColor Red
    Write-Host "`nPlease run manually:" -ForegroundColor Yellow
    Write-Host "  ssh $vmUser@$vmHost" -ForegroundColor White
    Write-Host "  Password: $vmPass" -ForegroundColor Magenta
}
