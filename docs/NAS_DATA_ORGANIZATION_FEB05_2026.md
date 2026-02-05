# NAS Data Organization - February 5, 2026

## Overview

This document describes the data organization structure on the Mycosoft NAS (192.168.0.105).

## Network Configuration

| Property | Value |
|----------|-------|
| NAS IP | 192.168.0.105 |
| Share Name | mycosoft.com |
| Mount Point (Sandbox) | /mnt/mycosoft-nas |
| Protocol | SMB/CIFS |
| Access | Read-write for mycosoft user |

## Directory Structure

```
/mnt/mycosoft-nas/
│
├── dev/                          # Development resources
│   ├── builds/                   # Build artifacts
│   │   ├── mas/                  # MAS Docker images
│   │   ├── website/              # Website builds
│   │   └── firmware/             # MycoBrain firmware
│   ├── artifacts/                # CI/CD artifacts
│   ├── logs/                     # Development logs
│   └── packages/                 # Development packages
│
├── mindex/                       # MINDEX data
│   ├── backups/                  # PostgreSQL backups
│   │   ├── mindex_backup_YYYYMMDD.sql
│   │   └── ...
│   ├── ledger/                   # Integrity ledger files
│   │   ├── ledger.json
│   │   └── blocks/
│   ├── exports/                  # Data exports
│   └── snapshots/                # Point-in-time snapshots
│
├── archives/                     # Long-term archives
│   └── 2026/
│       ├── Q1/
│       ├── Q2/
│       ├── Q3/
│       └── Q4/
│
├── media/                        # Media assets
│   └── website/
│       └── assets/               # Website media (mounted to container)
│           ├── videos/
│           └── images/
│
└── shared/                       # Cross-system shared data
    ├── configs/                  # Shared configurations
    ├── credentials/              # Encrypted credentials
    └── templates/                # Shared templates
```

## Data Categories

### Development (`/dev/`)

| Subdirectory | Purpose | Retention |
|--------------|---------|-----------|
| builds/ | Docker images, binaries | 90 days |
| artifacts/ | CI/CD outputs | 30 days |
| logs/ | Development logs | 14 days |
| packages/ | NPM, pip packages | As needed |

### MINDEX Data (`/mindex/`)

| Subdirectory | Purpose | Retention |
|--------------|---------|-----------|
| backups/ | PostgreSQL dumps | 30 days |
| ledger/ | Integrity verification | Permanent |
| exports/ | Data exports | 90 days |
| snapshots/ | Point-in-time data | 7 days |

### Archives (`/archives/`)

| Organization | Purpose | Retention |
|--------------|---------|-----------|
| Year/Quarter | Historical data | Permanent |

### Media (`/media/`)

| Subdirectory | Purpose | Note |
|--------------|---------|------|
| website/assets/ | Website media | Mounted to container |

## Mount Configuration

### Sandbox VM (192.168.0.187)

```bash
# /etc/fstab entry
//192.168.0.105/mycosoft.com /mnt/mycosoft-nas cifs credentials=/root/.smbcredentials,uid=1000,gid=1000,iocharset=utf8 0 0
```

### Docker Container Mount

```bash
docker run -d --name mycosoft-website \
  -p 3000:3000 \
  -v /mnt/mycosoft-nas/media/website/assets:/app/public/assets:ro \
  --restart unless-stopped \
  mycosoft-website:latest
```

## Integrity Verification

All data written to NAS is verified using the `NASSyncService`:

```python
from mycosoft_mas.security.nas_sync_service import NASSyncService

sync = NASSyncService("/mnt/mycosoft-nas")

# Sync with integrity verification
result = await sync.sync_with_integrity(
    source_dir="/local/data",
    dest_subpath="mindex/exports",
    record_in_ledger=True
)

# Result includes:
# - file_count: Number of files synced
# - total_size: Total bytes transferred
# - merkle_root: Root hash for verification
# - manifest_path: Path to sync manifest
```

### Manifest Format

Each sync creates a `sync_manifest.json`:

```json
{
  "sync_id": "uuid",
  "timestamp": "2026-02-05T00:00:00Z",
  "source_dir": "/local/data",
  "dest_path": "/mnt/mycosoft-nas/mindex/exports",
  "files": [
    {
      "path": "file.json",
      "hash": "sha256:...",
      "size": 1024
    }
  ],
  "merkle_root": "sha256:...",
  "ledger_entry_id": "uuid"
}
```

## Access Control

| Role | Permissions | Directories |
|------|-------------|-------------|
| Admin | Full | All |
| Developer | Read-write | /dev/, /mindex/exports/ |
| Service Account | Read-write | /mindex/backups/, /mindex/ledger/ |
| Website Container | Read-only | /media/website/assets/ |

## Maintenance

### Cleanup Script

```bash
# Run monthly to clean old data
find /mnt/mycosoft-nas/dev/builds -mtime +90 -delete
find /mnt/mycosoft-nas/mindex/backups -mtime +30 -delete
find /mnt/mycosoft-nas/dev/logs -mtime +14 -delete
```

### Capacity Monitoring

Monitor NAS capacity via Grafana dashboard or:

```bash
df -h /mnt/mycosoft-nas
```
