# Generate NEXTAUTH_SECRET for secure session cookies
# Run this script and add the output to your .env file

$bytes = New-Object byte[] 32
$rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
$rng.GetBytes($bytes)
$secret = [Convert]::ToBase64String($bytes)

Write-Host "========================================"
Write-Host "NEXTAUTH_SECRET Generated:"
Write-Host "========================================"
Write-Host ""
Write-Host "NEXTAUTH_SECRET=$secret"
Write-Host ""
Write-Host "========================================"
Write-Host "Add this to your .env file on the VM:"
Write-Host "  /home/mycosoft/mycosoft/mas/.env"
Write-Host ""
Write-Host "Then rebuild the website container:"
Write-Host "  docker compose -f docker-compose.always-on.yml up -d --no-deps --force-recreate mycosoft-website"
Write-Host "========================================"

# Also output to clipboard if possible
try {
    Set-Clipboard -Value "NEXTAUTH_SECRET=$secret"
    Write-Host ""
    Write-Host "(Copied to clipboard)"
} catch {
    # Clipboard not available
}
