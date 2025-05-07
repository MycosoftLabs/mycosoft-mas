Write-Host "Checking Virtualization Status..."
Write-Host "------------------------------"

$computerInfo = Get-ComputerInfo | Select-Object -Property HyperV*

Write-Host "HyperVisor Present: $($computerInfo.HyperVisorPresent)"
Write-Host "Virtualization Firmware Enabled: $($computerInfo.HyperVRequirementVirtualizationFirmwareEnabled)"
Write-Host "VMMonitorMode Extensions: $($computerInfo.HyperVRequirementVMMonitorModeExtensions)"

if ($computerInfo.HyperVRequirementVirtualizationFirmwareEnabled) {
    Write-Host "`nVirtualization is properly enabled in BIOS!" -ForegroundColor Green
} else {
    Write-Host "`nVirtualization is NOT enabled in BIOS. Please follow these steps:" -ForegroundColor Red
    Write-Host "1. Restart your computer"
    Write-Host "2. Press Delete or F2 during startup to enter BIOS"
    Write-Host "3. Navigate to Advanced > CPU Configuration"
    Write-Host "4. Enable 'Intel Virtualization Technology (VT-x)'"
    Write-Host "5. Save changes and exit BIOS"
} 