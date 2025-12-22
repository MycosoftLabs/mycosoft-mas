# n8n Workflow Import Script
# Imports all MYCA workflows to n8n instance

param(
    [string]$N8nUrl = "http://localhost:5678",
    [string]$WorkflowsDir = "$PSScriptRoot\..\workflows"
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   MYCA n8n Workflow Importer" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Get all workflow JSON files
$workflowFiles = Get-ChildItem -Path $WorkflowsDir -Filter "*.json" -File | Sort-Object Name

Write-Host "Found $($workflowFiles.Count) workflow files to import" -ForegroundColor Green
Write-Host ""

$imported = 0
$failed = 0

foreach ($file in $workflowFiles) {
    Write-Host "Importing: $($file.Name)..." -NoNewline
    
    try {
        # Read the workflow JSON
        $workflowJson = Get-Content -Path $file.FullName -Raw | ConvertFrom-Json
        
        # Prepare the workflow for import (remove id if present to create new)
        if ($workflowJson.id) {
            $workflowJson.PSObject.Properties.Remove('id')
        }
        
        # Ensure workflow is active
        $workflowJson | Add-Member -NotePropertyName "active" -NotePropertyValue $false -Force
        
        # Convert back to JSON
        $body = $workflowJson | ConvertTo-Json -Depth 100 -Compress
        
        # Import via n8n API
        $response = Invoke-RestMethod -Uri "$N8nUrl/api/v1/workflows" -Method POST -ContentType "application/json" -Body $body -ErrorAction Stop
        
        Write-Host " OK (ID: $($response.id))" -ForegroundColor Green
        $imported++
        
    } catch {
        Write-Host " FAILED: $($_.Exception.Message)" -ForegroundColor Red
        $failed++
    }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Import Complete!" -ForegroundColor Green
Write-Host "  Imported: $imported" -ForegroundColor Green
Write-Host "  Failed: $failed" -ForegroundColor $(if ($failed -gt 0) { "Red" } else { "Green" })
Write-Host "========================================" -ForegroundColor Cyan
