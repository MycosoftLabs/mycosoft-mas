# MINDEX NAS Storage Configuration

This guide explains how to configure MINDEX to use your NAS storage for persistent fungal data.

## Storage Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        MINDEX Storage Layout                             │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐  │
│  │   PRIMARY NAS    │    │   BACKUP NAS     │    │   LOCAL CACHE    │  │
│  │  (16TB Synology) │    │ (26TB Dream M.)  │    │   (Container)    │  │
│  ├──────────────────┤    ├──────────────────┤    ├──────────────────┤  │
│  │ /mnt/nas/mindex  │───▶│ /mnt/dream/mindex│    │   /app/data      │  │
│  │                  │    │                  │    │                  │  │
│  │ • mindex.db      │    │ • mindex.db.bak  │    │ • temp files     │  │
│  │ • images/        │    │ • images/        │    │ • session cache  │  │
│  │ • genomes/       │    │ • genomes/       │    │                  │  │
│  │ • sequences/     │    │ • sequences/     │    │                  │  │
│  └──────────────────┘    └──────────────────┘    └──────────────────┘  │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

## Required Storage Space

| Data Type | Estimated Size | Growth Rate |
|-----------|---------------|-------------|
| **Species Database** | 2-5 GB | 100 MB/month |
| **Observations** | 10-50 GB | 500 MB/month |
| **Images** | 500 GB - 2 TB | 50 GB/month |
| **Genome Sequences** | 1-5 TB | 100 GB/month |
| **GenBank Data** | 500 GB - 1 TB | 50 GB/month |

**Total Recommended**: 6-10 TB minimum, 16 TB recommended

## Windows Setup

### Step 1: Mount NAS Share

```powershell
# Create persistent network drive for Synology NAS
net use M: \\192.168.1.100\mindex /user:username password /persistent:yes

# Verify mount
Get-PSDrive M
```

### Step 2: Create Directory Structure

```powershell
# Create data directories
mkdir M:\mindex
mkdir M:\mindex\images
mkdir M:\mindex\genomes
mkdir M:\mindex\sequences
mkdir M:\mindex\backups
```

### Step 3: Configure Docker

Update `docker-compose.mindex.yml`:

```yaml
volumes:
  mindex_data:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: M:\mindex
```

Or set environment variable:

```powershell
$env:MINDEX_HOST_PATH = "M:\mindex"
docker-compose -f docker-compose.mindex.yml up -d
```

## Linux Setup

### Step 1: Install CIFS Utils

```bash
sudo apt-get install cifs-utils
```

### Step 2: Create Credentials File

```bash
sudo nano /etc/nas-creds

# Add:
username=your_nas_user
password=your_nas_password
domain=WORKGROUP
```

```bash
sudo chmod 600 /etc/nas-creds
```

### Step 3: Add to fstab

```bash
sudo nano /etc/fstab

# Add line for Synology NAS (16TB)
//192.168.1.100/mindex /mnt/nas/mindex cifs credentials=/etc/nas-creds,uid=1000,gid=1000,vers=3.0 0 0

# Add line for Dream Machine (26TB) - backup
//192.168.1.1/mindex /mnt/dream/mindex cifs credentials=/etc/nas-creds,uid=1000,gid=1000,vers=3.0 0 0
```

### Step 4: Mount

```bash
sudo mkdir -p /mnt/nas/mindex /mnt/dream/mindex
sudo mount -a
```

### Step 5: Verify

```bash
df -h | grep mindex
ls -la /mnt/nas/mindex
```

## Dream Machine Setup

The UniFi Dream Machine Pro (26TB) serves as backup storage:

### Configure SMB Share on Dream Machine

1. SSH into Dream Machine:
```bash
ssh root@192.168.1.1
```

2. Create share directory:
```bash
mkdir -p /mnt/data/mindex
```

3. Configure Samba (if not already):
```bash
# Install samba if needed
apt-get update && apt-get install samba

# Edit /etc/samba/smb.conf
[mindex]
    path = /mnt/data/mindex
    browsable = yes
    read only = no
    guest ok = no
```

## Environment Variables

Set these in your `.env` file or environment:

```bash
# Primary storage (Synology NAS)
MINDEX_NAS_PATH=/mnt/nas/mindex

# Backup storage (Dream Machine)
MINDEX_BACKUP_PATH=/mnt/dream/mindex

# For Docker on host machine
MINDEX_HOST_PATH=/mnt/nas/mindex  # Linux
# MINDEX_HOST_PATH=M:\mindex      # Windows
```

## Backup Strategy

### Automated Daily Backup

Add to crontab on the server:

```bash
# Daily backup at 3 AM
0 3 * * * rsync -avz /mnt/nas/mindex/ /mnt/dream/mindex/
```

### Or use Docker backup service:

```yaml
# In docker-compose.mindex.yml
services:
  mindex-backup:
    image: restic/restic
    volumes:
      - /mnt/nas/mindex:/source:ro
      - /mnt/dream/mindex:/backup
    environment:
      - RESTIC_REPOSITORY=/backup
      - RESTIC_PASSWORD=your_backup_password
    command: |
      backup /source --tag mindex
    depends_on:
      - mindex
```

## Monitoring Storage

### Check Database Size

```bash
# Connect to container
docker exec -it mindex sh

# Check database size
ls -lh /mnt/nas/mindex/mindex.db

# Check total storage
du -sh /mnt/nas/mindex/*
```

### Via API

```bash
curl http://localhost:8000/health | jq '.db_size_mb'
```

## Troubleshooting

### "Permission denied" on NAS mount

```bash
# Check mount options
mount | grep mindex

# Remount with correct UID
sudo mount -o remount,uid=1000,gid=1000 /mnt/nas/mindex
```

### "No space left on device"

```bash
# Check available space
df -h /mnt/nas/mindex

# If full, clean old backups
find /mnt/nas/mindex/backups -mtime +30 -delete
```

### Container can't write to volume

```bash
# Check Docker volume
docker inspect mindex | grep -A 10 Mounts

# Fix permissions
sudo chown -R 1000:1000 /mnt/nas/mindex
```

### NAS not accessible

```bash
# Test network connectivity
ping 192.168.1.100

# Test SMB access
smbclient //192.168.1.100/mindex -U username
```

## Data Migration

### Import existing data to NAS:

```bash
# Stop MINDEX
docker-compose -f docker-compose.mindex.yml down

# Copy data to NAS
rsync -avz ./data/mindex/ /mnt/nas/mindex/

# Update config and restart
docker-compose -f docker-compose.mindex.yml up -d
```

