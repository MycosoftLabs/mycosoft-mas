# MYCA n8n Workflow Import Script
# Imports all workflow JSON files into n8n instance

param(
    [string]$N8nUrl = "http://localhost:5678",
    [string]$Username = "admin",
    [string]$Password = "",
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$N8nRoot = Split-Path -Parent $ScriptDir
$WorkflowsDir = Join-Path $N8nRoot "workflows"

Write-Host "==================================" -ForegroundColor Cyan
Write-Host "MYCA n8n Workflow Import" -ForegroundColor Cyan
Write-Host "==================================" -ForegroundColor Cyan
Write-Host ""

# Check if workflows directory exists
if (-not (Test-Path $WorkflowsDir)) {
    Write-Host "ERROR: Workflows directory not found: $WorkflowsDir" -ForegroundColor Red
    exit 1
}

# Get password from .env if not provided
if ([string]::IsNullOrEmpty($Password)) {
    $envPath = Join-Path $N8nRoot ".env"
    if (Test-Path $envPath) {
        $envContent = Get-Content $envPath
        $passwordLine = $envContent | Where-Object { $_ -match "^N8N_PASSWORD=(.+)$" }
        if ($passwordLine) {
            $Password = $Matches[1]
        }
    }
}

if ([string]::IsNullOrEmpty($Password)) {
    Write-Host "ERROR: Password not provided and not found in .env file" -ForegroundColor Red
    Write-Host "Usage: .\import.ps1 -Password <password>" -ForegroundColor Yellow
    exit 1
}

# Get all workflow JSON files
$workflowFiles = Get-ChildItem -Path $WorkflowsDir -Filter "*.json" | Sort-Object Name

if ($workflowFiles.Count -eq 0) {
    Write-Host "WARNING: No workflow files found in $WorkflowsDir" -ForegroundColor Yellow
    exit 0
}

Write-Host "Found $($workflowFiles.Count) workflow files" -ForegroundColor Green
Write-Host ""

if ($DryRun) {
    Write-Host "DRY RUN MODE - No workflows will be imported" -ForegroundColor Yellow
    Write-Host ""
    
    foreach ($file in $workflowFiles) {
        Write-Host "  [DRY RUN] Would import: $($file.Name)" -ForegroundColor Gray
    }
    
    exit 0
}

# Create base64 auth header
$authString = "${Username}:${Password}"
$authBytes = [System.Text.Encoding]::ASCII.GetBytes($authString)
$authBase64 = [System.Convert]::ToBase64String($authBytes)
$headers = @{
    "Authorization" = "Basic $authBase64"
    "Content-Type" = "application/json"
}

# Test connection
Write-Host "Testing n8n connection..." -ForegroundColor Yellow
try {
    $testResponse = Invoke-WebRequest -Uri "$N8nUrl/healthz" -UseBasicParsing -TimeoutSec 5
    Write-Host "  ✓ Connected to n8n" -ForegroundColor Green
} catch {
    Write-Host "ERROR: Cannot connect to n8n at $N8nUrl" -ForegroundColor Red
    Write-Host "Make sure n8n is running: docker-compose ps" -ForegroundColor Yellow
    exit 1
}

Write-Host ""
Write-Host "Importing workflows..." -ForegroundColor Yellow
Write-Host ""

$successCount = 0
$failCount = 0
$skippedCount = 0

foreach ($file in $workflowFiles) {
    $workflowName = $file.BaseName
    Write-Host "[$($workflowFiles.IndexOf($file) + 1)/$($workflowFiles.Count)] Importing: $workflowName" -ForegroundColor Cyan
    
    try {
        # Read workflow JSON
        $workflowJson = Get-Content $file.FullName -Raw
        $workflow = $workflowJson | ConvertFrom-Json
        
        # Note: n8n workflow import via API requires special handling
        # This is a simplified version. In production, you might need to use n8n CLI
        # or manually import via UI for first-time setup
        
        Write-Host "  ! Manual import required via n8n UI" -ForegroundColor Yellow
        Write-Host "    File: $($file.FullName)" -ForegroundColor Gray
        $skippedCount++
        
        # Alternative: Use n8n CLI if available
        # n8n import:workflow --input=$($file.FullName)
        
    } catch {
        Write-Host "  ✗ Failed: $_" -ForegroundColor Red
        $failCount++
    }
    
    Write-Host ""
}

# Summary
Write-Host "==================================" -ForegroundColor Cyan
Write-Host "Import Summary" -ForegroundColor Cyan
Write-Host "==================================" -ForegroundColor Cyan
Write-Host "Success:  $successCount" -ForegroundColor Green
Write-Host "Failed:   $failCount" -ForegroundColor Red
Write-Host "Skipped:  $skippedCount" -ForegroundColor Yellow
Write-Host ""

if ($skippedCount -gt 0) {
    Write-Host "NOTE: Automatic workflow import requires n8n CLI or API setup" -ForegroundColor Yellow
    Write-Host "To import manually:" -ForegroundColor Yellow
    Write-Host "  1. Open n8n UI: $N8nUrl" -ForegroundColor White
    Write-Host "  2. Go to Workflows > Import from File" -ForegroundColor White
    Write-Host "  3. Select files from: $WorkflowsDir" -ForegroundColor White
    Write-Host ""
    Write-Host "Or install n8n CLI and use:" -ForegroundColor Yellow
    Write-Host "  npm install -g n8n" -ForegroundColor Gray
    Write-Host "  n8n import:workflow --input=$WorkflowsDir\*.json" -ForegroundColor Gray
    Write-Host ""
}
