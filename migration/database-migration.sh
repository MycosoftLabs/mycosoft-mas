#!/bin/bash
# Database Migration Script
# Run this on Windows machine to export databases, then on VM1 to import

set -e

MODE="${1:-export}"  # export or import
VM1_IP="${2:-192.168.1.100}"
VM1_USER="${3:-mycosoft}"

echo "=========================================="
echo "Database Migration: $MODE"
echo "=========================================="

if [ "$MODE" = "export" ]; then
    echo "Exporting databases from local machine..."
    
    # Export PostgreSQL
    echo "[1/3] Exporting PostgreSQL..."
    if docker ps | grep -q postgres; then
        docker exec $(docker ps | grep postgres | awk '{print $1}') pg_dump -U mas mas > mas_backup.sql
        echo "PostgreSQL exported to mas_backup.sql"
    elif command -v pg_dump &> /dev/null; then
        pg_dump -U mas -h localhost -p 5433 mas > mas_backup.sql
        echo "PostgreSQL exported to mas_backup.sql"
    else
        echo "WARNING: PostgreSQL not found. Skipping export."
    fi
    
    # Export Redis
    echo "[2/3] Exporting Redis..."
    if docker ps | grep -q redis; then
        REDIS_CONTAINER=$(docker ps | grep redis | awk '{print $1}')
        docker exec $REDIS_CONTAINER redis-cli SAVE
        docker cp $REDIS_CONTAINER:/data/dump.rdb ./redis_backup.rdb
        echo "Redis exported to redis_backup.rdb"
    else
        echo "WARNING: Redis not found. Skipping export."
    fi
    
    # Export Qdrant
    echo "[3/3] Exporting Qdrant..."
    if docker ps | grep -q qdrant; then
        QDRANT_VOLUME=$(docker volume ls | grep qdrant | awk '{print $2}')
        if [ -n "$QDRANT_VOLUME" ]; then
            docker run --rm \
                -v $QDRANT_VOLUME:/data \
                -v $(pwd):/backup \
                alpine tar czf /backup/qdrant_backup.tar.gz -C /data .
            echo "Qdrant exported to qdrant_backup.tar.gz"
        fi
    else
        echo "WARNING: Qdrant not found. Skipping export."
    fi
    
    echo ""
    echo "Export completed!"
    echo "Files created:"
    ls -lh *.sql *.rdb *.tar.gz 2>/dev/null || true
    echo ""
    echo "Next: Transfer files to VM1 and run:"
    echo "  ./database-migration.sh import $VM1_IP $VM1_USER"
    
elif [ "$MODE" = "import" ]; then
    echo "Importing databases to VM1..."
    
    # Transfer files to VM1
    echo "[1/4] Transferring backup files to VM1..."
    scp mas_backup.sql redis_backup.rdb qdrant_backup.tar.gz $VM1_USER@$VM1_IP:/tmp/ 2>/dev/null || {
        echo "ERROR: Could not transfer files. Ensure files exist and VM1 is accessible."
        exit 1
    }
    
    # Import PostgreSQL
    echo "[2/4] Importing PostgreSQL..."
    ssh $VM1_USER@$VM1_IP << 'EOF'
        cd /opt/mycosoft
        docker-compose -f docker-compose.prod.yml up -d postgres
        sleep 10
        docker exec -i mycosoft-postgres psql -U mas -d mas < /tmp/mas_backup.sql
        echo "PostgreSQL imported successfully"
EOF
    
    # Import Redis
    echo "[3/4] Importing Redis..."
    ssh $VM1_USER@$VM1_IP << 'EOF'
        cd /opt/mycosoft
        docker-compose -f docker-compose.prod.yml up -d redis
        sleep 5
        docker cp /tmp/redis_backup.rdb mycosoft-redis:/data/dump.rdb
        docker restart mycosoft-redis
        echo "Redis imported successfully"
EOF
    
    # Import Qdrant
    echo "[4/4] Importing Qdrant..."
    ssh $VM1_USER@$VM1_IP << 'EOF'
        cd /opt/mycosoft
        docker-compose -f docker-compose.prod.yml up -d qdrant
        sleep 5
        docker run --rm \
            -v mycosoft-qdrant:/data \
            -v /tmp:/backup \
            alpine sh -c "cd /data && rm -rf * && tar xzf /backup/qdrant_backup.tar.gz"
        docker restart mycosoft-qdrant
        echo "Qdrant imported successfully"
EOF
    
    echo ""
    echo "=========================================="
    echo "Database import completed!"
    echo "=========================================="
    
else
    echo "Usage: $0 [export|import] [VM1_IP] [VM1_USER]"
    exit 1
fi
