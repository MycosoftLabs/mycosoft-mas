# UDM Pro 26TB Storage Configuration

This document provides step-by-step instructions for configuring the 26TB drive attached to the UniFi Dream Machine Pro as the primary storage for MYCA.

## Prerequisites

- UniFi Dream Machine Pro with 26TB internal/USB drive
- Access to UniFi OS Console (https://192.168.0.1)
- Admin credentials for UniFi

## Step 1: Enable NAS Functionality

1. Log into UniFi OS at https://192.168.0.1
2. Navigate to **Settings** → **System** → **Storage**
3. Verify the 26TB drive is detected
4. Enable **Network Share** functionality

## Step 2: Create Directory Structure

Create the following directory structure on the UDM Pro storage:

```
/mycosoft/
├── databases/           # PostgreSQL, Redis, Qdrant data
│   ├── postgres/
│   ├── redis/
│   └── qdrant/
├── knowledge/           # Knowledge bases, vector stores
│   ├── qdrant/
│   ├── embeddings/
│   └── documents/
├── agents/              # Agent work directories, logs
│   ├── cycles/
│   ├── insights/
│   ├── workloads/
│   └── wisdom/
├── website/             # Static assets, uploads
│   ├── static/
│   ├── uploads/
│   └── cache/
├── backups/             # Automated backups
│   ├── daily/
│   ├── weekly/
│   └── monthly/
├── audit/               # Security audit logs
│   └── logs/
├── dev/                 # Development data (mycocomp)
│   ├── data/
│   └── logs/
└── shared/              # Shared between dev and prod
    ├── models/
    └── configs/
```

## Step 3: Configure Network Shares

### SMB Share (Windows/mycocomp)

Configure SMB share for Windows access from mycocomp:

1. In UniFi OS, go to **Storage** → **Shares**
2. Create a new share named `mycosoft`
3. Set path to `/mycosoft`
4. Enable SMB protocol
5. Configure user authentication

### NFS Share (Linux/Proxmox)

Configure NFS share for Proxmox nodes:

1. Enable NFS in UniFi storage settings
2. Export `/mycosoft` with the following options:
   - Allowed hosts: `192.168.0.0/24`
   - Access: Read/Write
   - Sync: Enabled

## Step 4: Mount Configuration

### Windows (mycocomp)

```powershell
# Run the mount script
.\scripts\mount_nas.ps1

# Or manually:
net use M: \\192.168.0.1\mycosoft /persistent:yes
```

### Linux/Proxmox Nodes

Add to `/etc/fstab`:

```bash
# NFS mount for MYCA storage
192.168.0.1:/mycosoft  /mnt/mycosoft  nfs  defaults,_netdev,nofail  0  0
```

Create mount point and mount:

```bash
sudo mkdir -p /mnt/mycosoft
sudo mount -a
```

## Step 5: Verify Configuration

Run the verification script:

```powershell
.\scripts\verify_storage.ps1
```

## Storage Allocation

Recommended allocation for 26TB:

| Directory | Allocation | Purpose |
|-----------|------------|---------|
| databases | 2TB | PostgreSQL, Redis, Qdrant |
| knowledge | 5TB | Vector stores, documents |
| agents | 1TB | Agent work data |
| website | 500GB | Static assets |
| backups | 10TB | Automated backups |
| audit | 100GB | Security logs |
| dev | 2TB | Development data |
| shared | 5TB | Shared models/configs |
| reserved | ~400GB | System overhead |

## Firewall Considerations

Ensure the following ports are allowed in UniFi firewall:

| Port | Protocol | Purpose |
|------|----------|---------|
| 445 | TCP | SMB |
| 139 | TCP | NetBIOS |
| 2049 | TCP/UDP | NFS |
| 111 | TCP/UDP | RPC (NFS) |

## Troubleshooting

### SMB Connection Failed

```powershell
# Check if SMB is accessible
Test-NetConnection -ComputerName 192.168.0.1 -Port 445
```

### NFS Mount Failed

```bash
# Check NFS exports
showmount -e 192.168.0.1

# Check connectivity
ping 192.168.0.1
```

## Next Steps

After configuring storage:

1. Run `.\scripts\mount_nas.ps1` on mycocomp
2. Mount storage on all Proxmox nodes
3. Configure Docker volumes to use NAS paths
4. Proceed to Phase 2: mycocomp development environment
