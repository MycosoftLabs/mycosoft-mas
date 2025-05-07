# Script to install npm with administrator privileges
$tempScript = Join-Path $env:TEMP "install_npm_elevated.ps1"
@"
# Set execution policy
Set-ExecutionPolicy Bypass -Scope Process -Force
Set-ExecutionPolicy Bypass -Scope CurrentUser -Force

# Install Node.js and npm
Write-Host "Installing Node.js and npm..."
choco install nodejs -y --force
refreshenv

# Verify npm installation
Write-Host "Verifying npm installation..."
npm --version
node --version

# Install global npm packages
Write-Host "Installing global npm packages..."
npm install -g npm@latest
npm install -g typescript
npm install -g @angular/cli
npm install -g create-react-app
npm install -g next
npm install -g yarn

# Verify installations
Write-Host "`nVerifying all installations:"
npm --version
node --version
tsc --version
ng --version
next --version
yarn --version

Write-Host "`nNPM installation completed!"
"@ | Out-File -FilePath $tempScript -Encoding UTF8

# Run the script with elevated privileges
Start-Process powershell -Verb RunAs -ArgumentList "-NoProfile -ExecutionPolicy Bypass -File `"$tempScript`""

# Clean up
Start-Sleep -Seconds 2
Remove-Item $tempScript -Force 