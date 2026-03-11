# Apply C-Suite role manifest — install role-specific apps from shared YAML config
# Date: March 7, 2026
# Run after bootstrap_openclaw_windows.ps1
# Usage: .\apply_role_manifest.ps1 -Role ceo
# Manifest source: config/csuite_role_manifests.yaml (via emit_role_config.py)

param(
    [ValidateSet("ceo", "cfo", "cto", "coo")]
    [string]$Role = "ceo",
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

# Fallback if config unavailable (e.g. guest without repo)
$Manifests = @{
    ceo = @{ Name = "Atlas"; Tool = "MYCAOS"; Apps = @("Google.Chrome", "Discord.Discord", "SlackTechnologies.Slack", "Notion.Notion") }
    cfo = @{ Name = "Meridian"; Tool = "Perplexity"; Apps = @("Google.Chrome", "Discord.Discord", "SlackTechnologies.Slack", "Perplexity.Perplexity", "Microsoft.Excel") }
    cto = @{ Name = "Forge"; Tool = "Cursor"; Apps = @("Google.Chrome", "Discord.Discord", "SlackTechnologies.Slack", "Cursor.Cursor", "Git.Git", "Microsoft.VisualStudioCode", "GitHub.cli") }
    coo = @{ Name = "Nexus"; Tool = "Claude Cowork"; Apps = @("Google.Chrome", "Discord.Discord", "SlackTechnologies.Slack", "Anthropic.Claude", "Asana.Asana") }
}

$cfg = $null
$configPaths = @(
    "$env:CSUITE_ROOT\config\role_config.json",
    "$env:ProgramData\Mycosoft\C-Suite\role_config.json",
    (Join-Path $PSScriptRoot "..\..\config\role_config.json")
)

foreach ($p in $configPaths) {
    if ($p -and (Test-Path $p)) {
        try {
            $json = Get-Content $p -Raw | ConvertFrom-Json
            if ($json.role_key -eq $Role -or $json.role -eq $Role) {
                $cfg = @{ Name = $json.assistant_name; Tool = $json.primary_tool; Apps = @($json.apps) }
                break
            }
        } catch {}
    }
}

if (-not $cfg) {
    $emitScript = Join-Path $PSScriptRoot "emit_role_config.py"
    $tempConfig = "$env:TEMP\csuite_role_config_$Role.json"
    if ((Test-Path $emitScript) -and (Get-Command python -ErrorAction SilentlyContinue)) {
        try {
            python $emitScript -r $Role -o $tempConfig 2>$null
            if (Test-Path $tempConfig) {
                $json = Get-Content $tempConfig -Raw | ConvertFrom-Json
                $cfg = @{ Name = $json.assistant_name; Tool = $json.primary_tool; Apps = @($json.apps) }
                Remove-Item $tempConfig -Force -ErrorAction SilentlyContinue
            }
        } catch {}
    }
}

if (-not $cfg) {
    $cfg = $Manifests[$Role]
    Write-Warning "[Manifest] Using fallback hardcoded config for $Role. Place role_config.json for authoritative config."
}

Write-Host "[Manifest] Applying $Role — $($cfg.Name) / $($cfg.Tool)" -ForegroundColor Cyan

foreach ($id in $cfg.Apps) {
    if ($DryRun) {
        Write-Host "  [DRY RUN] winget install $id"
    } else {
        Write-Host "  Installing $id..." -ForegroundColor Gray
        winget install $id --accept-package-agreements --accept-source-agreements 2>$null
    }
}
Write-Host "[Manifest] Role $Role applied." -ForegroundColor Green