# MINDEX NAS Storage Configuration

This guide explains how to configure MINDEX to use your NAS storage for persistent fungal data.

## Storage Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        MINDEX Storage Layout                             │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐  │
│  │   PRIMARY NAS    │    │   BACKUP NAS     │    │   LOCAL CACHE    │  │
│  │  (16TB Synology) │    │ (26TB Dream M.)  │    │   (Container)    │  │
│  ├──────────────────┤    ├──────────────────┤    ├──────────────────┤  │
│  │ /mnt/nas/mindex  │───▶│ /mnt/dream/mindex│    │   /app/data      │  │
│  │                  │    │                  │    │                  │  │
│  │ • mindex.db      │    │ • mindex.db.bak  │    │ • temp files     │  │
│  │ • images/        │    │ • images/        │    │ • session cache  │  │
│  │ • genomes/       │    │ • genomes/       │    │                  │  │
│  │ • sequences/     │    │ • sequences/     │    │                  │  │
│  └──────────────────┘    └──────────────────┘    └──────────────────┘  │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

## Required Storage Space

| Data Type | Estimated Size | Growth Rate |
|-----------|---------------|-------------|
| **Species Database** | 2-5 GB | 100 MB/month |
| **Observations** | 10-50 GB | 500 MB/month |
| **Images** | 500 GB - 2 TB | 50 GB/month |
| **Genome Sequences** | 1-5 TB | 100 GB/month |
| **GenBank Data** | 500 GB - 1 TB | 50 GB/month |

**Total Recommended**: 6-10 TB minimum, 16 TB recommended

## Windows Setup

### Step 1: Mount NAS Share

```powershell
# Create persistent network drive for Synology NAS
net use M: \\192.168.1.100\mindex /user:username password /persistent:yes

# Verify mount
Get-PSDrive M
```

### Step 2: Create Directory Structure

```powershell
# Create data directories
mkdir M:\mindex
mkdir M:\mindex\images
mkdir M:\mindex\genomes
mkdir M:\mindex\sequences
mkdir M:\mindex\backups
```

### Step 3: Configure Docker

Update `docker-compose.mindex.yml`:

```yaml
volumes:
  mindex_data:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: M:\mindex
```

Or set environment variable:

```powershell
$env:MINDEX_HOST_PATH = "M:\mindex"
docker-compose -f docker-compose.mindex.yml up -d
```

## Linux Setup

### Step 1: Install CIFS Utils

```bash
sudo apt-get install cifs-utils
```

### Step 2: Create Credentials File

```bash
sudo nano /etc/nas-creds

# Add:
username=your_nas_user
password=your_nas_password
domain=WORKGROUP
```

```bash
sudo chmod 600 /etc/nas-creds
```

### Step 3: Add to fstab

```bash
sudo nano /etc/fstab

# Add line for Synology NAS (16TB)
//192.168.1.100/mindex /mnt/nas/mindex cifs credentials=/etc/nas-creds,uid=1000,gid=1000,vers=3.0 0 0

# Add line for Dream Machine (26TB) - backup
//192.168.1.1/mindex /mnt/dream/mindex cifs credentials=/etc/nas-creds,uid=1000,gid=1000,vers=3.0 0 0
```

### Step 4: Mount

```bash
sudo mkdir -p /mnt/nas/mindex /mnt/dream/mindex
sudo mount -a
```

### Step 5: Verify

```bash
df -h | grep mindex
ls -la /mnt/nas/mindex
```

## Dream Machine Setup

The UniFi Dream Machine Pro (26TB) serves as backup storage:

### Configure SMB Share on Dream Machine

1. SSH into Dream Machine:
```bash
ssh root@192.168.1.1
```

2. Create share directory:
```bash
mkdir -p /mnt/data/mindex
```

3. Configure Samba (if not already):
```bash
# Install samba if needed
apt-get update && apt-get install samba

# Edit /etc/samba/smb.conf
[mindex]
    path = /mnt/data/mindex
    browsable = yes
    read only = no
    guest ok = no
```

## Environment Variables

Set these in your `.env` file or environment:

```bash
# Primary storage (Synology NAS)
MINDEX_NAS_PATH=/mnt/nas/mindex

# Backup storage (Dream Machine)
MINDEX_BACKUP_PATH=/mnt/dream/mindex

# For Docker on host machine
MINDEX_HOST_PATH=/mnt/nas/mindex  # Linux
# MINDEX_HOST_PATH=M:\mindex      # Windows
```

## Backup Strategy

### Automated Daily Backup

Add to crontab on the server:

```bash
# Daily backup at 3 AM
0 3 * * * rsync -avz /mnt/nas/mindex/ /mnt/dream/mindex/
```

### Or use Docker backup service:

```yaml
# In docker-compose.mindex.yml
services:
  mindex-backup:
    image: restic/restic
    volumes:
      - /mnt/nas/mindex:/source:ro
      - /mnt/dream/mindex:/backup
    environment:
      - RESTIC_REPOSITORY=/backup
      - RESTIC_PASSWORD=your_backup_password
    command: |
      backup /source --tag mindex
    depends_on:
      - mindex
```

## Monitoring Storage

### Check Database Size

```bash
# Connect to container
docker exec -it mindex sh

# Check database size
ls -lh /mnt/nas/mindex/mindex.db

# Check total storage
du -sh /mnt/nas/mindex/*
```

### Via API

```bash
curl http://localhost:8000/health | jq '.db_size_mb'
```

## Troubleshooting

### "Permission denied" on NAS mount

```bash
# Check mount options
mount | grep mindex

# Remount with correct UID
sudo mount -o remount,uid=1000,gid=1000 /mnt/nas/mindex
```

### "No space left on device"

```bash
# Check available space
df -h /mnt/nas/mindex

# If full, clean old backups
find /mnt/nas/mindex/backups -mtime +30 -delete
```

### Container can't write to volume

```bash
# Check Docker volume
docker inspect mindex | grep -A 10 Mounts

# Fix permissions
sudo chown -R 1000:1000 /mnt/nas/mindex
```

### NAS not accessible

```bash
# Test network connectivity
ping 192.168.1.100

# Test SMB access
smbclient //192.168.1.100/mindex -U username
```

## Data Migration

### Import existing data to NAS:

```bash
# Stop MINDEX
docker-compose -f docker-compose.mindex.yml down

# Copy data to NAS
rsync -avz ./data/mindex/ /mnt/nas/mindex/

# Update config and restart
docker-compose -f docker-compose.mindex.yml up -d
```


