# Import n8n Workflows Script
# Imports all workflows from n8n/workflows directory into n8n instance

param(
    [string]$N8nUrl = "http://localhost:5678",
    [string]$ApiKey = $env:N8N_API_KEY,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
$WorkflowsDir = Join-Path $ProjectRoot "n8n" "workflows"

Write-Host "==================================" -ForegroundColor Cyan
Write-Host "n8n Workflow Import Script" -ForegroundColor Cyan
Write-Host "==================================" -ForegroundColor Cyan
Write-Host "n8n URL: $N8nUrl" -ForegroundColor Yellow
Write-Host "API Key: $(if ($ApiKey) { '[SET]' } else { '[NOT SET]' })" -ForegroundColor Yellow
Write-Host "Mode: $(if ($DryRun) { 'DRY RUN' } else { 'LIVE IMPORT' })" -ForegroundColor Yellow
Write-Host ""

if (-not $ApiKey -and -not $DryRun) {
    Write-Host "ERROR: N8N_API_KEY environment variable is required for import." -ForegroundColor Red
    Write-Host "Set it with: `$env:N8N_API_KEY = 'your_api_key'" -ForegroundColor Yellow
    Write-Host "Or run with -DryRun to preview." -ForegroundColor Yellow
    exit 1
}

# Check if n8n is accessible
try {
    $healthCheck = Invoke-WebRequest -Uri "$N8nUrl/healthz" -Method GET -TimeoutSec 5 -ErrorAction Stop
    Write-Host "✓ n8n is accessible" -ForegroundColor Green
} catch {
    Write-Host "✗ Cannot connect to n8n at $N8nUrl" -ForegroundColor Red
    Write-Host "  Make sure n8n is running and accessible" -ForegroundColor Yellow
    exit 1
}

# Get all workflow JSON files
$workflowFiles = Get-ChildItem -Path $WorkflowsDir -Filter "*.json" -Recurse | 
    Where-Object { $_.Name -notmatch "\\" -and $_.Directory.Name -ne "backup" } |
    Sort-Object Name

if ($workflowFiles.Count -eq 0) {
    Write-Host "WARNING: No workflow files found in $WorkflowsDir" -ForegroundColor Yellow
    exit 0
}

Write-Host "Found $($workflowFiles.Count) workflow files to import" -ForegroundColor Green
Write-Host ""

$successCount = 0
$failCount = 0
$skippedCount = 0

foreach ($file in $workflowFiles) {
    $workflowName = $file.BaseName
    Write-Host "[$($workflowFiles.IndexOf($file) + 1)/$($workflowFiles.Count)] Processing: $workflowName" -ForegroundColor Cyan
    
    try {
        # Read workflow JSON
        $workflowJson = Get-Content $file.FullName -Raw | ConvertFrom-Json
        
        if ($DryRun) {
            Write-Host "  [DRY RUN] Would import: $($workflowJson.name)" -ForegroundColor Yellow
            $skippedCount++
            continue
        }
        
        # Prepare payload for n8n API
        $payload = @{
            name = $workflowJson.name
            nodes = $workflowJson.nodes
            connections = $workflowJson.connections
            settings = if ($workflowJson.settings) { $workflowJson.settings } else { @{ executionOrder = "v1" } }
            active = $false  # Import as inactive first
        } | ConvertTo-Json -Depth 100
        
        # Import workflow via API
        $headers = @{
            "Content-Type" = "application/json"
            "X-N8N-API-KEY" = $ApiKey
        }
        
        $response = Invoke-RestMethod -Uri "$N8nUrl/api/v1/workflows" -Method POST -Headers $headers -Body $payload -ErrorAction Stop
        
        Write-Host "  ✓ Imported: $($response.name) (ID: $($response.id))" -ForegroundColor Green
        $successCount++
        
    } catch {
        $errorMsg = $_.Exception.Message
        if ($_.Exception.Response) {
            $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
            $responseBody = $reader.ReadToEnd()
            $errorMsg = $responseBody
        }
        Write-Host "  ✗ Failed: $errorMsg" -ForegroundColor Red
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

if ($successCount -gt 0 -and -not $DryRun) {
    Write-Host "Workflows imported successfully!" -ForegroundColor Green
    Write-Host "Visit $N8nUrl to activate and configure workflows" -ForegroundColor Cyan
}

