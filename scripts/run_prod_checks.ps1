<#
.SYNOPSIS
  Convenience runner for production readiness checks.

.DESCRIPTION
  Runs:
  - PowerShell smoke test (black box HTTP)
  - Dashboard E2E (Playwright) if requested

.PARAMETER DashboardUrl
  Base URL for dashboard (default: http://127.0.0.1:3000)

.PARAMETER RunE2E
  If set, runs Playwright E2E tests (requires Playwright browsers installed).
#>

param(
  [string]$DashboardUrl = "http://127.0.0.1:3000",
  [switch]$RunE2E
)

$ErrorActionPreference = "Stop"

Write-Host "Running smoke test..." -ForegroundColor Cyan
& "$PSScriptRoot\\prod_smoke_test.ps1" -DashboardUrl $DashboardUrl

if ($RunE2E) {
  Write-Host ""
  Write-Host "Running Playwright E2E..." -ForegroundColor Cyan

  $dashDir = Join-Path (Split-Path $PSScriptRoot -Parent) "unifi-dashboard"
  if (-not (Test-Path $dashDir)) { throw "unifi-dashboard not found at $dashDir" }

  # Ensure browsers installed (safe if already installed)
  npm --prefix $dashDir exec playwright install
  npm --prefix $dashDir run test:e2e
}

Write-Host ""
Write-Host "✅ Production checks complete." -ForegroundColor Green