# MINDEX NAS Storage Configuration

This guide explains how to configure MINDEX to use your NAS storage for persistent fungal data.

## Storage Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        MINDEX Storage Layout                             │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐  │
│  │   PRIMARY NAS    │    │   BACKUP NAS     │    │   LOCAL CACHE    │  │
│  │  (16TB Synology) │    │ (26TB Dream M.)  │    │   (Container)    │  │
│  ├──────────────────┤    ├──────────────────┤    ├──────────────────┤  │
│  │ /mnt/nas/mindex  │───▶│ /mnt/dream/mindex│    │   /app/data      │  │
│  │                  │    │                  │    │                  │  │
│  │ • mindex.db      │    │ • mindex.db.bak  │    │ • temp files     │  │
│  │ • images/        │    │ • images/        │    │ • session cache  │  │
│  │ • genomes/       │    │ • genomes/       │    │                  │  │
│  │ • sequences/     │    │ • sequences/     │    │                  │  │
│  └──────────────────┘    └──────────────────┘    └──────────────────┘  │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

## Required Storage Space

| Data Type | Estimated Size | Growth Rate |
|-----------|---------------|-------------|
| **Species Database** | 2-5 GB | 100 MB/month |
| **Observations** | 10-50 GB | 500 MB/month |
| **Images** | 500 GB - 2 TB | 50 GB/month |
| **Genome Sequences** | 1-5 TB | 100 GB/month |
| **GenBank Data** | 500 GB - 1 TB | 50 GB/month |

**Total Recommended**: 6-10 TB minimum, 16 TB recommended

## Windows Setup

### Step 1: Mount NAS Share

```powershell
# Create persistent network drive for Synology NAS
net use M: \\192.168.1.100\mindex /user:username password /persistent:yes

# Verify mount
Get-PSDrive M
```

### Step 2: Create Directory Structure

```powershell
# Create data directories
mkdir M:\mindex
mkdir M:\mindex\images
mkdir M:\mindex\genomes
mkdir M:\mindex\sequences
mkdir M:\mindex\backups
```

### Step 3: Configure Docker

Update `docker-compose.mindex.yml`:

```yaml
volumes:
  mindex_data:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: M:\mindex
```

Or set environment variable:

```powershell
$env:MINDEX_HOST_PATH = "M:\mindex"
docker-compose -f docker-compose.mindex.yml up -d
```

## Linux Setup

### Step 1: Install CIFS Utils

```bash
sudo apt-get install cifs-utils
```

### Step 2: Create Credentials File

```bash
sudo nano /etc/nas-creds

# Add:
username=your_nas_user
password=your_nas_password
domain=WORKGROUP
```

```bash
sudo chmod 600 /etc/nas-creds
```

### Step 3: Add to fstab

```bash
sudo nano /etc/fstab

# Add line for Synology NAS (16TB)
//192.168.1.100/mindex /mnt/nas/mindex cifs credentials=/etc/nas-creds,uid=1000,gid=1000,vers=3.0 0 0

# Add line for Dream Machine (26TB) - backup
//192.168.1.1/mindex /mnt/dream/mindex cifs credentials=/etc/nas-creds,uid=1000,gid=1000,vers=3.0 0 0
```

### Step 4: Mount

```bash
sudo mkdir -p /mnt/nas/mindex /mnt/dream/mindex
sudo mount -a
```

### Step 5: Verify

```bash
df -h | grep mindex
ls -la /mnt/nas/mindex
```

## Dream Machine Setup

The UniFi Dream Machine Pro (26TB) serves as backup storage:

### Configure SMB Share on Dream Machine

1. SSH into Dream Machine:
```bash
ssh root@192.168.1.1
```

2. Create share directory:
```bash
mkdir -p /mnt/data/mindex
```

3. Configure Samba (if not already):
```bash
# Install samba if needed
apt-get update && apt-get install samba

# Edit /etc/samba/smb.conf
[mindex]
    path = /mnt/data/mindex
    browsable = yes
    read only = no
    guest ok = no
```

## Environment Variables

Set these in your `.env` file or environment:

```bash
# Primary storage (Synology NAS)
MINDEX_NAS_PATH=/mnt/nas/mindex

# Backup storage (Dream Machine)
MINDEX_BACKUP_PATH=/mnt/dream/mindex

# For Docker on host machine
MINDEX_HOST_PATH=/mnt/nas/mindex  # Linux
# MINDEX_HOST_PATH=M:\mindex      # Windows
```

## Backup Strategy

### Automated Daily Backup

Add to crontab on the server:

```bash
# Daily backup at 3 AM
0 3 * * * rsync -avz /mnt/nas/mindex/ /mnt/dream/mindex/
```

### Or use Docker backup service:

```yaml
# In docker-compose.mindex.yml
services:
  mindex-backup:
    image: restic/restic
    volumes:
      - /mnt/nas/mindex:/source:ro
      - /mnt/dream/mindex:/backup
    environment:
      - RESTIC_REPOSITORY=/backup
      - RESTIC_PASSWORD=your_backup_password
    command: |
      backup /source --tag mindex
    depends_on:
      - mindex
```

## Monitoring Storage

### Check Database Size

```bash
# Connect to container
docker exec -it mindex sh

# Check database size
ls -lh /mnt/nas/mindex/mindex.db

# Check total storage
du -sh /mnt/nas/mindex/*
```

### Via API

```bash
curl http://localhost:8000/health | jq '.db_size_mb'
```

## Troubleshooting

### "Permission denied" on NAS mount

```bash
# Check mount options
mount | grep mindex

# Remount with correct UID
sudo mount -o remount,uid=1000,gid=1000 /mnt/nas/mindex
```

### "No space left on device"

```bash
# Check available space
df -h /mnt/nas/mindex

# If full, clean old backups
find /mnt/nas/mindex/backups -mtime +30 -delete
```

### Container can't write to volume

```bash
# Check Docker volume
docker inspect mindex | grep -A 10 Mounts

# Fix permissions
sudo chown -R 1000:1000 /mnt/nas/mindex
```

### NAS not accessible

```bash
# Test network connectivity
ping 192.168.1.100

# Test SMB access
smbclient //192.168.1.100/mindex -U username
```

## Data Migration

### Import existing data to NAS:

```bash
# Stop MINDEX
docker-compose -f docker-compose.mindex.yml down

# Copy data to NAS
rsync -avz ./data/mindex/ /mnt/nas/mindex/

# Update config and restart
docker-compose -f docker-compose.mindex.yml up -d
```

