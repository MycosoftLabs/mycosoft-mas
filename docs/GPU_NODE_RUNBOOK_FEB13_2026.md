# GPU Node Installation Runbook
**Date:** February 13, 2026  
**Target Machine:** Desktop-T7NKNVS → mycosoft-gpu01  
**Author:** Cursor Agent for Morgan Rockwell

---

## Table of Contents
1. [Pre-Installation Checklist](#pre-installation-checklist)
2. [Phase 0: Discovery](#phase-0-discovery)
3. [Phase 1: Network Planning](#phase-1-network-planning)
4. [Phase 2: Ubuntu Installation](#phase-2-ubuntu-installation)
5. [Phase 3: Post-Install Bootstrap](#phase-3-post-install-bootstrap)
6. [Phase 4: Verification](#phase-4-verification)
7. [Phase 5: SSH Finalization](#phase-5-ssh-finalization)
8. [Troubleshooting](#troubleshooting)

---

## Pre-Installation Checklist

### Required Items
- [ ] USB flash drive (8GB+ minimum)
- [ ] Keyboard + monitor connected to Desktop-T7NKNVS
- [ ] Network cable connected
- [ ] Ubuntu 22.04.4 Server ISO downloaded
- [ ] SSH public key from main PC ready

### Critical Confirmations (DO NOT PROCEED WITHOUT)
- [ ] **DATA CONFIRMED SAFE TO WIPE** — No data on either 1TB drive needs preservation
- [ ] MAC address recorded for DHCP reservation
- [ ] IP address decided and reserved in UDM Pro Max

---

## Phase 0: Discovery

### Step 0.1: Run Discovery Commands on Windows

Open PowerShell as Administrator and run:

```powershell
# Network info
Write-Host "=== NETWORK ===" -ForegroundColor Green
Get-NetAdapter | Where-Object Status -eq 'Up' | Format-Table Name, MacAddress, Status
Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.InterfaceAlias -notlike '*Loopback*' } | Format-Table InterfaceAlias, IPAddress

# GPU
Write-Host "=== GPU ===" -ForegroundColor Green
Get-CimInstance Win32_VideoController | Format-Table Name, DriverVersion

# Disks
Write-Host "=== DISKS ===" -ForegroundColor Green
Get-Disk | Format-Table Number, Size, PartitionStyle
Get-Volume | Where-Object DriveLetter | Format-Table DriveLetter, FileSystemLabel, @{N='SizeGB';E={[math]::Round($_.Size/1GB,1)}}

# Boot mode
Write-Host "=== BOOT MODE ===" -ForegroundColor Green
$env:firmware_type
```

### Step 0.2: Record Results

Fill in this table:

| Property | Value |
|----------|-------|
| MAC Address | __________________ |
| Current IP | __________________ |
| Gateway | 192.168.0.1 (assumed) |
| Disk 0 Size | __________________ |
| Disk 1 Size | __________________ |
| Boot Mode | UEFI / Legacy |

### Step 0.3: Confirm Data Safety

**STOP HERE** and confirm with Morgan:
> "Both 1TB drives can be completely wiped. No data preservation needed."

- [ ] **CONFIRMED** — Proceed to Phase 1

---

## Phase 1: Network Planning

### Step 1.1: DHCP Reservation in UDM Pro Max

1. Log into UDM Pro Max controller
2. Go to **Settings → Networks → your LAN → DHCP**
3. Add a **Static IP Assignment**:
   - MAC Address: `[from discovery]`
   - IP Address: `192.168.0.190` (or your chosen IP)
   - Name: `mycosoft-gpu01`

### Step 1.2: Decide Final Configuration

| Property | Value |
|----------|-------|
| Hostname | mycosoft-gpu01 |
| IP Address | 192.168.0.190 |
| Gateway | 192.168.0.1 |
| DNS | 192.168.0.1 (or 1.1.1.1, 8.8.8.8) |
| Subnet | 255.255.255.0 (/24) |
| Username | mycosoft |

### Step 1.3: Prepare SSH Key on Main PC

On Morgan's main computer, ensure SSH key exists:

```powershell
# Check if key exists
Test-Path $env:USERPROFILE\.ssh\id_ed25519.pub

# If not, generate one:
ssh-keygen -t ed25519 -C "morgan@mycosoft.com"

# Copy the public key (you'll paste this later)
Get-Content $env:USERPROFILE\.ssh\id_ed25519.pub | Set-Clipboard
Write-Host "Public key copied to clipboard"
```

### Step 1.4: Add hosts entry (optional, for immediate access)

On main PC, add to `C:\Windows\System32\drivers\etc\hosts`:
```
192.168.0.190    mycosoft-gpu01
```

---

## Phase 2: Ubuntu Installation

### Step 2.1: Create Bootable USB

On any computer with internet:

1. Download Ubuntu Server 22.04.4 LTS ISO:
   - https://releases.ubuntu.com/22.04/ubuntu-22.04.4-live-server-amd64.iso

2. Download Rufus (Windows) or Balena Etcher:
   - Rufus: https://rufus.ie/
   - Etcher: https://etcher.balena.io/

3. Flash the ISO to USB:
   - **Rufus settings:**
     - Partition scheme: **GPT**
     - Target system: **UEFI (non CSM)**
     - File system: FAT32
     - Click START

### Step 2.2: BIOS Configuration

1. Insert USB into Desktop-T7NKNVS
2. Power on and press **DEL** or **F2** repeatedly to enter BIOS
3. Configure these settings:

| Setting | Value | Notes |
|---------|-------|-------|
| Boot Mode | UEFI | Not Legacy/CSM |
| Secure Boot | **Disabled** | Required for NVIDIA drivers |
| SATA Mode | AHCI | Not RAID |
| Boot Priority | USB First | Temporarily |

4. Save and exit (usually F10)

### Step 2.3: Install Ubuntu Server

The system will boot from USB into the Ubuntu installer.

**Installation choices:**

| Screen | Selection |
|--------|-----------|
| Language | English |
| Keyboard | US (or your preference) |
| Install type | **Ubuntu Server (minimized)** |
| Network | Use DHCP (will get reserved IP) |
| Proxy | Leave empty |
| Mirror | Default (archive.ubuntu.com) |
| Storage | **Use entire disk** on primary 1TB |
| Storage layout | Use LVM if you want flexibility |
| Profile setup | See below |
| SSH | **Install OpenSSH server** ✓ |
| Featured snaps | Skip all |

**Profile setup:**
| Field | Value |
|-------|-------|
| Your name | Mycosoft GPU Node |
| Server name | mycosoft-gpu01 |
| Username | mycosoft |
| Password | [your secure password] |

### Step 2.4: Complete Installation

1. Wait for installation to complete (~5-10 minutes)
2. When prompted, **remove USB drive**
3. Press Enter to reboot
4. System boots into Ubuntu

### Step 2.5: First Login and Network Confirm

Log in at the console with username `mycosoft` and your password.

```bash
# Check network
ip addr show
# Look for your IP (should be 192.168.0.190 if DHCP reservation worked)

# Check internet
ping -c 3 google.com

# Check hostname
hostname
# Should show: mycosoft-gpu01
```

---

## Phase 3: Post-Install Bootstrap

### Step 3.1: Test SSH from Main PC

From Morgan's main computer:

```powershell
# Test SSH connection
ssh mycosoft@192.168.0.190
# Or if hosts entry added:
ssh mycosoft@mycosoft-gpu01
```

If this works, you now have remote access! The rest can be done over SSH.

### Step 3.2: Copy SSH Public Key

From main PC:

```powershell
# Copy your public key to the GPU node
type $env:USERPROFILE\.ssh\id_ed25519.pub | ssh mycosoft@mycosoft-gpu01 "mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys && chmod 700 ~/.ssh"
```

Test key-based login:
```powershell
ssh mycosoft@mycosoft-gpu01
# Should NOT prompt for password if key works
```

### Step 3.3: Transfer Bootstrap Script

Option A - Copy via SCP:
```powershell
# From MAS repo directory
scp scripts/gpu-node/mycosoft-gpu-node-bootstrap.sh mycosoft@mycosoft-gpu01:~/
```

Option B - Create directly on server:
```bash
# SSH into the server, then:
nano ~/mycosoft-gpu-node-bootstrap.sh
# Paste the script contents
# Save with Ctrl+O, exit with Ctrl+X
```

### Step 3.4: Run Bootstrap Script

```bash
# On the GPU node (via SSH)
cd ~
chmod +x mycosoft-gpu-node-bootstrap.sh
sudo ./mycosoft-gpu-node-bootstrap.sh
```

The script will:
1. Update all packages
2. Install NVIDIA driver 535
3. Install Docker + NVIDIA Container Toolkit
4. Configure SSH hardening
5. Set up UFW firewall
6. Enable unattended-upgrades
7. Prompt for reboot

**Say YES to reboot when prompted.**

---

## Phase 4: Verification

After reboot, SSH back in and run these verification commands:

### Step 4.1: NVIDIA Driver Check

```bash
nvidia-smi
```

**Expected output:**
```
+-----------------------------------------------------------------------------+
| NVIDIA-SMI 535.xxx.xx    Driver Version: 535.xxx.xx    CUDA Version: 12.x   |
|-------------------------------+----------------------+----------------------+
| GPU  Name        Persistence-M| Bus-Id        Disp.A | Volatile Uncorr. ECC |
| Fan  Temp  Perf  Pwr:Usage/Cap|         Memory-Usage | GPU-Util  Compute M. |
|===============================+======================+======================|
|   0  NVIDIA GeForce ...  Off  | 00000000:XX:00.0 Off |                  N/A |
|  0%   35C    P8    10W / 250W |      0MiB / 11264MiB |      0%      Default |
+-------------------------------+----------------------+----------------------+
```

### Step 4.2: Docker Check

```bash
# Check Docker is running
sudo systemctl status docker

# Check your user can run docker
docker ps

# Check NVIDIA container runtime
docker info | grep -i nvidia
```

### Step 4.3: Docker GPU Test

```bash
# Run NVIDIA CUDA container with GPU access
docker run --rm --gpus all nvidia/cuda:12.2.0-base-ubuntu22.04 nvidia-smi
```

**Expected:** Same nvidia-smi output as above, but from inside a container.

### Step 4.4: Firewall Check

```bash
sudo ufw status verbose
```

**Expected:**
```
Status: active
Logging: on (low)
Default: deny (incoming), allow (outgoing), disabled (routed)

To                         Action      From
--                         ------      ----
22/tcp                     ALLOW IN    Anywhere
8998                       ALLOW IN    192.168.0.0/24
8999                       ALLOW IN    192.168.0.0/24
...
```

### Step 4.5: System Resources

```bash
# Check memory
free -h

# Check disk space
df -h

# GPU monitoring (live)
nvtop
# Press 'q' to exit
```

---

## Phase 5: SSH Finalization

### Step 5.1: Confirm Key-Based SSH Works

From main PC, verify you can SSH without password:

```powershell
ssh mycosoft@mycosoft-gpu01
# Should connect immediately without password prompt
```

### Step 5.2: Disable Password Authentication

**ONLY DO THIS AFTER CONFIRMING KEY AUTH WORKS!**

On the GPU node:

```bash
sudo nano /etc/ssh/sshd_config.d/99-mycosoft-hardening.conf
```

Find and uncomment this line:
```
PasswordAuthentication no
```

Save and reload SSH:
```bash
sudo systemctl reload sshd
```

### Step 5.3: Test Password is Disabled

Try to force password auth (should fail):

```powershell
ssh -o PreferredAuthentications=password mycosoft@mycosoft-gpu01
# Should say: Permission denied (publickey)
```

---

## Verification Checklist

Run through this checklist to confirm everything works:

| Test | Command | Expected | Status |
|------|---------|----------|--------|
| SSH connection | `ssh mycosoft@mycosoft-gpu01` | Connects without password | [ ] |
| Hostname | `hostname` | mycosoft-gpu01 | [ ] |
| IP address | `ip -4 addr show` | 192.168.0.190 | [ ] |
| NVIDIA driver | `nvidia-smi` | Shows GTX 1080 Ti | [ ] |
| Docker running | `docker ps` | No errors | [ ] |
| Docker GPU | `docker run --rm --gpus all nvidia/cuda:12.2.0-base-ubuntu22.04 nvidia-smi` | Shows GPU | [ ] |
| Firewall active | `sudo ufw status` | Status: active | [ ] |
| Password auth disabled | `ssh -o PreferredAuthentications=password ...` | Permission denied | [ ] |

---

## Troubleshooting

### NVIDIA driver not loading
```bash
# Check if driver is installed
dpkg -l | grep nvidia

# Check for errors
dmesg | grep -i nvidia
sudo journalctl -b | grep -i nvidia

# Try reinstalling
sudo apt purge nvidia-*
sudo apt autoremove
sudo ubuntu-drivers autoinstall
sudo reboot
```

### Docker can't access GPU
```bash
# Check nvidia-container-toolkit
dpkg -l | grep nvidia-container

# Reconfigure runtime
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
```

### SSH connection refused
```bash
# On the server (at console)
sudo systemctl status sshd
sudo systemctl start sshd

# Check firewall isn't blocking
sudo ufw status
sudo ufw allow ssh
```

### Network not working after install
```bash
# Check network config
cat /etc/netplan/*.yaml

# Apply network changes
sudo netplan apply

# Check if DHCP working
sudo dhclient -v
```

---

## Post-Setup: Integration with Mycosoft

Once verified, update these documents:

1. **Add to VM registry:** `docs/SYSTEM_REGISTRY_FEB04_2026.md`
   ```
   | mycosoft-gpu01 | 192.168.0.190 | GPU Compute Node | PersonaPlex, Earth2 |
   ```

2. **Add to hosts on all VMs** (optional):
   ```
   192.168.0.190    mycosoft-gpu01
   ```

3. **Test from other nodes:**
   ```bash
   # From MAS VM (192.168.0.188)
   ssh mycosoft@192.168.0.190 nvidia-smi
   ```

---

## Future Tasks (Out of Scope for This Runbook)

- [ ] Mount second 1TB drive as /data
- [ ] Deploy PersonaPlex container
- [ ] Deploy Earth2 inference service
- [ ] Set up monitoring (Prometheus node exporter)
- [ ] Configure VS Code / Cursor Remote SSH
- [ ] RAM upgrade (16GB → 32GB+)

---

## Summary

| Item | Value |
|------|-------|
| Hostname | mycosoft-gpu01 |
| IP | 192.168.0.190 |
| User | mycosoft |
| GPU | NVIDIA GeForce GTX 1080 Ti (11GB) |
| OS | Ubuntu 22.04.4 LTS Server |
| Docker | Yes, with NVIDIA runtime |
| SSH | Key-based only |
| Firewall | UFW active |

**Access:** `ssh mycosoft@mycosoft-gpu01`
