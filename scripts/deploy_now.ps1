# MAS Deployment Script - Jan 26, 2026
# Run this to deploy to MAS VM (192.168.0.188)

$MAS_VM = "192.168.0.188"
$SANDBOX_VM = "192.168.0.187"
$USER = "mycosoft"
$PASS = "REDACTED_VM_SSH_PASSWORD"

Write-Host "=== MAS Deployment Script ===" -ForegroundColor Cyan
Write-Host "Date: $(Get-Date)" -ForegroundColor Gray

# Check if Posh-SSH module is available
if (-not (Get-Module -ListAvailable -Name Posh-SSH)) {
    Write-Host "Installing Posh-SSH module..." -ForegroundColor Yellow
    Install-Module -Name Posh-SSH -Force -Scope CurrentUser
}

Import-Module Posh-SSH

# Create credential
$SecPass = ConvertTo-SecureString $PASS -AsPlainText -Force
$Cred = New-Object System.Management.Automation.PSCredential ($USER, $SecPass)

# Deploy to MAS VM
Write-Host "`n=== Deploying to MAS VM ($MAS_VM) ===" -ForegroundColor Green
try {
    $session = New-SSHSession -ComputerName $MAS_VM -Credential $Cred -AcceptKey -Force
    
    # Pull latest code
    Write-Host "Pulling latest code..." -ForegroundColor Yellow
    $result = Invoke-SSHCommand -SessionId $session.SessionId -Command "cd /opt/mycosoft/mas && git pull origin main"
    Write-Host $result.Output
    
    # Restart orchestrator
    Write-Host "Restarting orchestrator..." -ForegroundColor Yellow
    $result = Invoke-SSHCommand -SessionId $session.SessionId -Command "pkill -f orchestrator_service; sleep 2; cd /opt/mycosoft/mas && nohup python3 -m mycosoft_mas.core.orchestrator_service > /var/log/myca-orchestrator.log 2>&1 &"
    Write-Host "Orchestrator restarted"
    
    # Verify
    Start-Sleep -Seconds 3
    $result = Invoke-SSHCommand -SessionId $session.SessionId -Command "curl -s http://localhost:8001/health"
    Write-Host "Health check: $($result.Output)" -ForegroundColor Cyan
    
    Remove-SSHSession -SessionId $session.SessionId
    Write-Host "MAS VM deployment complete!" -ForegroundColor Green
} catch {
    Write-Host "Error deploying to MAS VM: $_" -ForegroundColor Red
}

# Deploy to Sandbox VM
Write-Host "`n=== Deploying to Sandbox VM ($SANDBOX_VM) ===" -ForegroundColor Green
try {
    $session = New-SSHSession -ComputerName $SANDBOX_VM -Credential $Cred -AcceptKey -Force
    
    # Pull latest code
    Write-Host "Pulling latest code..." -ForegroundColor Yellow
    $result = Invoke-SSHCommand -SessionId $session.SessionId -Command "cd /opt/mycosoft/website && git pull origin main"
    Write-Host $result.Output
    
    # Rebuild Docker image
    Write-Host "Rebuilding Docker image (this may take a few minutes)..." -ForegroundColor Yellow
    $result = Invoke-SSHCommand -SessionId $session.SessionId -Command "cd /opt/mycosoft/website && docker build -t mycosoft-website:latest ." -Timeout 600
    Write-Host "Docker build complete"
    
    # Restart container
    Write-Host "Restarting container..." -ForegroundColor Yellow
    $result = Invoke-SSHCommand -SessionId $session.SessionId -Command @"
docker stop mycosoft-website 2>/dev/null || true
docker rm mycosoft-website 2>/dev/null || true
docker run -d --name mycosoft-website -p 3000:3000 \
  -v /opt/mycosoft/media/website/assets:/app/public/assets:ro \
  --restart unless-stopped mycosoft-website:latest
"@
    Write-Host "Container restarted"
    
    # Verify
    Start-Sleep -Seconds 5
    $result = Invoke-SSHCommand -SessionId $session.SessionId -Command "docker ps | grep mycosoft-website"
    Write-Host "Container status: $($result.Output)" -ForegroundColor Cyan
    
    Remove-SSHSession -SessionId $session.SessionId
    Write-Host "Sandbox VM deployment complete!" -ForegroundColor Green
} catch {
    Write-Host "Error deploying to Sandbox VM: $_" -ForegroundColor Red
}

Write-Host "`n=== Deployment Complete ===" -ForegroundColor Cyan
Write-Host "Remember to clear Cloudflare cache!" -ForegroundColor Yellow
