# n8n Workflow Import Script (PowerShell)
#
# Imports all MAS workflows into n8n via the API.
#
# Environment Variables:
#   N8N_API_URL - n8n API URL (default: http://localhost:5678)
#   N8N_API_KEY - n8n API key
#
# Usage:
#   .\import-workflows.ps1
#   .\import-workflows.ps1 -DryRun

param(
    [switch]$DryRun
)

$N8N_API_URL = if ($env:N8N_API_URL) { $env:N8N_API_URL } else { "http://localhost:5678" }
$N8N_API_KEY = $env:N8N_API_KEY

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$WorkflowsDir = Join-Path (Split-Path -Parent $ScriptDir) "workflows"

Write-Host "=" * 60
Write-Host "n8n Workflow Import Script (PowerShell)"
Write-Host "=" * 60
Write-Host "n8n API URL: $N8N_API_URL"
Write-Host "API Key: $(if ($N8N_API_KEY) { '[SET]' } else { '[NOT SET]' })"
Write-Host "Mode: $(if ($DryRun) { 'DRY RUN' } else { 'LIVE IMPORT' })"
Write-Host "Workflows Dir: $WorkflowsDir"
Write-Host "=" * 60

if (-not $N8N_API_KEY -and -not $DryRun) {
    Write-Error "ERROR: N8N_API_KEY environment variable is required for import."
    Write-Host 'Set it with: $env:N8N_API_KEY = "your_api_key"'
    Write-Host "Or run with -DryRun to preview."
    exit 1
}

# Get all workflow JSON files
$WorkflowFiles = Get-ChildItem -Path $WorkflowsDir -Filter "*.json" | 
    Where-Object { $_.Name -notmatch "\\" } |
    Sort-Object Name

Write-Host "`nFound $($WorkflowFiles.Count) workflow files to import.`n"

$SuccessCount = 0
$FailCount = 0
$Results = @()

foreach ($File in $WorkflowFiles) {
    try {
        $WorkflowData = Get-Content -Path $File.FullName -Raw | ConvertFrom-Json
        $WorkflowName = $WorkflowData.name
        
        if ($DryRun) {
            Write-Host "[DRY RUN] Would import: $($File.Name) - `"$WorkflowName`""
            $SuccessCount++
            continue
        }
        
        $Headers = @{
            "Content-Type" = "application/json"
            "X-N8N-API-KEY" = $N8N_API_KEY
        }
        
        $Body = Get-Content -Path $File.FullName -Raw
        
        $Response = Invoke-RestMethod -Uri "$N8N_API_URL/api/v1/workflows" `
            -Method Post `
            -Headers $Headers `
            -Body $Body `
            -ErrorAction Stop
        
        Write-Host "✓ Imported: $($File.Name) -> ID: $($Response.id) (`"$($Response.name)`")" -ForegroundColor Green
        $SuccessCount++
        $Results += @{
            Name = $Response.name
            Id = $Response.id
            File = $File.Name
        }
        
    } catch {
        Write-Host "✗ Failed: $($File.Name) - $($_.Exception.Message)" -ForegroundColor Red
        $FailCount++
    }
}

Write-Host "`n" + "=" * 60
Write-Host "Import Summary"
Write-Host "=" * 60
Write-Host "Successful: $SuccessCount" -ForegroundColor Green
Write-Host "Failed: $FailCount" -ForegroundColor $(if ($FailCount -gt 0) { "Red" } else { "Green" })

if ($Results.Count -gt 0 -and -not $DryRun) {
    Write-Host "`n" + "=" * 60
    Write-Host "Workflow IDs for .env file:"
    Write-Host "=" * 60
    foreach ($r in $Results) {
        Write-Host "$($r.File): $($r.Id)"
    }
}
