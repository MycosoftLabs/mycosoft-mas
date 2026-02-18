#!/bin/bash
# =============================================================================
# Mycosoft GPU Node Bootstrap Script
# Target: Desktop-T7NKNVS → mycosoft-gpu01
# Date: February 13, 2026
# 
# Run this AFTER Ubuntu Server is installed and SSH is confirmed working.
# Execute as: sudo bash mycosoft-gpu-node-bootstrap.sh
# =============================================================================

set -e  # Exit on error

# Non-interactive mode for apt and needrestart
export DEBIAN_FRONTEND=noninteractive
export NEEDRESTART_MODE=a
export NEEDRESTART_SUSPEND=1

# Configure needrestart to auto-restart services (no prompts)
if [ -d /etc/needrestart/conf.d ]; then
    echo '$nrconf{restart} = "a";' > /etc/needrestart/conf.d/99-autorestart.conf
fi

# Parse arguments
AUTO_YES=false
AUTO_REBOOT=false
for arg in "$@"; do
    case $arg in
        -y|--yes)
            AUTO_YES=true
            ;;
        --reboot)
            AUTO_REBOOT=true
            ;;
    esac
done

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN} Mycosoft GPU Node Bootstrap${NC}"
echo -e "${GREEN} Target: mycosoft-gpu01${NC}"
echo -e "${GREEN}========================================${NC}"

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}Error: Please run as root (sudo)${NC}"
    exit 1
fi

# Confirm before proceeding
echo ""
echo -e "${YELLOW}This script will:${NC}"
echo "  1. Update system packages"
echo "  2. Install NVIDIA drivers (535 series)"
echo "  3. Install Docker with NVIDIA Container Toolkit"
echo "  4. Harden SSH (disable password auth after key confirmed)"
echo "  5. Configure firewall (UFW)"
echo "  6. Enable unattended-upgrades"
echo ""

if [ "$AUTO_YES" = false ]; then
    read -p "Continue? [y/N] " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Aborted."
        exit 1
    fi
else
    echo "Auto-yes mode enabled. Proceeding..."
fi

# =============================================================================
# PHASE 1: System Updates
# =============================================================================
echo -e "\n${GREEN}[1/6] Updating system packages...${NC}"
apt-get update -y
apt-get upgrade -y -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold"
apt-get autoremove -y

# =============================================================================
# PHASE 2: NVIDIA Drivers
# =============================================================================
echo -e "\n${GREEN}[2/6] Installing NVIDIA drivers...${NC}"

# Add NVIDIA driver PPA for latest stable drivers
apt install -y software-properties-common
add-apt-repository -y ppa:graphics-drivers/ppa
apt update

# Install NVIDIA driver 535 (well-tested for GTX 1080 Ti)
# Alternative: ubuntu-drivers autoinstall (picks recommended)
apt install -y nvidia-driver-535

# Install NVIDIA utilities
apt install -y nvidia-utils-535

echo -e "${YELLOW}Note: Reboot required after driver install. Will reboot at end.${NC}"

# =============================================================================
# PHASE 3: Docker + NVIDIA Container Toolkit
# =============================================================================
echo -e "\n${GREEN}[3/6] Installing Docker and NVIDIA Container Toolkit...${NC}"

# Install Docker prerequisites
apt install -y apt-transport-https ca-certificates curl gnupg lsb-release

# Add Docker GPG key and repo
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker
apt update
apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Add mycosoft user to docker group
usermod -aG docker mycosoft

# Install NVIDIA Container Toolkit
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
    sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
    tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

apt update
apt install -y nvidia-container-toolkit

# Configure Docker to use NVIDIA runtime
nvidia-ctk runtime configure --runtime=docker
systemctl restart docker

# =============================================================================
# PHASE 4: SSH Hardening
# =============================================================================
echo -e "\n${GREEN}[4/6] Configuring SSH...${NC}"

# Backup original config
cp /etc/ssh/sshd_config /etc/ssh/sshd_config.backup.$(date +%Y%m%d)

# Create hardened SSH config
cat > /etc/ssh/sshd_config.d/99-mycosoft-hardening.conf << 'EOF'
# Mycosoft SSH Hardening
# Applied: $(date)

