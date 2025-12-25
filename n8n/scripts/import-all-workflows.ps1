# N8n Workflow Import Script
# Imports all JSON workflow files into the running N8n instance

$N8N_URL = "http://localhost:5678"
$WORKFLOWS_DIR = "$PSScriptRoot\..\workflows"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "N8N Workflow Importer" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# Check if N8n is running
try {
    $health = Invoke-RestMethod -Uri "$N8N_URL/healthz" -Method GET -TimeoutSec 5
    Write-Host "✓ N8n is running" -ForegroundColor Green
} catch {
    Write-Host "✗ N8n is not accessible at $N8N_URL" -ForegroundColor Red
    Write-Host "  Make sure N8n is running: docker compose up -d n8n" -ForegroundColor Yellow
    exit 1
}

# Get all workflow JSON files
$workflowFiles = Get-ChildItem -Path $WORKFLOWS_DIR -Filter "*.json" -Recurse

Write-Host "`nFound $($workflowFiles.Count) workflow files to import" -ForegroundColor Yellow

$imported = 0
$failed = 0
$skipped = 0

foreach ($file in $workflowFiles) {
    Write-Host "`nProcessing: $($file.Name)" -ForegroundColor Cyan
    
    try {
        # Read workflow JSON
        $workflowJson = Get-Content -Path $file.FullName -Raw | ConvertFrom-Json
        $workflowName = $workflowJson.name
        
        if (-not $workflowName) {
            Write-Host "  ⚠ No workflow name found, skipping" -ForegroundColor Yellow
            $skipped++
            continue
        }
        
        # Check if workflow already exists
        try {
            $existingWorkflows = Invoke-RestMethod -Uri "$N8N_URL/api/v1/workflows" -Method GET -ContentType "application/json"
            $existing = $existingWorkflows.data | Where-Object { $_.name -eq $workflowName }
            
            if ($existing) {
                Write-Host "  → Workflow '$workflowName' already exists (ID: $($existing.id)), updating..." -ForegroundColor Yellow
                
                # Update existing workflow
                $updateBody = $workflowJson | ConvertTo-Json -Depth 50 -Compress
                $updateResult = Invoke-RestMethod -Uri "$N8N_URL/api/v1/workflows/$($existing.id)" -Method PATCH -Body $updateBody -ContentType "application/json"
                Write-Host "  ✓ Updated workflow: $workflowName" -ForegroundColor Green
                $imported++
                continue
            }
        } catch {
            # API might require auth, try direct import
        }
        
        # Import workflow
        $importBody = $workflowJson | ConvertTo-Json -Depth 50 -Compress
        $result = Invoke-RestMethod -Uri "$N8N_URL/api/v1/workflows" -Method POST -Body $importBody -ContentType "application/json"
        
        Write-Host "  ✓ Imported: $workflowName (ID: $($result.id))" -ForegroundColor Green
        
        # Activate the workflow if it has webhooks
        if ($workflowJson.active -eq $true -or ($workflowJson.nodes | Where-Object { $_.type -like "*webhook*" })) {
            try {
                $activateResult = Invoke-RestMethod -Uri "$N8N_URL/api/v1/workflows/$($result.id)/activate" -Method POST -ContentType "application/json"
                Write-Host "  ✓ Activated workflow" -ForegroundColor Green
            } catch {
                Write-Host "  ⚠ Could not activate (may need manual activation)" -ForegroundColor Yellow
            }
        }
        
        $imported++
        
    } catch {
        Write-Host "  ✗ Failed to import: $($_.Exception.Message)" -ForegroundColor Red
        $failed++
    }
}

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "Import Complete" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Imported/Updated: $imported" -ForegroundColor Green
Write-Host "  Failed: $failed" -ForegroundColor $(if ($failed -gt 0) { "Red" } else { "Green" })
Write-Host "  Skipped: $skipped" -ForegroundColor Yellow
Write-Host "`nAccess N8n UI at: $N8N_URL" -ForegroundColor Cyan

