#!/bin/bash
#
# Mycosoft VM Setup Script
# This script automates the post-installation setup of a Mycosoft VM
#
# Usage: curl -sSL https://raw.githubusercontent.com/MYCOSOFT/mycosoft-mas/main/scripts/setup-vm.sh | bash
# Or: ./setup-vm.sh
#
# Created: January 17, 2026
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
MYCOSOFT_DIR="/opt/mycosoft"
MYCOSOFT_USER="${USER}"

echo -e "${BLUE}"
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║                                                               ║"
echo "║            MYCOSOFT VM SETUP SCRIPT                          ║"
echo "║                                                               ║"
echo "║  This script will:                                           ║"
echo "║  1. Update the system                                        ║"
echo "║  2. Install Docker and Docker Compose                        ║"
echo "║  3. Create directory structure                               ║"
echo "║  4. Set up helper scripts                                    ║"
echo "║                                                               ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    echo -e "${RED}Please do not run this script as root.${NC}"
    echo "Run as your regular user; the script will use sudo when needed."
    exit 1
fi

# Confirm
read -p "Continue with setup? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Setup cancelled."
    exit 0
fi

echo -e "\n${YELLOW}[1/6] Updating system packages...${NC}"
sudo apt update
sudo apt upgrade -y
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
    ncdu \
    fail2ban \
    ufw

echo -e "\n${YELLOW}[2/6] Installing Docker...${NC}"

# Remove old Docker versions
sudo apt remove docker docker-engine docker.io containerd runc 2>/dev/null || true

# Add Docker GPG key
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

# Add Docker repository
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Add user to docker group
sudo usermod -aG docker $USER

# Configure Docker daemon
sudo mkdir -p /etc/docker
sudo tee /etc/docker/daemon.json << 'DOCKERCONFIG'
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "50m",
    "max-file": "3"
  },
  "storage-driver": "overlay2",
  "live-restore": true
}
DOCKERCONFIG

# Enable and start Docker
sudo systemctl enable docker
sudo systemctl enable containerd
sudo systemctl restart docker

echo -e "\n${YELLOW}[3/6] Creating directory structure...${NC}"

# Create main directories
sudo mkdir -p ${MYCOSOFT_DIR}/{website,mas,data,backups,logs,secrets,scripts}
sudo mkdir -p ${MYCOSOFT_DIR}/data/{postgres,redis,minio,grafana,prometheus}
sudo mkdir -p ${MYCOSOFT_DIR}/backups/{postgres,volumes}
sudo mkdir -p ${MYCOSOFT_DIR}/cloudflared

# Set ownership
sudo chown -R ${MYCOSOFT_USER}:${MYCOSOFT_USER} ${MYCOSOFT_DIR}
chmod 700 ${MYCOSOFT_DIR}/secrets

echo -e "\n${YELLOW}[4/6] Creating helper scripts...${NC}"

# Health check script
cat > ${MYCOSOFT_DIR}/scripts/health-check.sh << 'HEALTHSCRIPT'
#!/bin/bash
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

echo "=========================================="
echo "Mycosoft System Health Check"
echo "$(date)"
echo "=========================================="

check_service() {
    local name=$1
    local url=$2
    local response=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "$url" 2>/dev/null)
    if [ "$response" = "200" ] || [ "$response" = "204" ]; then
        echo -e "[$GREEN✓$NC] $name"
        return 0
    else
        echo -e "[$RED✗$NC] $name (HTTP $response)"
        return 1
    fi
}

echo -e "\n--- Services ---"
check_service "Website" "http://localhost:3000/api/health" 2>/dev/null || echo "  Not running"
check_service "MINDEX API" "http://localhost:8000/health" 2>/dev/null || echo "  Not running"
check_service "n8n" "http://localhost:5678/healthz" 2>/dev/null || echo "  Not running"
check_service "Grafana" "http://localhost:3002/api/health" 2>/dev/null || echo "  Not running"

echo -e "\n--- Containers ---"
docker ps --format "table {{.Names}}\t{{.Status}}" 2>/dev/null | head -15

echo -e "\n--- Resources ---"
echo "Disk: $(df -h / | awk 'NR==2 {print $5 " used of " $2}')"
echo "Memory: $(free -h | awk 'NR==2 {print $3 " used of " $2}')"
echo "CPU: $(nproc) cores"