# MINDEX NAS Storage Configuration

This guide explains how to configure MINDEX to use your NAS storage for persistent fungal data.

## Storage Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        MINDEX Storage Layout                             │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐  │
│  │   PRIMARY NAS    │    │   BACKUP NAS     │    │   LOCAL CACHE    │  │
│  │  (16TB Synology) │    │ (26TB Dream M.)  │    │   (Container)    │  │
│  ├──────────────────┤    ├──────────────────┤    ├──────────────────┤  │
│  │ /mnt/nas/mindex  │───▶│ /mnt/dream/mindex│    │   /app/data      │  │
│  │                  │    │                  │    │                  │  │
│  │ • mindex.db      │    │ • mindex.db.bak  │    │ • temp files     │  │
│  │ • images/        │    │ • images/        │    │ • session cache  │  │
│  │ • genomes/       │    │ • genomes/       │    │                  │  │
│  │ • sequences/     │    │ • sequences/     │    │                  │  │
│  └──────────────────┘    └──────────────────┘    └──────────────────┘  │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

## Required Storage Space

| Data Type | Estimated Size | Growth Rate |
|-----------|---------------|-------------|
| **Species Database** | 2-5 GB | 100 MB/month |
| **Observations** | 10-50 GB | 500 MB/month |
| **Images** | 500 GB - 2 TB | 50 GB/month |
| **Genome Sequences** | 1-5 TB | 100 GB/month |
| **GenBank Data** | 500 GB - 1 TB | 50 GB/month |

**Total Recommended**: 6-10 TB minimum, 16 TB recommended

## Windows Setup

### Step 1: Mount NAS Share

```powershell
# Create persistent network drive for Synology NAS
net use M: \\192.168.1.100\mindex /user:username password /persistent:yes

# Verify mount
Get-PSDrive M
```

### Step 2: Create Directory Structure

```powershell
# Create data directories
mkdir M:\mindex
mkdir M:\mindex\images
mkdir M:\mindex\genomes
mkdir M:\mindex\sequences
mkdir M:\mindex\backups
```

### Step 3: Configure Docker

Update `docker-compose.mindex.yml`:

```yaml
volumes:
  mindex_data:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: M:\mindex
```

Or set environment variable:

```powershell
$env:MINDEX_HOST_PATH = "M:\mindex"
docker-compose -f docker-compose.mindex.yml up -d
```

## Linux Setup

### Step 1: Install CIFS Utils

```bash
sudo apt-get install cifs-utils
```

### Step 2: Create Credentials File

```bash
sudo nano /etc/nas-creds

# Add:
username=your_nas_user
password=your_nas_password
domain=WORKGROUP
```

```bash
sudo chmod 600 /etc/nas-creds
```

### Step 3: Add to fstab

```bash
sudo nano /etc/fstab

# Add line for Synology NAS (16TB)
//192.168.1.100/mindex /mnt/nas/mindex cifs credentials=/etc/nas-creds,uid=1000,gid=1000,vers=3.0 0 0

# Add line for Dream Machine (26TB) - backup
//192.168.1.1/mindex /mnt/dream/mindex cifs credentials=/etc/nas-creds,uid=1000,gid=1000,vers=3.0 0 0
```

### Step 4: Mount

```bash
sudo mkdir -p /mnt/nas/mindex /mnt/dream/mindex
sudo mount -a
```

### Step 5: Verify

```bash
df -h | grep mindex
ls -la /mnt/nas/mindex
```

## Dream Machine Setup

The UniFi Dream Machine Pro (26TB) serves as backup storage:

### Configure SMB Share on Dream Machine

1. SSH into Dream Machine:
```bash
ssh root@192.168.1.1
```

2. Create share directory:
```bash
mkdir -p /mnt/data/mindex
```

3. Configure Samba (if not already):
```bash
# Install samba if needed
apt-get update && apt-get install samba

# Edit /etc/samba/smb.conf
[mindex]
    path = /mnt/data/mindex
    browsable = yes
    read only = no
    guest ok = no
```

## Environment Variables

Set these in your `.env` file or environment:

```bash
# Primary storage (Synology NAS)
MINDEX_NAS_PATH=/mnt/nas/mindex

# Backup storage (Dream Machine)
MINDEX_BACKUP_PATH=/mnt/dream/mindex

# For Docker on host machine
MINDEX_HOST_PATH=/mnt/nas/mindex  # Linux
# MINDEX_HOST_PATH=M:\mindex      # Windows
```

## Backup Strategy

### Automated Daily Backup

Add to crontab on the server:

```bash
# Daily backup at 3 AM
0 3 * * * rsync -avz /mnt/nas/mindex/ /mnt/dream/mindex/
```

### Or use Docker backup service:

```yaml
# In docker-compose.mindex.yml
services:
  mindex-backup:
    image: restic/restic
    volumes:
      - /mnt/nas/mindex:/source:ro
      - /mnt/dream/mindex:/backup
    environment:
      - RESTIC_REPOSITORY=/backup
      - RESTIC_PASSWORD=your_backup_password
    command: |
      backup /source --tag mindex
    depends_on:
      - mindex
```

## Monitoring Storage

### Check Database Size

```bash
# Connect to container
docker exec -it mindex sh

# Check database size
ls -lh /mnt/nas/mindex/mindex.db

# Check total storage
du -sh /mnt/nas/mindex/*
```

### Via API

```bash
curl http://localhost:8000/health | jq '.db_size_mb'
```

## Troubleshooting

### "Permission denied" on NAS mount

```bash
# Check mount options
mount | grep mindex

# Remount with correct UID
sudo mount -o remount,uid=1000,gid=1000 /mnt/nas/mindex
```

### "No space left on device"

```bash
# Check available space
df -h /mnt/nas/mindex

# If full, clean old backups
find /mnt/nas/mindex/backups -mtime +30 -delete
```

### Container can't write to volume

```bash
# Check Docker volume
docker inspect mindex | grep -A 10 Mounts

# Fix permissions
sudo chown -R 1000:1000 /mnt/nas/mindex
```

### NAS not accessible

```bash
# Test network connectivity
ping 192.168.1.100

# Test SMB access
smbclient //192.168.1.100/mindex -U username
```

## Data Migration

### Import existing data to NAS:

```bash
# Stop MINDEX
docker-compose -f docker-compose.mindex.yml down

# Copy data to NAS
rsync -avz ./data/mindex/ /mnt/nas/mindex/

# Update config and restart
docker-compose -f docker-compose.mindex.yml up -d
```





