# Sync Configuration between Cursor and Claude Code
# Ensures both systems use consistent rules, agents, and skills

param(
    [ValidateSet("ToClaude", "ToCursor", "Both")]
    [string]$Direction = "Both"
)

$RepoRoot = Split-Path $PSScriptRoot -Parent
$CursorDir = Join-Path $RepoRoot ".cursor"
$ClaudeDir = Join-Path $RepoRoot ".claude"

# Ensure directories exist
@($ClaudeDir, "$ClaudeDir\agents") | ForEach-Object {
    if (-not (Test-Path $_)) {
        New-Item -Path $_ -ItemType Directory -Force | Out-Null
    }
}

function Sync-Directory {
    param(
        [string]$Source,
        [string]$Destination,
        [string]$Description
    )
    
    if (-not (Test-Path $Source)) {
        Write-Host "[WARN] Source not found: $Source" -ForegroundColor Yellow
        return
    }
    
    Write-Host "Syncing $Description..." -ForegroundColor Cyan
    
    # Create destination if needed
    if (-not (Test-Path $Destination)) {
        New-Item -Path $Destination -ItemType Directory -Force | Out-Null
    }
    
    # Copy files
    Get-ChildItem -Path $Source -File -Recurse | ForEach-Object {
        $RelativePath = $_.FullName.Substring($Source.Length + 1)
        $DestFile = Join-Path $Destination $RelativePath
        $DestDir = Split-Path $DestFile -Parent
        
        if (-not (Test-Path $DestDir)) {
            New-Item -Path $DestDir -ItemType Directory -Force | Out-Null
        }
        
        Copy-Item -Path $_.FullName -Destination $DestFile -Force
        Write-Host "  [OK] $RelativePath" -ForegroundColor Green
    }
}

# Cursor → Claude
if ($Direction -in @("ToClaude", "Both")) {
    Write-Host "`n=== Syncing Cursor → Claude ===" -ForegroundColor Magenta
    
    # Sync agents
    Sync-Directory "$CursorDir\agents" "$ClaudeDir\agents" "agents"
    
    # Sync rules to CLAUDE.md (augment)
    if (Test-Path "$CursorDir\rules") {
        Write-Host "Syncing rules to CLAUDE.md..." -ForegroundColor Cyan
        $ClaudeMd = Join-Path $RepoRoot "CLAUDE.md"
        $ClaudeContent = Get-Content $ClaudeMd -Raw
        
        # Add cursor rules reference if not present
        if ($ClaudeContent -notmatch "\.cursor/rules") {
            $RulesSection = @"

## Cursor Rules Integration

This project uses Cursor with specialized rules in `.cursor/rules/`:
- `python-process-registry.mdc` - Process and port management
- `vm-layout-and-dev-remote-services.mdc` - VM infrastructure
- `autostart-services.mdc` - Background services
- See `.cursor/rules/` for full list

When making changes, respect these rules and registries.
"@
            Add-Content -Path $ClaudeMd -Value $RulesSection
            Write-Host "  [OK] Added Cursor rules reference to CLAUDE.md" -ForegroundColor Green
        }
    }
}

# Claude → Cursor
if ($Direction -in @("ToCursor", "Both")) {
    Write-Host "`n=== Syncing Claude → Cursor ===" -ForegroundColor Magenta
    
    # Sync Claude-specific agents back to Cursor
    if (Test-Path "$ClaudeDir\agents") {
        Sync-Directory "$ClaudeDir\agents" "$CursorDir\agents" "Claude agents to Cursor"
    }
}

Write-Host "`n[OK] Configuration sync complete" -ForegroundColor Green
Write-Host "Both Cursor and Claude Code now use consistent configuration" -ForegroundColor Cyan
