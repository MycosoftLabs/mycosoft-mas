#!/bin/bash
# Setup script for myca-database VM (192.168.20.12)
# Run after vm_setup_common.sh

set -e

echo "=================================================="
echo "  MYCA Database VM Setup"
echo "=================================================="

VM_IP="192.168.20.12"
NAS_PATH="/mnt/mycosoft"

# Verify NAS mount
echo "[1/6] Verifying NAS mount..."
if ! mountpoint -q $NAS_PATH; then
    echo "ERROR: NAS not mounted at $NAS_PATH"
    echo "Run: mount -a (after configuring /etc/fstab)"
    exit 1
fi
echo "  NAS mounted successfully"

# Create database directories on NAS
echo "[2/6] Creating database directories..."
mkdir -p $NAS_PATH/databases/postgres
mkdir -p $NAS_PATH/databases/redis
mkdir -p $NAS_PATH/databases/qdrant
chown -R 999:999 $NAS_PATH/databases/postgres  # PostgreSQL user
chown -R 999:999 $NAS_PATH/databases/redis     # Redis user

# Create Docker network
echo "[3/6] Creating Docker network..."
docker network create myca-network 2>/dev/null || true

# Create docker-compose for databases
echo "[4/6] Creating docker-compose.yml..."
cat > /opt/myca/docker-compose.database.yml << 'EOF'
version: '3.8'

services:
  postgres:
    image: postgres:16-alpine
    container_name: myca-postgres
    restart: always
    environment:
      POSTGRES_USER: mas
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: mas
    volumes:
      - /mnt/mycosoft/databases/postgres:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    networks:
      - myca-network
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U mas"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    container_name: myca-redis
    restart: always
    command: redis-server --appendonly yes
    volumes:
      - /mnt/mycosoft/databases/redis:/data
    ports:
      - "6379:6379"
    networks:
      - myca-network
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  qdrant:
    image: qdrant/qdrant:latest
    container_name: myca-qdrant
    restart: always
    volumes:
      - /mnt/mycosoft/databases/qdrant:/qdrant/storage
    ports:
      - "6333:6333"
      - "6334:6334"
    networks:
      - myca-network
    environment:
      QDRANT__SERVICE__HTTP_PORT: 6333
      QDRANT__SERVICE__GRPC_PORT: 6334

networks:
  myca-network:
    external: true
EOF

# Create environment file
echo "[5/6] Creating environment file..."
if [ ! -f /etc/myca/database.env ]; then
    POSTGRES_PASSWORD=$(openssl rand -base64 32 | tr -d '/+=' | head -c 32)
    cat > /etc/myca/database.env << EOF
POSTGRES_PASSWORD=$POSTGRES_PASSWORD
POSTGRES_USER=mas
POSTGRES_DB=mas
REDIS_URL=redis://localhost:6379
QDRANT_URL=http://localhost:6333
EOF
    chmod 600 /etc/myca/database.env
    echo "  Generated new database credentials"
    echo "  POSTGRES_PASSWORD: $POSTGRES_PASSWORD"
    echo "  SAVE THIS PASSWORD!"
fi

# Create systemd service
echo "[6/6] Creating systemd service..."
cat > /etc/systemd/system/myca-database.service << 'EOF'
[Unit]
Description=MYCA Database Services
After=network.target docker.service
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/myca
EnvironmentFile=/etc/myca/database.env
ExecStart=/usr/bin/docker compose -f docker-compose.database.yml up -d
ExecStop=/usr/bin/docker compose -f docker-compose.database.yml down
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable myca-database

echo ""
echo "=================================================="
echo "  Database VM Setup Complete!"
echo "=================================================="
echo ""
echo "  To start databases:"
echo "    systemctl start myca-database"
echo ""
echo "  Or manually:"
echo "    cd /opt/myca"
echo "    source /etc/myca/database.env"
echo "    docker compose -f docker-compose.database.yml up -d"
echo ""
echo "  Connection info:"
echo "    PostgreSQL: postgresql://mas:PASSWORD@$VM_IP:5432/mas"
echo "    Redis: redis://$VM_IP:6379"
echo "    Qdrant: http://$VM_IP:6333"
echo ""