# MINDEX NAS Storage Configuration

This guide explains how to configure MINDEX to use your NAS storage for persistent fungal data.

## Storage Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        MINDEX Storage Layout                             │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐  │
│  │   PRIMARY NAS    │    │   BACKUP NAS     │    │   LOCAL CACHE    │  │
│  │  (16TB Synology) │    │ (26TB Dream M.)  │    │   (Container)    │  │
│  ├──────────────────┤    ├──────────────────┤    ├──────────────────┤  │
│  │ /mnt/nas/mindex  │───▶│ /mnt/dream/mindex│    │   /app/data      │  │
│  │                  │    │                  │    │                  │  │
│  │ • mindex.db      │    │ • mindex.db.bak  │    │ • temp files     │  │
│  │ • images/        │    │ • images/        │    │ • session cache  │  │
│  │ • genomes/       │    │ • genomes/       │    │                  │  │
│  │ • sequences/     │    │ • sequences/     │    │                  │  │
│  └──────────────────┘    └──────────────────┘    └──────────────────┘  │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

## Required Storage Space

| Data Type | Estimated Size | Growth Rate |
|-----------|---------------|-------------|
| **Species Database** | 2-5 GB | 100 MB/month |
| **Observations** | 10-50 GB | 500 MB/month |
| **Images** | 500 GB - 2 TB | 50 GB/month |
| **Genome Sequences** | 1-5 TB | 100 GB/month |
| **GenBank Data** | 500 GB - 1 TB | 50 GB/month |

**Total Recommended**: 6-10 TB minimum, 16 TB recommended

## Windows Setup

### Step 1: Mount NAS Share

```powershell
# Create persistent network drive for Synology NAS
net use M: \\192.168.1.100\mindex /user:username password /persistent:yes

# Verify mount
Get-PSDrive M
```

### Step 2: Create Directory Structure

```powershell
# Create data directories
mkdir M:\mindex
mkdir M:\mindex\images
mkdir M:\mindex\genomes
mkdir M:\mindex\sequences
mkdir M:\mindex\backups
```

### Step 3: Configure Docker

Update `docker-compose.mindex.yml`:

```yaml
volumes:
  mindex_data:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: M:\mindex
```

Or set environment variable:

```powershell
$env:MINDEX_HOST_PATH = "M:\mindex"
docker-compose -f docker-compose.mindex.yml up -d
```

## Linux Setup

### Step 1: Install CIFS Utils

```bash
sudo apt-get install cifs-utils
```

### Step 2: Create Credentials File

```bash
sudo nano /etc/nas-creds

# Add:
username=your_nas_user
password=your_nas_password
domain=WORKGROUP
```

```bash
sudo chmod 600 /etc/nas-creds
```

### Step 3: Add to fstab

```bash
sudo nano /etc/fstab

# Add line for Synology NAS (16TB)
//192.168.1.100/mindex /mnt/nas/mindex cifs credentials=/etc/nas-creds,uid=1000,gid=1000,vers=3.0 0 0

# Add line for Dream Machine (26TB) - backup
//192.168.1.1/mindex /mnt/dream/mindex cifs credentials=/etc/nas-creds,uid=1000,gid=1000,vers=3.0 0 0
```

### Step 4: Mount

```bash
sudo mkdir -p /mnt/nas/mindex /mnt/dream/mindex
sudo mount -a
```

### Step 5: Verify

```bash
df -h | grep mindex
ls -la /mnt/nas/mindex
```

## Dream Machine Setup

The UniFi Dream Machine Pro (26TB) serves as backup storage:

### Configure SMB Share on Dream Machine

1. SSH into Dream Machine:
```bash
ssh root@192.168.1.1
```

2. Create share directory:
```bash
mkdir -p /mnt/data/mindex
```

3. Configure Samba (if not already):
```bash
# Install samba if needed
apt-get update && apt-get install samba

# Edit /etc/samba/smb.conf
[mindex]
    path = /mnt/data/mindex
    browsable = yes
    read only = no
    guest ok = no
```

## Environment Variables

Set these in your `.env` file or environment:

```bash
# Primary storage (Synology NAS)
MINDEX_NAS_PATH=/mnt/nas/mindex

# Backup storage (Dream Machine)
MINDEX_BACKUP_PATH=/mnt/dream/mindex

# For Docker on host machine
MINDEX_HOST_PATH=/mnt/nas/mindex  # Linux
# MINDEX_HOST_PATH=M:\mindex      # Windows
```

## Backup Strategy

### Automated Daily Backup

Add to crontab on the server:

```bash
# Daily backup at 3 AM
0 3 * * * rsync -avz /mnt/nas/mindex/ /mnt/dream/mindex/
```

### Or use Docker backup service:

```yaml
# In docker-compose.mindex.yml
services:
  mindex-backup:
    image: restic/restic
    volumes:
      - /mnt/nas/mindex:/source:ro
      - /mnt/dream/mindex:/backup
    environment:
      - RESTIC_REPOSITORY=/backup
      - RESTIC_PASSWORD=your_backup_password
    command: |
      backup /source --tag mindex
    depends_on:
      - mindex
```

## Monitoring Storage

### Check Database Size

```bash
# Connect to container
docker exec -it mindex sh

# Check database size
ls -lh /mnt/nas/mindex/mindex.db

# Check total storage
du -sh /mnt/nas/mindex/*
```

### Via API

```bash
curl http://localhost:8000/health | jq '.db_size_mb'
```

## Troubleshooting

### "Permission denied" on NAS mount

```bash
# Check mount options
mount | grep mindex

# Remount with correct UID
sudo mount -o remount,uid=1000,gid=1000 /mnt/nas/mindex
```

### "No space left on device"

```bash
# Check available space
df -h /mnt/nas/mindex

# If full, clean old backups
find /mnt/nas/mindex/backups -mtime +30 -delete
```

### Container can't write to volume

```bash
# Check Docker volume
docker inspect mindex | grep -A 10 Mounts

# Fix permissions
sudo chown -R 1000:1000 /mnt/nas/mindex
```

### NAS not accessible

```bash
# Test network connectivity
ping 192.168.1.100

# Test SMB access
smbclient //192.168.1.100/mindex -U username
```

## Data Migration

### Import existing data to NAS:

```bash
# Stop MINDEX
docker-compose -f docker-compose.mindex.yml down

# Copy data to NAS
rsync -avz ./data/mindex/ /mnt/nas/mindex/

# Update config and restart
docker-compose -f docker-compose.mindex.yml up -d
```