echo -e "\n=========================================="
HEALTHSCRIPT
chmod +x ${MYCOSOFT_DIR}/scripts/health-check.sh

# Start all script
cat > ${MYCOSOFT_DIR}/scripts/start-all.sh << 'STARTSCRIPT'
#!/bin/bash
set -e
echo "Starting Mycosoft Stack..."

cd /opt/mycosoft/mas
docker compose -f docker-compose.always-on.yml up -d 2>/dev/null || echo "Always-on stack not configured"
sleep 5
docker compose up -d 2>/dev/null || echo "MAS stack not configured"

cd /opt/mycosoft/website
docker compose up -d 2>/dev/null || echo "Website stack not configured"

echo "All services started!"
/opt/mycosoft/scripts/health-check.sh
STARTSCRIPT
chmod +x ${MYCOSOFT_DIR}/scripts/start-all.sh

# Stop all script
cat > ${MYCOSOFT_DIR}/scripts/stop-all.sh << 'STOPSCRIPT'
#!/bin/bash
echo "Stopping Mycosoft Stack..."

cd /opt/mycosoft/website
docker compose down 2>/dev/null || true

cd /opt/mycosoft/mas
docker compose down 2>/dev/null || true
docker compose -f docker-compose.always-on.yml down 2>/dev/null || true

echo "All services stopped."
STOPSCRIPT
chmod +x ${MYCOSOFT_DIR}/scripts/stop-all.sh

# Database backup script
cat > ${MYCOSOFT_DIR}/scripts/backup-database.sh << 'BACKUPSCRIPT'
#!/bin/bash
set -e
BACKUP_DIR="/opt/mycosoft/backups/postgres"
DATE=$(date +%Y%m%d_%H%M%S)

echo "=== Database Backup $(date) ==="

for db in mycosoft_mas mindex website n8n; do
    if docker exec mycosoft-postgres psql -U mycosoft -d $db -c '\q' 2>/dev/null; then
        echo "Backing up $db..."
        docker exec mycosoft-postgres pg_dump -U mycosoft -d $db | gzip > "$BACKUP_DIR/${db}_${DATE}.sql.gz"
    fi
done

find $BACKUP_DIR -name "*.sql.gz" -mtime +7 -delete 2>/dev/null || true
echo "Backup complete!"
BACKUPSCRIPT
chmod +x ${MYCOSOFT_DIR}/scripts/backup-database.sh

echo -e "\n${YELLOW}[5/6] Configuring firewall...${NC}"

# Configure UFW
sudo ufw --force reset
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
# Allow local network access to services
sudo ufw allow from 192.168.0.0/24 to any port 3000
sudo ufw allow from 192.168.0.0/24 to any port 5678
sudo ufw allow from 192.168.0.0/24 to any port 8000
sudo ufw allow from 192.168.0.0/24 to any port 8001
sudo ufw allow from 192.168.0.0/24 to any port 8003
sudo ufw allow from 192.168.0.0/24 to any port 3002
sudo ufw allow from 192.168.0.0/24 to any port 9090
sudo ufw --force enable

echo -e "\n${YELLOW}[6/6] Final configuration...${NC}"

# Enable fail2ban
sudo systemctl enable fail2ban
sudo systemctl start fail2ban

# Expand LVM if possible
if command -v lvextend &> /dev/null; then
    sudo lvextend -l +100%FREE /dev/ubuntu-vg/ubuntu-lv 2>/dev/null || true
    sudo resize2fs /dev/ubuntu-vg/ubuntu-lv 2>/dev/null || true
fi

echo -e "\n${GREEN}"
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║                                                               ║"
echo "║            SETUP COMPLETE!                                    ║"
echo "║                                                               ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

echo -e "Docker version: $(docker --version)"
echo -e "Docker Compose version: $(docker compose version)"
echo ""
echo -e "${YELLOW}IMPORTANT:${NC} Log out and log back in for Docker group permissions to take effect!"
echo ""
echo "Next steps:"
echo "  1. Log out and log back in"
echo "  2. Clone repositories to /opt/mycosoft/mas and /opt/mycosoft/website"
echo "  3. Configure .env files"
echo "  4. Run: /opt/mycosoft/scripts/start-all.sh"
echo ""
echo "Documentation: /opt/mycosoft/mas/docs/"
echo ""
