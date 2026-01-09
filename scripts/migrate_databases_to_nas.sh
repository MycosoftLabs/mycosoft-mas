#!/bin/bash
# Migrate PostgreSQL, Redis, and Qdrant data to NAS storage
# Run this script on the MYCA Core VM after NFS is mounted

set -e

NAS_MOUNT="/mnt/mycosoft"
BACKUP_DATE=$(date +%Y%m%d_%H%M%S)

echo "=========================================="
echo "  MYCA Database Migration to NAS"
echo "=========================================="
echo ""

# Check if NAS is mounted
if ! mountpoint -q "$NAS_MOUNT"; then
    echo "ERROR: NAS not mounted at $NAS_MOUNT"
    echo "Please mount the NAS first:"
    echo "  sudo mount -t nfs 192.168.0.1:/mycosoft $NAS_MOUNT"
    exit 1
fi

echo "NAS mounted at $NAS_MOUNT"
echo ""

# Create directories if they don't exist
echo "Creating directory structure..."
mkdir -p "$NAS_MOUNT/databases/postgres"
mkdir -p "$NAS_MOUNT/databases/redis"
mkdir -p "$NAS_MOUNT/knowledge/qdrant"
mkdir -p "$NAS_MOUNT/backups/migration_$BACKUP_DATE"

# ==============================================
# PostgreSQL Migration
# ==============================================
echo ""
echo "=== PostgreSQL Migration ==="

# Check if PostgreSQL is running
if docker ps | grep -q postgres; then
    echo "Stopping PostgreSQL container..."
    docker stop mas-postgres || true
    
    # Backup current data
    echo "Backing up current PostgreSQL data..."
    if [ -d "/var/lib/docker/volumes/mycosoft-mas_postgres_data" ]; then
        sudo cp -r /var/lib/docker/volumes/mycosoft-mas_postgres_data/_data/* \
            "$NAS_MOUNT/backups/migration_$BACKUP_DATE/postgres/"
        echo "Backup created at $NAS_MOUNT/backups/migration_$BACKUP_DATE/postgres/"
    fi
    
    # Set permissions
    echo "Setting permissions..."
    sudo chown -R 999:999 "$NAS_MOUNT/databases/postgres"
    sudo chmod -R 700 "$NAS_MOUNT/databases/postgres"
    
    echo "PostgreSQL data directory ready at $NAS_MOUNT/databases/postgres"
else
    echo "PostgreSQL container not running, skipping backup"
    echo "Data directory prepared at $NAS_MOUNT/databases/postgres"
fi

# ==============================================
# Redis Migration
# ==============================================
echo ""
echo "=== Redis Migration ==="

# Check if Redis is running
if docker ps | grep -q redis; then
    echo "Stopping Redis container..."
    docker stop mas-redis || true
    
    # Backup current data
    echo "Backing up current Redis data..."
    if [ -d "/var/lib/docker/volumes/mycosoft-mas_redis-data" ]; then
        sudo cp -r /var/lib/docker/volumes/mycosoft-mas_redis-data/_data/* \
            "$NAS_MOUNT/backups/migration_$BACKUP_DATE/redis/" 2>/dev/null || true
        echo "Backup created"
    fi
    
    # Set permissions
    echo "Setting permissions..."
    sudo chown -R 999:999 "$NAS_MOUNT/databases/redis"
    sudo chmod -R 755 "$NAS_MOUNT/databases/redis"
    
    echo "Redis data directory ready at $NAS_MOUNT/databases/redis"
else
    echo "Redis container not running, skipping backup"
    echo "Data directory prepared at $NAS_MOUNT/databases/redis"
fi

# ==============================================
# Qdrant Migration
# ==============================================
echo ""
echo "=== Qdrant Migration ==="

# Check if Qdrant is running
if docker ps | grep -q qdrant; then
    echo "Stopping Qdrant container..."
    docker stop mas-qdrant || true
    
    # Backup current data
    echo "Backing up current Qdrant data..."
    if [ -d "/var/lib/docker/volumes/mycosoft-mas_qdrant_data" ]; then
        sudo cp -r /var/lib/docker/volumes/mycosoft-mas_qdrant_data/_data/* \
            "$NAS_MOUNT/backups/migration_$BACKUP_DATE/qdrant/" 2>/dev/null || true
        echo "Backup created"
    fi
    
    # Set permissions
    echo "Setting permissions..."
    sudo chown -R 1000:1000 "$NAS_MOUNT/knowledge/qdrant"
    sudo chmod -R 755 "$NAS_MOUNT/knowledge/qdrant"
    
    echo "Qdrant data directory ready at $NAS_MOUNT/knowledge/qdrant"
else
    echo "Qdrant container not running, skipping backup"
    echo "Data directory prepared at $NAS_MOUNT/knowledge/qdrant"
fi

# ==============================================
# Summary
# ==============================================
echo ""
echo "=========================================="
echo "  Migration Preparation Complete"
echo "=========================================="
echo ""
echo "NAS Directories Created:"
echo "  PostgreSQL: $NAS_MOUNT/databases/postgres"
echo "  Redis:      $NAS_MOUNT/databases/redis"
echo "  Qdrant:     $NAS_MOUNT/knowledge/qdrant"
echo ""
echo "Backup Location:"
echo "  $NAS_MOUNT/backups/migration_$BACKUP_DATE/"
echo ""
echo "Next Steps:"
echo "1. Update docker-compose.yml to use NAS volumes"
echo "2. Restart containers with new volume mounts"
echo "3. Verify data integrity"
echo ""
echo "Example docker-compose volume configuration:"
echo "  postgres:"
echo "    volumes:"
echo "      - /mnt/mycosoft/databases/postgres:/var/lib/postgresql/data"
echo ""
echo "  redis:"
echo "    volumes:"
echo "      - /mnt/mycosoft/databases/redis:/data"
echo ""
echo "  qdrant:"
echo "    volumes:"
echo "      - /mnt/mycosoft/knowledge/qdrant:/qdrant/storage"
