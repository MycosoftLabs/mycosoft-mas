# Ubuntu VM Post-Installation Guide

*Created: January 17, 2026*  
*For: VM 103 (mycosoft-sandbox) - Ubuntu Server 24.04.2 LTS*

---

## 📋 Table of Contents

1. [Initial System Access](#1-initial-system-access)
2. [System Update & Configuration](#2-system-update--configuration)
3. [Docker Installation](#3-docker-installation)
4. [User & Permissions Setup](#4-user--permissions-setup)
5. [Network Configuration](#5-network-configuration)
6. [Storage Configuration](#6-storage-configuration)
7. [Security Hardening](#7-security-hardening)
8. [Verification Checklist](#8-verification-checklist)

---

## 1. Initial System Access

### Get VM IP Address

After Ubuntu installation completes, find the IP address:

```bash
# From Proxmox console or after logging in
ip addr show
# or
hostname -I
```

### SSH Access from Windows

```powershell
# From your Windows machine
ssh mycosoft@<VM_IP_ADDRESS>

# Example
ssh mycosoft@192.168.0.XXX
```

### First Login Tasks

```bash
# Update password if needed
passwd

# Set timezone
sudo timedatectl set-timezone America/New_York

# Verify system info
hostnamectl
```

---

## 2. System Update & Configuration

### Full System Update

```bash
# Update package lists
sudo apt update

# Upgrade all packages
sudo apt upgrade -y

# Install essential packages
sudo apt install -y \
    curl \
    wget \
    git \
    vim \
    htop \
    net-tools \
    ca-certificates \
    gnupg \
    lsb-release \
    software-properties-common \
    apt-transport-https \
    jq \
    unzip \
    zip \
    tree \
    ncdu

# Clean up
sudo apt autoremove -y
sudo apt autoclean
```

### Set Hostname (if not already set)

```bash
sudo hostnamectl set-hostname mycosoft-sandbox
```

### Configure /etc/hosts

```bash
sudo tee -a /etc/hosts << EOF
127.0.0.1   mycosoft-sandbox
127.0.0.1   localhost
EOF
```

---

## 3. Docker Installation

### Install Docker Engine

```bash
# Remove old versions
sudo apt remove docker docker-engine docker.io containerd runc 2>/dev/null

# Add Docker's official GPG key
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

# Add Docker repository
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Update and install Docker
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

### Configure Docker

```bash
# Add current user to docker group
sudo usermod -aG docker $USER

# Enable Docker to start on boot
sudo systemctl enable docker
sudo systemctl enable containerd

# Start Docker
sudo systemctl start docker

# Verify installation
docker --version
docker compose version
```

### Docker Daemon Configuration

```bash
sudo tee /etc/docker/daemon.json << 'EOF'
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "50m",
    "max-file": "3"
  },
  "storage-driver": "overlay2",
  "live-restore": true,
  "default-address-pools": [
    {
      "base": "172.20.0.0/16",
      "size": 24
    }
  ]
}
EOF

# Restart Docker to apply changes
sudo systemctl restart docker
```

### Verify Docker Installation

```bash
# Run test container
docker run hello-world

# Check Docker status
sudo systemctl status docker
```

---

## 4. User & Permissions Setup

### Create Mycosoft Directory Structure

```bash
# Create main directories
sudo mkdir -p /opt/mycosoft/{website,mas,data,backups,logs,secrets}
sudo mkdir -p /opt/mycosoft/data/{postgres,redis,minio,grafana,prometheus}

# Set ownership
sudo chown -R $USER:$USER /opt/mycosoft

# Set permissions
chmod -R 755 /opt/mycosoft
chmod 700 /opt/mycosoft/secrets
```

### Create Service User (Optional)

```bash
# Create dedicated service user
sudo useradd -r -s /bin/false -d /opt/mycosoft mycosoft-svc

# Add to docker group
sudo usermod -aG docker mycosoft-svc
```

---

## 5. Network Configuration

### Configure UFW Firewall

```bash
# Install UFW if not present
sudo apt install -y ufw

# Default policies
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Allow SSH
sudo ufw allow 22/tcp

# Allow HTTP/HTTPS (for website and Cloudflare tunnel)
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Allow Docker container ports (internal network only)
# These are for local development - Cloudflare tunnel will handle external access
sudo ufw allow from 192.168.0.0/24 to any port 3000  # Website
sudo ufw allow from 192.168.0.0/24 to any port 5678  # n8n
sudo ufw allow from 192.168.0.0/24 to any port 8000  # MINDEX API
sudo ufw allow from 192.168.0.0/24 to any port 8001  # MAS Orchestrator
sudo ufw allow from 192.168.0.0/24 to any port 8003  # MycoBrain
sudo ufw allow from 192.168.0.0/24 to any port 3002  # Grafana
sudo ufw allow from 192.168.0.0/24 to any port 9090  # Prometheus

# Enable firewall
sudo ufw enable

# Check status
sudo ufw status verbose
```

### Static IP Configuration (Optional)

If you need a static IP, edit netplan:

```bash
sudo nano /etc/netplan/00-installer-config.yaml
```

Example configuration:
```yaml
network:
  version: 2
  renderer: networkd
  ethernets:
    ens18:
      addresses:
        - 192.168.0.103/24
      routes:
        - to: default
          via: 192.168.0.1
      nameservers:
        addresses:
          - 8.8.8.8
          - 8.8.4.4
```

Apply changes:
```bash
sudo netplan apply
```

---

## 6. Storage Configuration

### Check Available Storage

```bash
# View disk usage
df -h

# View block devices
lsblk

# Check LVM status
sudo lvs
sudo vgs
sudo pvs
```

### Expand LVM if Needed

If your root partition isn't using all available space:

```bash
# Extend LVM to use all available space
sudo lvextend -l +100%FREE /dev/ubuntu-vg/ubuntu-lv

# Resize filesystem
sudo resize2fs /dev/ubuntu-vg/ubuntu-lv

# Verify
df -h /
```

### NAS Mount (For Data Volumes)

```bash
# Install NFS client
sudo apt install -y nfs-common

# Create mount point
sudo mkdir -p /mnt/nas/mycosoft

# Add to fstab for persistent mount
# Replace with your NAS IP and share path
echo "192.168.0.XX:/volume1/mycosoft /mnt/nas/mycosoft nfs defaults,_netdev 0 0" | sudo tee -a /etc/fstab

# Mount now
sudo mount -a

# Verify
df -h | grep nas
```

---

## 7. Security Hardening

### SSH Configuration

```bash
sudo nano /etc/ssh/sshd_config
```

Recommended settings:
```
# Disable root login
PermitRootLogin no

# Disable password authentication (after setting up SSH keys)
# PasswordAuthentication no

# Limit SSH to specific user
AllowUsers mycosoft

# Change default port (optional)
# Port 2222
```

Apply changes:
```bash
sudo systemctl restart sshd
```

### Install Fail2ban

```bash
sudo apt install -y fail2ban

# Create local configuration
sudo cp /etc/fail2ban/jail.conf /etc/fail2ban/jail.local

# Enable and start
sudo systemctl enable fail2ban
sudo systemctl start fail2ban

# Check status
sudo fail2ban-client status
```

### Automatic Security Updates

```bash
sudo apt install -y unattended-upgrades
sudo dpkg-reconfigure -plow unattended-upgrades
```

---

## 8. Verification Checklist

Run these commands to verify the system is ready:

```bash
echo "=== System Information ==="
hostnamectl

echo -e "\n=== Network ==="
ip addr show | grep inet
hostname -I

echo -e "\n=== Docker ==="
docker --version
docker compose version
docker ps

echo -e "\n=== Storage ==="
df -h

echo -e "\n=== Memory ==="
free -h

echo -e "\n=== CPU ==="
nproc
cat /proc/cpuinfo | grep "model name" | head -1

echo -e "\n=== Firewall ==="
sudo ufw status

echo -e "\n=== Services ==="
sudo systemctl status docker --no-pager
```

### Expected Output

| Check | Expected |
|-------|----------|
| Hostname | `mycosoft-sandbox` |
| IP Address | `192.168.0.XXX` |
| Docker Version | `24.x` or higher |
| Docker Compose | `v2.x` or higher |
| Available Disk | `200+ GB` free |
| Available RAM | `30+ GB` available |
| CPU Cores | `8` cores |

---

## 🎯 Next Steps

Once all checks pass, proceed to:

1. **[MYCOSOFT_STACK_DEPLOYMENT.md](MYCOSOFT_STACK_DEPLOYMENT.md)** - Deploy all containers
2. **[CLOUDFLARE_TUNNEL_SETUP.md](CLOUDFLARE_TUNNEL_SETUP.md)** - Configure public access

---

*Document Version: 1.0*  
*Last Updated: January 17, 2026*
