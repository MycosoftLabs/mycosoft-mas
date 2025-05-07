# Install Azure CLI if not present
if (-not (Get-Command az -ErrorAction SilentlyContinue)) {
    Write-Host "Azure CLI not found. Installing..."
    Invoke-WebRequest -Uri https://aka.ms/installazurecliwindows -OutFile .\AzureCLI.msi
    Start-Process msiexec.exe -Wait -ArgumentList '/I AzureCLI.msi /quiet'
    Remove-Item .\AzureCLI.msi
    Write-Host "Azure CLI installed. Please restart your PowerShell session and re-run this script."
    exit
}

# Login to Azure (if not already)
az account show 2>$null
if ($LASTEXITCODE -ne 0) {
    az login
}

# Variables
$ResourceGroup = "mas-rg"
$Location = "eastus"
$VMName = "mas-vm"
$AdminUser = "azureuser"
$VMSize = "Standard_D4s_v3"
$Image = "UbuntuLTS"

# Create resource group
az group create --name $ResourceGroup --location $Location

# Create VM
az vm create `
  --resource-group $ResourceGroup `
  --name $VMName `
  --image $Image `
  --size $VMSize `
  --admin-username $AdminUser `
  --generate-ssh-keys `
  --public-ip-sku Standard

# Open ports
az vm open-port --port 22 --resource-group $ResourceGroup --name $VMName
az vm open-port --port 80 --resource-group $ResourceGroup --name $VMName
az vm open-port --port 443 --resource-group $ResourceGroup --name $VMName

# Get public IP
$VMIP = az vm show -d -g $ResourceGroup -n $VMName --query publicIps -o tsv
Write-Host "VM Public IP: $VMIP"
Write-Host "SSH into your VM: ssh $AdminUser@$VMIP"
Write-Host "Then run the MAS setup script provided earlier." 