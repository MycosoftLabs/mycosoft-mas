#!/bin/bash
# Setup automated Docker cleanup cron job
# This runs weekly on Sundays at 3 AM to clean up old Docker resources

set -e

echo "=========================================="
echo "SETTING UP DOCKER CLEANUP CRON"
echo "=========================================="

# Create cleanup script
CLEANUP_SCRIPT="/usr/local/bin/docker-cleanup.sh"

sudo tee ${CLEANUP_SCRIPT} > /dev/null << 'EOF'
#!/bin/bash
# Weekly Docker cleanup script
# Removes unused images, containers, volumes older than 7 days

LOG_FILE="/var/log/docker-cleanup.log"
DATE=$(date '+%Y-%m-%d %H:%M:%S')

echo "[${DATE}] Starting Docker cleanup..." >> ${LOG_FILE}

# Get disk usage before
BEFORE=$(df -h / | awk 'NR==2 {print $5}')

# Clean up resources older than 7 days (168 hours)
docker system prune -af --filter "until=168h" >> ${LOG_FILE} 2>&1
docker builder prune -af --keep-storage=2GB >> ${LOG_FILE} 2>&1
docker volume prune -f >> ${LOG_FILE} 2>&1

# Get disk usage after
AFTER=$(df -h / | awk 'NR==2 {print $5}')

echo "[${DATE}] Cleanup complete. Disk usage: ${BEFORE} -> ${AFTER}" >> ${LOG_FILE}
EOF

# Make script executable
sudo chmod +x ${CLEANUP_SCRIPT}

# Add to crontab (run every Sunday at 3 AM)
CRON_JOB="0 3 * * 0 ${CLEANUP_SCRIPT}"

# Check if cron job already exists
if sudo crontab -l 2>/dev/null | grep -q "docker-cleanup.sh"; then
    echo "Cron job already exists. Updating..."
    sudo crontab -l 2>/dev/null | grep -v "docker-cleanup.sh" | sudo crontab -
fi

# Add new cron job
(sudo crontab -l 2>/dev/null; echo "${CRON_JOB}") | sudo crontab -

echo ""
echo "Cleanup script created: ${CLEANUP_SCRIPT}"
echo "Cron job scheduled: Every Sunday at 3 AM"
echo ""
echo "Current crontab:"
sudo crontab -l

echo ""
echo "=========================================="
echo "CRON SETUP COMPLETE!"
echo "=========================================="
