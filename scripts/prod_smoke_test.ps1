<#
.SYNOPSIS
  Production-readiness smoke test for MYCA dashboard + services.

.DESCRIPTION
  Validates that key endpoints used by the dashboard work in a way that should
  remain stable when moving from local/dev to staging/prod.

  This is intentionally "black box": it hits HTTP endpoints like a real client would.

.PARAMETER DashboardUrl
  Base URL for the dashboard (e.g. http://127.0.0.1:3000 or https://dashboard.mycosoft.com)

.PARAMETER MasUrl
  Base URL for MAS backend (e.g. http://localhost:8001)

.PARAMETER N8nUrl
  Base URL for n8n (e.g. http://localhost:5678)

.PARAMETER ElevenLabsProxyUrl
  Base URL for ElevenLabs proxy (e.g. http://localhost:5501)

.PARAMETER N8nApiKey
  Optional n8n API key. If provided, the test will verify workflows exist.

.PARAMETER RequireN8nWebhooks
  If set, fail if n8n webhook endpoints return 404 (i.e., require production webhooks to be working).
#>

param(
  [string]$DashboardUrl = "http://127.0.0.1:3000",
  [string]$MasUrl = "http://localhost:8001",
  [string]$N8nUrl = "http://localhost:5678",
  [string]$ElevenLabsProxyUrl = "http://localhost:5501",
  [string]$N8nApiKey = "",
  [switch]$RequireN8nWebhooks
)

$ErrorActionPreference = "Stop"

function Write-Section([string]$Title) {
  Write-Host ""
  Write-Host "=== $Title ===" -ForegroundColor Cyan
}

function Assert-True([bool]$Condition, [string]$Message) {
  if (-not $Condition) {
    throw "FAIL: $Message"
  }
  Write-Host "PASS: $Message" -ForegroundColor Green
}

function Invoke-JsonPost([string]$Url, [object]$Body, [int]$TimeoutSec = 30) {
  $json = $Body | ConvertTo-Json -Depth 20
  return Invoke-WebRequest -Uri $Url -Method POST -ContentType "application/json" -Body $json -TimeoutSec $TimeoutSec -UseBasicParsing
}

function Invoke-Get([string]$Url, [int]$TimeoutSec = 15) {
  $ErrorActionPreference = "Stop"
  try {
    $response = Invoke-WebRequest -Uri $Url -Method GET -TimeoutSec $TimeoutSec -UseBasicParsing
    return $response
  } catch {
    $msg = if ($_.Exception.Message) { $_.Exception.Message } else { "Unknown error" }
    Write-Host "GET $Url failed: $msg" -ForegroundColor Red
    throw
  }
}

Write-Host "MYCA Production Smoke Test" -ForegroundColor White
Write-Host "DashboardUrl: $DashboardUrl"
Write-Host "MasUrl: $MasUrl"
Write-Host "N8nUrl: $N8nUrl"
Write-Host "ElevenLabsProxyUrl: $ElevenLabsProxyUrl"
Write-Host "RequireN8nWebhooks: $RequireN8nWebhooks"

Write-Section "Dashboard reachable"
$dash = Invoke-Get "$DashboardUrl/"
Assert-True ($dash.StatusCode -eq 200) "Dashboard returns HTTP 200"

Write-Section "Dashboard MYCA chat API"
# Health (GET should exist in our API routes)
try {
  $chatHealth = Invoke-Get "$DashboardUrl/api/myca/chat"
  Assert-True ($chatHealth.StatusCode -eq 200) "GET /api/myca/chat health returns 200"
} catch {
  Write-Host "WARN: GET /api/myca/chat health not available" -ForegroundColor Yellow
}

$chatResp = Invoke-JsonPost "$DashboardUrl/api/myca/chat" @{ message = "What is your name and how do you pronounce it?" }
Assert-True ($chatResp.StatusCode -eq 200) "POST /api/myca/chat returns 200"
$chatJson = $chatResp.Content | ConvertFrom-Json
Assert-True ($null -ne $chatJson) "Chat response is JSON"

# Basic contract: must contain text somewhere
$text = $chatJson.response_text
if (-not $text) { $text = $chatJson.text }
if (-not $text) { $text = $chatJson.message }
Assert-True ([string]::IsNullOrWhiteSpace($text) -eq $false) "Chat response contains text"
Assert-True ($text.ToLower().Contains("myca")) "Chat response mentions MYCA"
Assert-True ($text.ToLower().Contains("my-kah")) "Chat response includes pronunciation 'my-kah'"

Write-Section "Dashboard MYCA TTS API"
try {
  $ttsHealth = Invoke-Get "$DashboardUrl/api/myca/tts"
  Assert-True ($ttsHealth.StatusCode -eq 200) "GET /api/myca/tts health returns 200"
} catch {
  Write-Host "WARN: GET /api/myca/tts health not available" -ForegroundColor Yellow
}

$tts = Invoke-JsonPost "$DashboardUrl/api/myca/tts" @{ text = "Hello. I am MYCA, pronounced my-kah." }
Assert-True ($tts.StatusCode -eq 200) "POST /api/myca/tts returns 200"
Assert-True ($tts.Headers["Content-Type"] -match "^audio/") "TTS returns audio content-type"
Assert-True ($tts.RawContentLength -gt 1024) "TTS audio payload is non-trivial (>1KB)"

Write-Section "ElevenLabs proxy (optional)"
try {
  $proxy = Invoke-JsonPost "$ElevenLabsProxyUrl/v1/audio/speech" @{ model="tts-1"; voice="alloy"; input="Hello, I am MYCA." } 45
  Assert-True ($proxy.StatusCode -eq 200) "ElevenLabs proxy /v1/audio/speech returns 200"
  Assert-True ($proxy.Headers["Content-Type"] -match "^audio/") "ElevenLabs proxy returns audio"
} catch {
  Write-Host "WARN: ElevenLabs proxy check failed (may be down in this environment)" -ForegroundColor Yellow
}

Write-Section "MAS backend (optional)"
try {
  $masHealth = Invoke-Get "$MasUrl/health" 10
  Assert-True ($masHealth.StatusCode -eq 200) "MAS /health returns 200"
} catch {
  Write-Host "WARN: MAS /health not reachable at $MasUrl (may be different in prod)" -ForegroundColor Yellow
}

Write-Section "n8n (optional)"
if ($N8nApiKey) {
  try {
    $headers = @{ "X-N8N-API-KEY" = $N8nApiKey }
    $wf = Invoke-RestMethod -Uri "$N8nUrl/api/v1/workflows" -Method GET -Headers $headers -TimeoutSec 20
    Assert-True ($null -ne $wf) "n8n workflows API returns JSON"
    Assert-True (($wf.data | Measure-Object).Count -gt 0) "n8n instance contains workflows"
  } catch {
    throw "FAIL: n8n API check failed with provided API key"
  }
} else {
  Write-Host "INFO: N8nApiKey not provided; skipping n8n API workflow checks." -ForegroundColor Yellow
}

Write-Section "n8n webhook endpoints (optional)"
try {
  $jarvisUrl = "$N8nUrl/webhook/myca/jarvis"
  $req = Invoke-JsonPost $jarvisUrl @{ message="ping"; want_audio=$false } 20
  if ($RequireN8nWebhooks) {
    Assert-True ($req.StatusCode -eq 200) "n8n Jarvis webhook returns 200"
  } else {
    Write-Host "INFO: n8n Jarvis webhook returned $($req.StatusCode)" -ForegroundColor Yellow
  }
} catch {
  if ($RequireN8nWebhooks) { throw "FAIL: n8n webhook is required but not working." }
  Write-Host "WARN: n8n webhook not working (acceptable if dashboard uses fallbacks)" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "✅ Smoke test completed." -ForegroundColor Green