# MINDEX NAS Storage Configuration

This guide explains how to configure MINDEX to use your NAS storage for persistent fungal data.

## Storage Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        MINDEX Storage Layout                             │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐  │
│  │   PRIMARY NAS    │    │   BACKUP NAS     │    │   LOCAL CACHE    │  │
│  │  (16TB Synology) │    │ (26TB Dream M.)  │    │   (Container)    │  │
│  ├──────────────────┤    ├──────────────────┤    ├──────────────────┤  │
│  │ /mnt/nas/mindex  │───▶│ /mnt/dream/mindex│    │   /app/data      │  │
│  │                  │    │                  │    │                  │  │
│  │ • mindex.db      │    │ • mindex.db.bak  │    │ • temp files     │  │
│  │ • images/        │    │ • images/        │    │ • session cache  │  │
│  │ • genomes/       │    │ • genomes/       │    │                  │  │
│  │ • sequences/     │    │ • sequences/     │    │                  │  │
│  └──────────────────┘    └──────────────────┘    └──────────────────┘  │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

## Required Storage Space

| Data Type | Estimated Size | Growth Rate |
|-----------|---------------|-------------|
| **Species Database** | 2-5 GB | 100 MB/month |
| **Observations** | 10-50 GB | 500 MB/month |
| **Images** | 500 GB - 2 TB | 50 GB/month |
| **Genome Sequences** | 1-5 TB | 100 GB/month |
| **GenBank Data** | 500 GB - 1 TB | 50 GB/month |

**Total Recommended**: 6-10 TB minimum, 16 TB recommended

## Windows Setup

### Step 1: Mount NAS Share

```powershell
# Create persistent network drive for Synology NAS
net use M: \\192.168.1.100\mindex /user:username password /persistent:yes

# Verify mount
Get-PSDrive M
```

### Step 2: Create Directory Structure

```powershell
# Create data directories
mkdir M:\mindex
mkdir M:\mindex\images
mkdir M:\mindex\genomes
mkdir M:\mindex\sequences
mkdir M:\mindex\backups
```

### Step 3: Configure Docker

Update `docker-compose.mindex.yml`:

```yaml
volumes:
  mindex_data:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: M:\mindex
```

Or set environment variable:

```powershell
$env:MINDEX_HOST_PATH = "M:\mindex"
docker-compose -f docker-compose.mindex.yml up -d
```

## Linux Setup

### Step 1: Install CIFS Utils

```bash
sudo apt-get install cifs-utils
```

### Step 2: Create Credentials File

```bash
sudo nano /etc/nas-creds

# Add:
username=your_nas_user
password=your_nas_password
domain=WORKGROUP
```

```bash
sudo chmod 600 /etc/nas-creds
```

### Step 3: Add to fstab

```bash
sudo nano /etc/fstab

# Add line for Synology NAS (16TB)
//192.168.1.100/mindex /mnt/nas/mindex cifs credentials=/etc/nas-creds,uid=1000,gid=1000,vers=3.0 0 0

# Add line for Dream Machine (26TB) - backup
//192.168.1.1/mindex /mnt/dream/mindex cifs credentials=/etc/nas-creds,uid=1000,gid=1000,vers=3.0 0 0
```

### Step 4: Mount

```bash
sudo mkdir -p /mnt/nas/mindex /mnt/dream/mindex
sudo mount -a
```

### Step 5: Verify

```bash
df -h | grep mindex
ls -la /mnt/nas/mindex
```

## Dream Machine Setup

The UniFi Dream Machine Pro (26TB) serves as backup storage:

### Configure SMB Share on Dream Machine

1. SSH into Dream Machine:
```bash
ssh root@192.168.1.1
```

2. Create share directory:
```bash
mkdir -p /mnt/data/mindex
```

3. Configure Samba (if not already):
```bash
# Install samba if needed
apt-get update && apt-get install samba

# Edit /etc/samba/smb.conf
[mindex]
    path = /mnt/data/mindex
    browsable = yes
    read only = no
    guest ok = no
```

## Environment Variables

Set these in your `.env` file or environment:

```bash
# Primary storage (Synology NAS)
MINDEX_NAS_PATH=/mnt/nas/mindex

# Backup storage (Dream Machine)
MINDEX_BACKUP_PATH=/mnt/dream/mindex

# For Docker on host machine
MINDEX_HOST_PATH=/mnt/nas/mindex  # Linux
# MINDEX_HOST_PATH=M:\mindex      # Windows
```

## Backup Strategy

### Automated Daily Backup

Add to crontab on the server:

```bash
# Daily backup at 3 AM
0 3 * * * rsync -avz /mnt/nas/mindex/ /mnt/dream/mindex/
```

### Or use Docker backup service:

```yaml
# In docker-compose.mindex.yml
services:
  mindex-backup:
    image: restic/restic
    volumes:
      - /mnt/nas/mindex:/source:ro
      - /mnt/dream/mindex:/backup
    environment:
      - RESTIC_REPOSITORY=/backup
      - RESTIC_PASSWORD=your_backup_password
    command: |
      backup /source --tag mindex
    depends_on:
      - mindex
```

## Monitoring Storage

### Check Database Size

```bash
# Connect to container
docker exec -it mindex sh

# Check database size
ls -lh /mnt/nas/mindex/mindex.db

# Check total storage
du -sh /mnt/nas/mindex/*
```

### Via API

```bash
curl http://localhost:8000/health | jq '.db_size_mb'
```

## Troubleshooting

### "Permission denied" on NAS mount

```bash
# Check mount options
mount | grep mindex

# Remount with correct UID
sudo mount -o remount,uid=1000,gid=1000 /mnt/nas/mindex
```

### "No space left on device"

```bash
# Check available space
df -h /mnt/nas/mindex

# If full, clean old backups
find /mnt/nas/mindex/backups -mtime +30 -delete
```

### Container can't write to volume

```bash
# Check Docker volume
docker inspect mindex | grep -A 10 Mounts

# Fix permissions
sudo chown -R 1000:1000 /mnt/nas/mindex
```

### NAS not accessible

```bash
# Test network connectivity
ping 192.168.1.100

# Test SMB access
smbclient //192.168.1.100/mindex -U username
```

## Data Migration

### Import existing data to NAS:

```bash
# Stop MINDEX
docker-compose -f docker-compose.mindex.yml down

# Copy data to NAS
rsync -avz ./data/mindex/ /mnt/nas/mindex/

# Update config and restart
docker-compose -f docker-compose.mindex.yml up -d
```


