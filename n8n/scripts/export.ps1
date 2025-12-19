# MYCA n8n Workflow Export Script
# Exports all workflows from n8n instance to JSON files

param(
    [string]$N8nUrl = "http://localhost:5678",
    [string]$Username = "admin",
    [string]$Password = "",
    [string]$OutputDir = "",
    [switch]$Backup
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$N8nRoot = Split-Path -Parent $ScriptDir

if ([string]::IsNullOrEmpty($OutputDir)) {
    if ($Backup) {
        $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
        $OutputDir = Join-Path $N8nRoot "backups\workflows_$timestamp"
    } else {
        $OutputDir = Join-Path $N8nRoot "workflows"
    }
}

Write-Host "==================================" -ForegroundColor Cyan
Write-Host "MYCA n8n Workflow Export" -ForegroundColor Cyan
Write-Host "==================================" -ForegroundColor Cyan
Write-Host ""

# Create output directory if it doesn't exist
if (-not (Test-Path $OutputDir)) {
    New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
    Write-Host "Created output directory: $OutputDir" -ForegroundColor Green
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
    Write-Host "Usage: .\export.ps1 -Password <password>" -ForegroundColor Yellow
    exit 1
}

Write-Host "Output directory: $OutputDir" -ForegroundColor Cyan
Write-Host ""

# Note: n8n workflow export via API requires proper setup
# This is a placeholder for the export logic
Write-Host "NOTE: Workflow export requires n8n CLI or manual export" -ForegroundColor Yellow
Write-Host ""
Write-Host "To export manually:" -ForegroundColor Yellow
Write-Host "  1. Open n8n UI: $N8nUrl" -ForegroundColor White
Write-Host "  2. Open each workflow" -ForegroundColor White
Write-Host "  3. Click Download > Export as JSON" -ForegroundColor White
Write-Host "  4. Save to: $OutputDir" -ForegroundColor White
Write-Host ""
Write-Host "Or use n8n CLI:" -ForegroundColor Yellow
Write-Host "  n8n export:workflow --all --output=$OutputDir" -ForegroundColor Gray
Write-Host ""
Write-Host "For automated backup, add this to a scheduled task:" -ForegroundColor Yellow
Write-Host "  .\export.ps1 -Backup" -ForegroundColor Gray
Write-Host ""