# Disable password authentication (keys only)
# IMPORTANT: Uncomment ONLY after confirming key auth works!
# PasswordAuthentication no

# Disable root login
PermitRootLogin no

# Only allow mycosoft user
AllowUsers mycosoft

# Use strong ciphers
Ciphers chacha20-poly1305@openssh.com,aes256-gcm@openssh.com,aes128-gcm@openssh.com

# Idle timeout (10 minutes)
ClientAliveInterval 300
ClientAliveCountMax 2

# Disable X11 forwarding (no GUI)
X11Forwarding no

# Log level
LogLevel VERBOSE
EOF

echo -e "${YELLOW}SSH hardening applied but password auth still enabled.${NC}"
echo -e "${YELLOW}Run 'sudo nano /etc/ssh/sshd_config.d/99-mycosoft-hardening.conf'${NC}"
echo -e "${YELLOW}and uncomment 'PasswordAuthentication no' after confirming key auth.${NC}"

systemctl reload sshd

# =============================================================================
# PHASE 5: Firewall (UFW)
# =============================================================================
echo -e "\n${GREEN}[5/6] Configuring firewall...${NC}"

# Install UFW if not present
apt install -y ufw

# Default policies
ufw default deny incoming
ufw default allow outgoing

# Allow SSH
ufw allow ssh

# Allow from Mycosoft LAN only for other services (adjust as needed)
# Example: Allow Docker ports only from LAN
ufw allow from 192.168.0.0/24 to any port 8998 comment 'PersonaPlex'
ufw allow from 192.168.0.0/24 to any port 8999 comment 'PersonaPlex Bridge'
ufw allow from 192.168.0.0/24 to any port 8220 comment 'Earth2 API'
ufw allow from 192.168.0.0/24 to any port 8300 comment 'GPU Gateway'

# Enable UFW (force to avoid interactive prompt)
ufw --force enable
ufw status verbose

# =============================================================================
# PHASE 6: Unattended Upgrades
# =============================================================================
echo -e "\n${GREEN}[6/6] Enabling unattended security upgrades...${NC}"

apt install -y unattended-upgrades

# Enable automatic security updates
cat > /etc/apt/apt.conf.d/20auto-upgrades << 'EOF'
APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Unattended-Upgrade "1";
APT::Periodic::AutocleanInterval "7";
EOF

systemctl enable unattended-upgrades
systemctl start unattended-upgrades

# =============================================================================
# PHASE 7: Useful Tools
# =============================================================================
echo -e "\n${GREEN}[Bonus] Installing useful tools...${NC}"

apt install -y \
    htop \
    iotop \
    nvtop \
    tmux \
    git \
    curl \
    wget \
    net-tools \
    jq \
    python3-pip \
    python3-venv

# =============================================================================
# SUMMARY
# =============================================================================
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN} Bootstrap Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${YELLOW}IMPORTANT: Reboot required to load NVIDIA drivers${NC}"
echo ""
echo "After reboot, verify with these commands:"
echo ""
echo "  # Check NVIDIA driver"
echo "  nvidia-smi"
echo ""
echo "  # Check Docker GPU access"
echo "  docker run --rm --gpus all nvidia/cuda:12.2.0-base-ubuntu22.04 nvidia-smi"
echo ""
echo "  # Check services"
echo "  systemctl status docker"
echo "  systemctl status ssh"
echo "  ufw status"
echo ""
echo -e "${YELLOW}Don't forget to:${NC}"
echo "  1. Add your SSH public key to ~/.ssh/authorized_keys"
echo "  2. Test SSH with key auth"
echo "  3. Then disable password auth in /etc/ssh/sshd_config.d/99-mycosoft-hardening.conf"
echo ""

if [ "$AUTO_REBOOT" = true ]; then
    echo "Auto-reboot enabled. Rebooting in 5 seconds..."
    sleep 5
    reboot
elif [ "$AUTO_YES" = false ]; then
    read -p "Reboot now? [y/N] " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "Rebooting in 5 seconds..."
        sleep 5
        reboot
    fi
else
    echo "Skipping reboot. Run 'sudo reboot' when ready."
fi