# MINDEX NAS Storage Configuration

This guide explains how to configure MINDEX to use your NAS storage for persistent fungal data.

## Storage Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        MINDEX Storage Layout                             │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐  │
│  │   PRIMARY NAS    │    │   BACKUP NAS     │    │   LOCAL CACHE    │  │
│  │  (16TB Synology) │    │ (26TB Dream M.)  │    │   (Container)    │  │
│  ├──────────────────┤    ├──────────────────┤    ├──────────────────┤  │
│  │ /mnt/nas/mindex  │───▶│ /mnt/dream/mindex│    │   /app/data      │  │
│  │                  │    │                  │    │                  │  │
│  │ • mindex.db      │    │ • mindex.db.bak  │    │ • temp files     │  │
│  │ • images/        │    │ • images/        │    │ • session cache  │  │
│  │ • genomes/       │    │ • genomes/       │    │                  │  │
│  │ • sequences/     │    │ • sequences/     │    │                  │  │
│  └──────────────────┘    └──────────────────┘    └──────────────────┘  │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

## Required Storage Space

| Data Type | Estimated Size | Growth Rate |
|-----------|---------------|-------------|
| **Species Database** | 2-5 GB | 100 MB/month |
| **Observations** | 10-50 GB | 500 MB/month |
| **Images** | 500 GB - 2 TB | 50 GB/month |
| **Genome Sequences** | 1-5 TB | 100 GB/month |
| **GenBank Data** | 500 GB - 1 TB | 50 GB/month |

**Total Recommended**: 6-10 TB minimum, 16 TB recommended

## Windows Setup

### Step 1: Mount NAS Share

```powershell
# Create persistent network drive for Synology NAS
net use M: \\192.168.1.100\mindex /user:username password /persistent:yes

# Verify mount
Get-PSDrive M
```

### Step 2: Create Directory Structure

```powershell
# Create data directories
mkdir M:\mindex
mkdir M:\mindex\images
mkdir M:\mindex\genomes
mkdir M:\mindex\sequences
mkdir M:\mindex\backups
```

### Step 3: Configure Docker

Update `docker-compose.mindex.yml`:

```yaml
volumes:
  mindex_data:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: M:\mindex
```

Or set environment variable:

```powershell
$env:MINDEX_HOST_PATH = "M:\mindex"
docker-compose -f docker-compose.mindex.yml up -d
```

## Linux Setup

### Step 1: Install CIFS Utils

```bash
sudo apt-get install cifs-utils
```

### Step 2: Create Credentials File

```bash
sudo nano /etc/nas-creds

# Add:
username=your_nas_user
password=your_nas_password
domain=WORKGROUP
```

```bash
sudo chmod 600 /etc/nas-creds
```

### Step 3: Add to fstab

```bash
sudo nano /etc/fstab

# Add line for Synology NAS (16TB)
//192.168.1.100/mindex /mnt/nas/mindex cifs credentials=/etc/nas-creds,uid=1000,gid=1000,vers=3.0 0 0

# Add line for Dream Machine (26TB) - backup
//192.168.1.1/mindex /mnt/dream/mindex cifs credentials=/etc/nas-creds,uid=1000,gid=1000,vers=3.0 0 0
```

### Step 4: Mount

```bash
sudo mkdir -p /mnt/nas/mindex /mnt/dream/mindex
sudo mount -a
```

### Step 5: Verify

```bash
df -h | grep mindex
ls -la /mnt/nas/mindex
```

## Dream Machine Setup

The UniFi Dream Machine Pro (26TB) serves as backup storage:

### Configure SMB Share on Dream Machine

1. SSH into Dream Machine:
```bash
ssh root@192.168.1.1
```

2. Create share directory:
```bash
mkdir -p /mnt/data/mindex
```

3. Configure Samba (if not already):
```bash
# Install samba if needed
apt-get update && apt-get install samba

# Edit /etc/samba/smb.conf
[mindex]
    path = /mnt/data/mindex
    browsable = yes
    read only = no
    guest ok = no
```

## Environment Variables

Set these in your `.env` file or environment:

```bash
# Primary storage (Synology NAS)
MINDEX_NAS_PATH=/mnt/nas/mindex

# Backup storage (Dream Machine)
MINDEX_BACKUP_PATH=/mnt/dream/mindex

# For Docker on host machine
MINDEX_HOST_PATH=/mnt/nas/mindex  # Linux
# MINDEX_HOST_PATH=M:\mindex      # Windows
```

## Backup Strategy

### Automated Daily Backup

Add to crontab on the server:

```bash
# Daily backup at 3 AM
0 3 * * * rsync -avz /mnt/nas/mindex/ /mnt/dream/mindex/
```

### Or use Docker backup service:

```yaml
# In docker-compose.mindex.yml
services:
  mindex-backup:
    image: restic/restic
    volumes:
      - /mnt/nas/mindex:/source:ro
      - /mnt/dream/mindex:/backup
    environment:
      - RESTIC_REPOSITORY=/backup
      - RESTIC_PASSWORD=your_backup_password
    command: |
      backup /source --tag mindex
    depends_on:
      - mindex
```

## Monitoring Storage

### Check Database Size

```bash
# Connect to container
docker exec -it mindex sh

# Check database size
ls -lh /mnt/nas/mindex/mindex.db

# Check total storage
du -sh /mnt/nas/mindex/*
```

### Via API

```bash
curl http://localhost:8000/health | jq '.db_size_mb'
```

## Troubleshooting

### "Permission denied" on NAS mount

```bash
# Check mount options
mount | grep mindex

# Remount with correct UID
sudo mount -o remount,uid=1000,gid=1000 /mnt/nas/mindex
```

### "No space left on device"

```bash
# Check available space
df -h /mnt/nas/mindex

# If full, clean old backups
find /mnt/nas/mindex/backups -mtime +30 -delete
```

### Container can't write to volume

```bash
# Check Docker volume
docker inspect mindex | grep -A 10 Mounts

# Fix permissions
sudo chown -R 1000:1000 /mnt/nas/mindex
```

### NAS not accessible

```bash
# Test network connectivity
ping 192.168.1.100

# Test SMB access
smbclient //192.168.1.100/mindex -U username
```

## Data Migration

### Import existing data to NAS:

```bash
# Stop MINDEX
docker-compose -f docker-compose.mindex.yml down

# Copy data to NAS
rsync -avz ./data/mindex/ /mnt/nas/mindex/

# Update config and restart
docker-compose -f docker-compose.mindex.yml up -d
```

