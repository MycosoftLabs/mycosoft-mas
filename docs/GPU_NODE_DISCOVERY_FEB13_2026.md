# GPU Node Discovery - Desktop-T7NKNVS
**Date:** February 13, 2026  
**Purpose:** Pre-install discovery for Ubuntu GPU node conversion

## Target Hardware Summary

| Property | Value |
|----------|-------|
| Device Name | Desktop-T7NKNVS |
| CPU | Intel Core i7-7700K @ 4.2GHz (8 threads) |
| RAM | 16GB DDR4 |
| GPU | NVIDIA GeForce GTX 1080 Ti (11GB VRAM) |
| Storage | 2x 1TB drives (SATA assumed) |
| Network | LAN connected (Ubiquiti stack) |
| Current OS | Windows (to be replaced) |

## Discovery Commands (Run on Windows Before Wipe)

### 1. Network Information
```powershell
# Get IP, MAC, and adapter info
Get-NetAdapter | Where-Object Status -eq 'Up' | Select-Object Name, MacAddress, Status
Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.InterfaceAlias -notlike '*Loopback*' } | Select-Object InterfaceAlias, IPAddress, PrefixLength
Get-NetIPConfiguration | Select-Object InterfaceAlias, IPv4DefaultGateway
Get-DnsClientServerAddress -AddressFamily IPv4 | Select-Object InterfaceAlias, ServerAddresses
```

### 2. GPU Verification
```powershell
# Check GPU via WMI
Get-CimInstance Win32_VideoController | Select-Object Name, DriverVersion, AdapterRAM

# If nvidia-smi installed
nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv
```

### 3. Disk Layout
```powershell
# List all physical disks
Get-PhysicalDisk | Select-Object DeviceId, MediaType, Size, FriendlyName

# List partitions and volumes
Get-Disk | Select-Object Number, Size, PartitionStyle, OperationalStatus
Get-Volume | Where-Object DriveLetter | Select-Object DriveLetter, FileSystemLabel, Size, SizeRemaining
```

### 4. BIOS/UEFI Check
```powershell
# Confirm UEFI boot mode
$env:firmware_type
# Or:
bcdedit | Select-String "path"
# Look for "\EFI\" in the path = UEFI mode
```

## Discovered Values (CONFIRMED Feb 13, 2026)

| Property | Value |
|----------|-------|
| Primary NIC Name | Ethernet |
| **MAC Address** | **B0-6E-BF-31-8A-CA** |
| Current IP | 192.168.0.14 |
| Gateway | 192.168.0.1 |
| DNS Servers | 192.168.0.1 |
| Disk 0 Size | 932 GB (MBR) |
| Disk 1 Size | 932 GB (MBR) |
| OS Disk | Disk 0 (will be wiped + reformatted GPT) |
| Data to Preserve? | **NO - Safe to wipe both drives** |
| Current Boot Mode | Legacy (will switch to UEFI) |
| External 7.4TB | **UNPLUGGED - safe** |

## Planned Configuration

| Property | Planned Value |
|----------|---------------|
| Hostname | mycosoft-gpu01 |
| Username | mycosoft |
| Ubuntu Version | **22.04.4 LTS (Jammy) ✓ CONFIRMED** |
| Install Type | **Server/Headless (no GUI) ✓ CONFIRMED** |
| IP Strategy | DHCP reservation via UDM Pro Max |
| SSH Auth | Key-based only |
| GPU Driver | nvidia-driver-535 (or latest stable) |
| CUDA | 12.x via nvidia-container-toolkit |

## Phase Checklist

### Phase 0: Discovery
- [x] Confirm no data needs preservation on drives ✓ CONFIRMED Feb 13
- [ ] Record MAC address for DHCP reservation
- [ ] Confirm UEFI boot available
- [ ] Verify GTX 1080 Ti visible in Device Manager

### Phase 1: Network Planning
- [ ] Add DHCP reservation in UDM Pro Max (MAC → IP)
- [ ] Decide on IP address (e.g., 192.168.0.190)
- [ ] Add mycosoft-gpu01 to local DNS or hosts file

### Phase 2: Ubuntu Installation
- [ ] Create bootable USB (Ubuntu 22.04.4 Server ISO)
- [ ] BIOS: Enable UEFI, Disable Secure Boot, AHCI mode
- [ ] Install Ubuntu Server minimal
- [ ] Create user "mycosoft" with sudo
- [ ] Set hostname to "mycosoft-gpu01"
- [ ] Confirm network connectivity

### Phase 3: Post-Install Bootstrap
- [ ] Run bootstrap script
- [ ] Verify SSH from main PC
- [ ] Verify nvidia-smi shows GPU
- [ ] Verify Docker GPU access
- [ ] Disable password SSH login

### Phase 4: Integration
- [ ] Add to Mycosoft VM registry docs
- [ ] Test from Cursor Remote SSH
- [ ] Optional: Add monitoring agent

---

## Notes

- This machine will NOT run Proxmox — it's a standalone GPU compute node
- Future workloads: PersonaPlex/Moshi, Earth2, PhysicsNeMo
- RAM upgrade planned (16GB → 32GB+ later)
