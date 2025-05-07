# Create a temporary script that will run with elevated privileges
$tempScript = Join-Path $env:TEMP "run_setup_elevated.ps1"
@"
# Set execution policy
Set-ExecutionPolicy Bypass -Scope Process -Force
Set-ExecutionPolicy Bypass -Scope CurrentUser -Force

# Run the setup script
cd '$PWD'
.\setup_all.ps1
"@ | Out-File -FilePath $tempScript -Encoding UTF8

# Run the script with elevated privileges
Start-Process powershell -Verb RunAs -ArgumentList "-NoProfile -ExecutionPolicy Bypass -File `"$tempScript`""

# Clean up
Start-Sleep -Seconds 2
Remove-Item $tempScript -Force 