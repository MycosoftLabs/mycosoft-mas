#!/bin/bash
# Migrate databases from local Docker to production
# Run from mycocomp after production DB is running

set -e

echo "=================================================="
echo "  MYCA Database Migration"
echo "=================================================="

# Configuration
LOCAL_POSTGRES_CONTAINER="mas-postgres"
LOCAL_REDIS_CONTAINER="mas-redis"
LOCAL_QDRANT_URL="http://localhost:6345"

PROD_DB_HOST="192.168.20.12"
PROD_POSTGRES_PORT="5432"
PROD_REDIS_PORT="6379"
PROD_QDRANT_PORT="6333"

BACKUP_DIR="M:/backups/migration/$(date +%Y%m%d_%H%M%S)"

# Create backup directory
echo "[1/6] Creating backup directory..."
mkdir -p "$BACKUP_DIR"

# Export PostgreSQL
echo "[2/6] Exporting PostgreSQL..."
docker exec $LOCAL_POSTGRES_CONTAINER pg_dumpall -U mas > "$BACKUP_DIR/postgres_full.sql"
echo "  Exported to $BACKUP_DIR/postgres_full.sql"
echo "  Size: $(du -h "$BACKUP_DIR/postgres_full.sql" | cut -f1)"

# Export Redis
echo "[3/6] Exporting Redis..."
docker exec $LOCAL_REDIS_CONTAINER redis-cli BGSAVE
sleep 5  # Wait for save to complete
docker cp $LOCAL_REDIS_CONTAINER:/data/dump.rdb "$BACKUP_DIR/redis_dump.rdb"
echo "  Exported to $BACKUP_DIR/redis_dump.rdb"

# Export Qdrant collections
echo "[4/6] Exporting Qdrant collections..."
COLLECTIONS=$(curl -s "$LOCAL_QDRANT_URL/collections" | jq -r '.result.collections[].name')
mkdir -p "$BACKUP_DIR/qdrant"

for collection in $COLLECTIONS; do
    echo "  Snapshotting collection: $collection"
    SNAPSHOT=$(curl -s -X POST "$LOCAL_QDRANT_URL/collections/$collection/snapshots" | jq -r '.result.name')
    echo "    Snapshot: $SNAPSHOT"
    # Note: Full export would require downloading the snapshot
done
echo "  Qdrant snapshots created (download manually if needed)"

# Verify backup
echo "[5/6] Verifying backups..."
ls -la "$BACKUP_DIR/"

echo ""
echo "[6/6] Import Instructions"
echo "========================="
echo ""
echo "To import to production ($PROD_DB_HOST):"
echo ""
echo "PostgreSQL:"
echo "  scp $BACKUP_DIR/postgres_full.sql myca@$PROD_DB_HOST:/tmp/"
echo "  ssh myca@$PROD_DB_HOST"
echo "  docker exec -i myca-postgres psql -U mas < /tmp/postgres_full.sql"
echo ""
echo "Redis:"
echo "  scp $BACKUP_DIR/redis_dump.rdb myca@$PROD_DB_HOST:/tmp/"
echo "  ssh myca@$PROD_DB_HOST"
echo "  docker stop myca-redis"
echo "  cp /tmp/redis_dump.rdb /mnt/mycosoft/databases/redis/dump.rdb"
echo "  docker start myca-redis"
echo ""
echo "Qdrant:"
echo "  # Restore from snapshot via API"
echo "  curl -X POST 'http://$PROD_DB_HOST:$PROD_QDRANT_PORT/collections/{name}/snapshots/recover'"
echo ""
echo "=================================================="
echo "  Backup complete: $BACKUP_DIR"
echo "=================================================="
