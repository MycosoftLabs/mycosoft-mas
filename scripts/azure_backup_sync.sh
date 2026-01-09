#!/bin/bash
# Azure Backup Sync Script
# Syncs local backups to Azure Blob Storage

set -e

# Configuration
STORAGE_ACCOUNT="${AZURE_STORAGE_ACCOUNT:-mycosoftbackups}"
CONTAINER="${AZURE_BACKUP_CONTAINER:-backups}"
LOCAL_BACKUP_PATH="/mnt/mycosoft/backups"
LOG_FILE="/var/log/azure-sync.log"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log "=========================================="
log "  Azure Backup Sync Started"
log "=========================================="

# Check if azcopy is installed
if ! command -v azcopy &> /dev/null; then
    log "Installing azcopy..."
    wget -q https://aka.ms/downloadazcopy-v10-linux -O /tmp/azcopy.tar.gz
    tar -xzf /tmp/azcopy.tar.gz -C /tmp
    cp /tmp/azcopy_linux_amd64_*/azcopy /usr/local/bin/
    rm -rf /tmp/azcopy*
fi

# Check Azure login
if ! az account show &> /dev/null; then
    log "ERROR: Not logged into Azure"
    log "Run: az login"
    exit 1
fi

# Check local backup directory
if [ ! -d "$LOCAL_BACKUP_PATH" ]; then
    log "ERROR: Backup directory not found: $LOCAL_BACKUP_PATH"
    exit 1
fi

# Get SAS token for upload
log "Getting SAS token..."
END_DATE=$(date -u -d "+1 day" '+%Y-%m-%dT%H:%MZ')
SAS_TOKEN=$(az storage container generate-sas \
    --account-name "$STORAGE_ACCOUNT" \
    --name "$CONTAINER" \
    --permissions rwdl \
    --expiry "$END_DATE" \
    --output tsv)

if [ -z "$SAS_TOKEN" ]; then
    log "ERROR: Failed to get SAS token"
    exit 1
fi

# Sync backups
BLOB_URL="https://${STORAGE_ACCOUNT}.blob.core.windows.net/${CONTAINER}?${SAS_TOKEN}"

log "Syncing backups to Azure..."
log "  Source: $LOCAL_BACKUP_PATH"
log "  Destination: https://${STORAGE_ACCOUNT}.blob.core.windows.net/${CONTAINER}"

# Sync with azcopy
azcopy sync "$LOCAL_BACKUP_PATH" "$BLOB_URL" \
    --recursive \
    --delete-destination=false \
    --log-level=WARNING 2>&1 | tee -a "$LOG_FILE"

# Get sync statistics
UPLOAD_COUNT=$(azcopy jobs show --with-status=Completed 2>/dev/null | grep -c "Uploaded" || echo "0")

log ""
log "Sync complete!"
log "  Files synced: $UPLOAD_COUNT"

# Verify sync
log ""
log "Verifying Azure storage..."
FILE_COUNT=$(az storage blob list \
    --account-name "$STORAGE_ACCOUNT" \
    --container-name "$CONTAINER" \
    --query "length(@)" \
    --output tsv)

TOTAL_SIZE=$(az storage blob list \
    --account-name "$STORAGE_ACCOUNT" \
    --container-name "$CONTAINER" \
    --query "[].properties.contentLength" \
    --output tsv | awk '{s+=$1} END {printf "%.2f GB\n", s/1024/1024/1024}')

log "  Total files in Azure: $FILE_COUNT"
log "  Total size: $TOTAL_SIZE"

log ""
log "=========================================="
log "  Azure Backup Sync Complete"
log "=========================================="
