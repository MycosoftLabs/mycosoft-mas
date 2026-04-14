#Requires -Version 5.1
# Run on Windows after WSL Ubuntu works; requires zstd: wsl -u root -e apt-get install -y zstd
$ErrorActionPreference = 'Stop'
$distro = 'Ubuntu'
Write-Host "Installing Ollama inside WSL ($distro)..."
wsl -d $distro -u root -e bash -c "curl -fsSL https://ollama.com/install.sh | bash"
Write-Host "Done. Run: wsl -d $distro -u root -e ollama --version"
