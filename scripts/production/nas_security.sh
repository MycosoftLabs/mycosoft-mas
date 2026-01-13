#!/bin/bash
# NAS Security Configuration
# Implements compartmentalization and access controls

set -e

echo "=================================================="
echo "  NAS Security Configuration"
echo "=================================================="

NAS_PATH="/mnt/mycosoft"

# Create secure directories structure
echo "[1/5] Creating secure directory structure..."

# Public directories (web accessible via API)
mkdir -p $NAS_PATH/knowledge/{mindex,encyclopedia,embeddings}
mkdir -p $NAS_PATH/website/{static,uploads}

# Private directories (staff only)
mkdir -p $NAS_PATH/secure/{admin,secrets,dev-data}
mkdir -p $NAS_PATH/backups/{daily,weekly,disaster}
mkdir -p $NAS_PATH/databases/{postgres,redis,qdrant}

# Set ownership
echo "[2/5] Setting ownership..."
chown -R myca:myca $NAS_PATH/knowledge
chown -R myca:myca $NAS_PATH/website
chown -R myca:myca $NAS_PATH/agents
chown -R root:root $NAS_PATH/secure
chown -R root:root $NAS_PATH/backups
chown -R 999:999 $NAS_PATH/databases/postgres
chown -R 999:999 $NAS_PATH/databases/redis
chown -R 1000:1000 $NAS_PATH/databases/qdrant

# Set permissions
echo "[3/5] Setting permissions..."

# Public - readable by myca user
chmod 755 $NAS_PATH/knowledge
chmod -R 644 $NAS_PATH/knowledge/*
find $NAS_PATH/knowledge -type d -exec chmod 755 {} \;

# Website uploads - writable
chmod 755 $NAS_PATH/website
chmod 755 $NAS_PATH/website/static
chmod 777 $NAS_PATH/website/uploads

# Secure - root only
chmod 700 $NAS_PATH/secure
chmod -R 600 $NAS_PATH/secure/*
find $NAS_PATH/secure -type d -exec chmod 700 {} \;

# Backups - root only
chmod 700 $NAS_PATH/backups
chmod -R 600 $NAS_PATH/backups/*
find $NAS_PATH/backups -type d -exec chmod 700 {} \;

# Databases - specific user ownership
chmod 700 $NAS_PATH/databases/postgres
chmod 700 $NAS_PATH/databases/redis
chmod 700 $NAS_PATH/databases/qdrant

# Create access control file
echo "[4/5] Creating access control documentation..."
cat > $NAS_PATH/ACCESS_CONTROL.md << 'EOF'
# NAS Access Control Policy

## Directory Access Levels

### PUBLIC (Web Accessible via API)
- `/mnt/mycosoft/knowledge/` - Read-only via MINDEX API
- `/mnt/mycosoft/website/static/` - Served via nginx

### RESTRICTED (Application Access)
- `/mnt/mycosoft/agents/` - MAS API only
- `/mnt/mycosoft/website/uploads/` - Website uploads

### PRIVATE (Staff Only - No Web Access)
- `/mnt/mycosoft/secure/` - SSH access only, root user
- `/mnt/mycosoft/backups/` - Backup processes only
- `/mnt/mycosoft/databases/` - Database containers only

## VM Access Matrix

| VM | knowledge | website | agents | secure | backups | databases |
|----|-----------|---------|--------|--------|---------|-----------|
| myca-website | R | RW | - | - | - | - |
| myca-api | RW | R | RW | - | - | - |
| myca-database | - | - | - | - | R | RW |
| SSH (root) | RW | RW | RW | RW | RW | RW |

## Security Notes

1. Web services NEVER have direct access to /secure or /backups
2. Database files are only accessed by database containers
3. All sensitive operations require SSH with key authentication
4. Uploads are scanned and sanitized by the application
5. Backups are encrypted at rest

## Emergency Access

In case of emergency, root SSH access is available:
- Requires SSH key authentication
- All access is logged
- Contact super admin (Morgan) for access
EOF

# Create NFS export rules
echo "[5/5] Creating NFS export configuration..."
cat > /tmp/mycosoft-exports << 'EOF'
# MYCA NAS Exports
# Add to /etc/exports on NAS

# Website VM - limited access
/mycosoft/knowledge 192.168.20.11(ro,sync,no_subtree_check)
/mycosoft/website 192.168.20.11(rw,sync,no_subtree_check)

# API VM - broader access
/mycosoft/knowledge 192.168.20.10(rw,sync,no_subtree_check)
/mycosoft/agents 192.168.20.10(rw,sync,no_subtree_check)
/mycosoft/website 192.168.20.10(ro,sync,no_subtree_check)

# Database VM - database only
/mycosoft/databases 192.168.20.12(rw,sync,no_subtree_check)

# DENY: secure and backups not exported via NFS
# Access only via SSH
EOF

echo ""
echo "  NFS export rules saved to /tmp/mycosoft-exports"
echo "  Apply these rules on the NAS server."

echo ""
echo "=================================================="
echo "  NAS Security Configuration Complete!"
echo "=================================================="
echo ""
echo "  Directory permissions set:"
echo "    /knowledge - Public (read via API)"
echo "    /website - Application access"
echo "    /agents - API VM only"
echo "    /secure - Staff SSH only"
echo "    /backups - Root only"
echo "    /databases - DB containers only"
echo ""
echo "  Review: $NAS_PATH/ACCESS_CONTROL.md"
echo ""
