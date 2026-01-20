# Check API Keys Configuration
# This script validates which API keys are configured in the environment

Write-Host "========================================"
Write-Host "Mycosoft API Keys Configuration Check"
Write-Host "========================================"
Write-Host ""

# Define required and optional keys
$requiredKeys = @(
    @{ Name = "NEXT_PUBLIC_SUPABASE_URL"; Description = "Supabase Project URL" },
    @{ Name = "NEXT_PUBLIC_SUPABASE_ANON_KEY"; Description = "Supabase Anon Key" },
    @{ Name = "NEXTAUTH_SECRET"; Description = "NextAuth Secret (for secure sessions)" },
    @{ Name = "NEXTAUTH_URL"; Description = "NextAuth URL (site URL)" }
)

$recommendedKeys = @(
    @{ Name = "SUPABASE_SERVICE_ROLE_KEY"; Description = "Supabase Service Role Key (server-side admin)" },
    @{ Name = "OPENAI_API_KEY"; Description = "OpenAI API Key (embeddings, AI features)" },
    @{ Name = "GOOGLE_CLIENT_ID"; Description = "Google OAuth Client ID" },
    @{ Name = "GOOGLE_CLIENT_SECRET"; Description = "Google OAuth Client Secret" },
    @{ Name = "GITHUB_CLIENT_ID"; Description = "GitHub OAuth Client ID" },
    @{ Name = "GITHUB_CLIENT_SECRET"; Description = "GitHub OAuth Client Secret" },
    @{ Name = "ANTHROPIC_API_KEY"; Description = "Anthropic/Claude API Key" },
    @{ Name = "NEXT_PUBLIC_GOOGLE_MAPS_API_KEY"; Description = "Google Maps API Key" }
)

$optionalKeys = @(
    @{ Name = "STRIPE_API_KEY"; Description = "Stripe API Key (payments)" },
    @{ Name = "TWILIO_ACCOUNT_SID"; Description = "Twilio Account SID" },
    @{ Name = "TWILIO_AUTH_TOKEN"; Description = "Twilio Auth Token" },
    @{ Name = "DISCORD_BOT_TOKEN"; Description = "Discord Bot Token" },
    @{ Name = "NOTION_API_KEY"; Description = "Notion API Key" },
    @{ Name = "AISSTREAM_API_KEY"; Description = "AIS Stream API Key (vessel tracking)" },
    @{ Name = "FLIGHTRADAR24_API_KEY"; Description = "FlightRadar24 API Key" }
)

function Check-Key {
    param([string]$KeyName, [string]$Description)
    
    $value = [Environment]::GetEnvironmentVariable($KeyName)
    if (-not $value) {
        # Try reading from .env file
        $envFile = Join-Path $PSScriptRoot "..\\.env"
        if (Test-Path $envFile) {
            $content = Get-Content $envFile -Raw
            if ($content -match "$KeyName=(.+)") {
                $value = $matches[1].Trim()
            }
        }
    }
    
    if ($value -and $value -notmatch "your_|placeholder|change_me|xxx|sk-1234") {
        Write-Host "  [OK] $KeyName" -ForegroundColor Green
        return $true
    } else {
        Write-Host "  [MISSING] $KeyName - $Description" -ForegroundColor Red
        return $false
    }
}

Write-Host "REQUIRED KEYS:" -ForegroundColor Yellow
Write-Host "--------------"
$requiredMissing = 0
foreach ($key in $requiredKeys) {
    if (-not (Check-Key -KeyName $key.Name -Description $key.Description)) {
        $requiredMissing++
    }
}

Write-Host ""
Write-Host "RECOMMENDED KEYS:" -ForegroundColor Yellow
Write-Host "-----------------"
$recommendedMissing = 0
foreach ($key in $recommendedKeys) {
    if (-not (Check-Key -KeyName $key.Name -Description $key.Description)) {
        $recommendedMissing++
    }
}

Write-Host ""
Write-Host "OPTIONAL KEYS:" -ForegroundColor Yellow
Write-Host "--------------"
$optionalMissing = 0
foreach ($key in $optionalKeys) {
    if (-not (Check-Key -KeyName $key.Name -Description $key.Description)) {
        $optionalMissing++
    }
}

Write-Host ""
Write-Host "========================================"
Write-Host "SUMMARY:"
Write-Host "========================================"
if ($requiredMissing -gt 0) {
    Write-Host "  Required keys missing: $requiredMissing" -ForegroundColor Red
    Write-Host "  ** Website may not function properly **" -ForegroundColor Red
} else {
    Write-Host "  All required keys configured!" -ForegroundColor Green
}

if ($recommendedMissing -gt 0) {
    Write-Host "  Recommended keys missing: $recommendedMissing" -ForegroundColor Yellow
}

if ($optionalMissing -gt 0) {
    Write-Host "  Optional keys missing: $optionalMissing" -ForegroundColor DarkGray
}

Write-Host ""
Write-Host "To configure keys:"
Write-Host "  1. Copy env.example to .env"
Write-Host "  2. Fill in the required values"
Write-Host "  3. Rebuild containers"
Write-Host ""