# MINDEX NAS Storage Configuration

This guide explains how to configure MINDEX to use your NAS storage for persistent fungal data.

## Storage Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        MINDEX Storage Layout                             │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐  │
│  │   PRIMARY NAS    │    │   BACKUP NAS     │    │   LOCAL CACHE    │  │
│  │  (16TB Synology) │    │ (26TB Dream M.)  │    │   (Container)    │  │
│  ├──────────────────┤    ├──────────────────┤    ├──────────────────┤  │
│  │ /mnt/nas/mindex  │───▶│ /mnt/dream/mindex│    │   /app/data      │  │
│  │                  │    │                  │    │                  │  │
│  │ • mindex.db      │    │ • mindex.db.bak  │    │ • temp files     │  │
│  │ • images/        │    │ • images/        │    │ • session cache  │  │
│  │ • genomes/       │    │ • genomes/       │    │                  │  │
│  │ • sequences/     │    │ • sequences/     │    │                  │  │
│  └──────────────────┘    └──────────────────┘    └──────────────────┘  │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

## Required Storage Space

| Data Type | Estimated Size | Growth Rate |
|-----------|---------------|-------------|
| **Species Database** | 2-5 GB | 100 MB/month |
| **Observations** | 10-50 GB | 500 MB/month |
| **Images** | 500 GB - 2 TB | 50 GB/month |
| **Genome Sequences** | 1-5 TB | 100 GB/month |
| **GenBank Data** | 500 GB - 1 TB | 50 GB/month |

**Total Recommended**: 6-10 TB minimum, 16 TB recommended

## Windows Setup

### Step 1: Mount NAS Share

```powershell
# Create persistent network drive for Synology NAS
net use M: \\192.168.1.100\mindex /user:username password /persistent:yes

# Verify mount
Get-PSDrive M
```

### Step 2: Create Directory Structure

```powershell
# Create data directories
mkdir M:\mindex
mkdir M:\mindex\images
mkdir M:\mindex\genomes
mkdir M:\mindex\sequences
mkdir M:\mindex\backups
```

### Step 3: Configure Docker

Update `docker-compose.mindex.yml`:

```yaml
volumes:
  mindex_data:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: M:\mindex
```

Or set environment variable:

```powershell
$env:MINDEX_HOST_PATH = "M:\mindex"
docker-compose -f docker-compose.mindex.yml up -d
```

## Linux Setup

### Step 1: Install CIFS Utils

```bash
sudo apt-get install cifs-utils
```

### Step 2: Create Credentials File

```bash
sudo nano /etc/nas-creds

# Add:
username=your_nas_user
password=your_nas_password
domain=WORKGROUP
```

```bash
sudo chmod 600 /etc/nas-creds
```

### Step 3: Add to fstab

```bash
sudo nano /etc/fstab

# Add line for Synology NAS (16TB)
//192.168.1.100/mindex /mnt/nas/mindex cifs credentials=/etc/nas-creds,uid=1000,gid=1000,vers=3.0 0 0

# Add line for Dream Machine (26TB) - backup
//192.168.1.1/mindex /mnt/dream/mindex cifs credentials=/etc/nas-creds,uid=1000,gid=1000,vers=3.0 0 0
```

### Step 4: Mount

```bash
sudo mkdir -p /mnt/nas/mindex /mnt/dream/mindex
sudo mount -a
```

### Step 5: Verify

```bash
df -h | grep mindex
ls -la /mnt/nas/mindex
```

## Dream Machine Setup

The UniFi Dream Machine Pro (26TB) serves as backup storage:

### Configure SMB Share on Dream Machine

1. SSH into Dream Machine:
```bash
ssh root@192.168.1.1
```

2. Create share directory:
```bash
mkdir -p /mnt/data/mindex
```

3. Configure Samba (if not already):
```bash
# Install samba if needed
apt-get update && apt-get install samba

# Edit /etc/samba/smb.conf
[mindex]
    path = /mnt/data/mindex
    browsable = yes
    read only = no
    guest ok = no
```

## Environment Variables

Set these in your `.env` file or environment:

```bash
# Primary storage (Synology NAS)
MINDEX_NAS_PATH=/mnt/nas/mindex

# Backup storage (Dream Machine)
MINDEX_BACKUP_PATH=/mnt/dream/mindex

# For Docker on host machine
MINDEX_HOST_PATH=/mnt/nas/mindex  # Linux
# MINDEX_HOST_PATH=M:\mindex      # Windows
```

## Backup Strategy

### Automated Daily Backup

Add to crontab on the server:

```bash
# Daily backup at 3 AM
0 3 * * * rsync -avz /mnt/nas/mindex/ /mnt/dream/mindex/
```

### Or use Docker backup service:

```yaml
# In docker-compose.mindex.yml
services:
  mindex-backup:
    image: restic/restic
    volumes:
      - /mnt/nas/mindex:/source:ro
      - /mnt/dream/mindex:/backup
    environment:
      - RESTIC_REPOSITORY=/backup
      - RESTIC_PASSWORD=your_backup_password
    command: |
      backup /source --tag mindex
    depends_on:
      - mindex
```

## Monitoring Storage

### Check Database Size

```bash
# Connect to container
docker exec -it mindex sh

# Check database size
ls -lh /mnt/nas/mindex/mindex.db

# Check total storage
du -sh /mnt/nas/mindex/*
```

### Via API

```bash
curl http://localhost:8000/health | jq '.db_size_mb'
```

## Troubleshooting

### "Permission denied" on NAS mount

```bash
# Check mount options
mount | grep mindex

# Remount with correct UID
sudo mount -o remount,uid=1000,gid=1000 /mnt/nas/mindex
```

### "No space left on device"

```bash
# Check available space
df -h /mnt/nas/mindex

# If full, clean old backups
find /mnt/nas/mindex/backups -mtime +30 -delete
```

### Container can't write to volume

```bash
# Check Docker volume
docker inspect mindex | grep -A 10 Mounts

# Fix permissions
sudo chown -R 1000:1000 /mnt/nas/mindex
```

### NAS not accessible

```bash
# Test network connectivity
ping 192.168.1.100

# Test SMB access
smbclient //192.168.1.100/mindex -U username
```

## Data Migration

### Import existing data to NAS:

```bash
# Stop MINDEX
docker-compose -f docker-compose.mindex.yml down

# Copy data to NAS
rsync -avz ./data/mindex/ /mnt/nas/mindex/

# Update config and restart
docker-compose -f docker-compose.mindex.yml up -d
```





