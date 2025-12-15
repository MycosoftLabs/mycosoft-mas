# Dependency Check Script
Write-Host "Checking installed dependencies..." -ForegroundColor Cyan

function Test-Command {
    param([string]$Name, [string]$Command, [string]$VersionCmd = $null)
    $exists = $null -ne (Get-Command $Command -ErrorAction SilentlyContinue)
    if ($exists) {
        $version = if ($VersionCmd) {
            try { Invoke-Expression $VersionCmd 2>&1 | Select-Object -First 1 } catch { "unknown" }
        } else { "installed" }
        Write-Host "✓ $Name : $version" -ForegroundColor Green
        return $true
    } else {
        Write-Host "✗ $Name : Not installed" -ForegroundColor Red
        return $false
    }
}

Write-Host "`nCore Tools:" -ForegroundColor Yellow
Test-Command "Python" "python" "python --version"
Test-Command "pip" "pip" "pip --version"
Test-Command "Poetry" "poetry" "poetry --version"
Test-Command "Node.js" "node" "node --version"
Test-Command "npm" "npm" "npm --version"
Test-Command "Docker" "docker" "docker --version"
Test-Command "Git" "git" "git --version"

Write-Host "`nCloud CLIs:" -ForegroundColor Yellow
Test-Command "Azure CLI" "az" "az --version"
Test-Command "GitHub CLI" "gh" "gh --version"
Test-Command "Vercel CLI" "vercel" "vercel --version"

Write-Host "`nDatabase Tools:" -ForegroundColor Yellow
Test-Command "PostgreSQL" "psql" "psql --version"
Test-Command "Redis" "redis-cli" "redis-cli --version"

Write-Host "`nWorkflow:" -ForegroundColor Yellow
Test-Command "N8N" "n8n" "n8n --version"

Write-Host "`nPython Packages:" -ForegroundColor Yellow
$pythonPkgs = @("notion_client", "asana", "google", "azure", "prometheus_client", "redis", "psycopg2")
foreach ($pkg in $pythonPkgs) {
    $installed = python -c "import $pkg" 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ $pkg" -ForegroundColor Green
    } else {
        Write-Host "✗ $pkg" -ForegroundColor Red
    }
}
