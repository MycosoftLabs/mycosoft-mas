# VM Infrastructure Upgrade Guide

This document outlines the steps to upgrade the Mycosoft VM from current specifications to production-ready specifications.

## Current Specifications (as of Jan 2026)

| Resource | Current | Target | Status |
|----------|---------|--------|--------|
| CPU Cores | 4 | 16 | Pending |
| RAM | 8 GB | 32 GB | Pending |
| Storage | 100 GB | 500 GB | Pending |

## Prerequisites

- Access to Proxmox web interface
- SSH access to VM (mycosoft@192.168.0.187)
- Root access on VM for disk operations
- Downtime window (15-30 minutes)

## Step 1: CPU and RAM Upgrade (Proxmox)

1. Access Proxmox web interface at `https://192.168.0.100:8006` (or your Proxmox IP)

2. Navigate to the Mycosoft VM

3. **Stop the VM**:
   - Click "Shutdown" or use console to: `sudo shutdown -h now`

4. **Upgrade CPU**:
   - Select the VM → Hardware → Processors
   - Set Cores to: **16**
   - Set Sockets: **1**
   - Click "OK"

5. **Upgrade RAM**:
   - Select the VM → Hardware → Memory
   - Set Memory to: **32768 MB** (32 GB)
   - Click "OK"

6. **Start the VM**:
   - Click "Start"

7. **Verify changes** (after VM boots):
   ```bash
   ssh mycosoft@192.168.0.187
   nproc  # Should show 16
   free -h  # Should show ~32 GB total
   ```

## Step 2: Storage Upgrade

### Option A: Expand Existing Disk (Recommended)

1. **In Proxmox**:
   - Select VM → Hardware → Hard Disk
   - Click "Resize disk"
   - Add **400 GB** (to reach 500 GB total)

2. **SSH into VM and expand partition**:
   ```bash
   ssh mycosoft@192.168.0.187
   
   # Check current disk layout
   lsblk
   df -h
   
   # If using LVM (Ubuntu default)
   sudo lvextend -l +100%FREE /dev/mapper/ubuntu--vg-ubuntu--lv
   sudo resize2fs /dev/mapper/ubuntu--vg-ubuntu--lv
   
   # If using standard partition (adjust /dev/sda as needed)
   sudo growpart /dev/sda 2
   sudo resize2fs /dev/sda2
   
   # Verify new size
   df -h
   ```

### Option B: Add Second Disk

1. **In Proxmox**:
   - Select VM → Hardware → Add → Hard Disk
   - Set Size to: **400 GB**
   - Storage: Select your storage pool

2. **SSH into VM and mount**:
   ```bash
   ssh mycosoft@192.168.0.187
   
   # Find new disk
   lsblk
   
   # Format (e.g., /dev/sdb)
   sudo mkfs.ext4 /dev/sdb
   
   # Create mount point
   sudo mkdir -p /data
   
   # Mount
   sudo mount /dev/sdb /data
   
   # Add to fstab for persistence
   echo "/dev/sdb /data ext4 defaults 0 2" | sudo tee -a /etc/fstab
   
   # Verify
   df -h
   ```

## Step 3: Move Docker Volumes to New Storage

If using Option B (second disk):

```bash
# Stop Docker
sudo systemctl stop docker

# Move Docker data
sudo mv /var/lib/docker /data/docker
sudo ln -s /data/docker /var/lib/docker

# Move Mycosoft data
sudo mv /opt/mycosoft /data/mycosoft
sudo ln -s /data/mycosoft /opt/mycosoft

# Start Docker
sudo systemctl start docker

# Verify containers
docker ps
```

## Step 4: Post-Upgrade Verification

Run this verification script:

```bash
#!/bin/bash
echo "=== VM Upgrade Verification ==="
echo ""
echo "CPU Cores: $(nproc)"
echo "Total RAM: $(free -h | awk '/^Mem:/ {print $2}')"
echo "Disk Usage:"
df -h / /data 2>/dev/null || df -h /
echo ""
echo "Docker Status:"
docker ps --format "table {{.Names}}\t{{.Status}}" | head -10
echo ""
echo "Container Health:"
docker ps --format "{{.Names}}: {{.Status}}" | grep -E "(healthy|unhealthy|starting)"
```

## Step 5: Update Monitoring Thresholds

After upgrade, update Grafana alert thresholds:

| Metric | Old Threshold | New Threshold |
|--------|---------------|---------------|
| CPU High | 80% of 4 cores | 80% of 16 cores |
| RAM High | 75% of 8 GB | 75% of 32 GB |
| Disk High | 80% of 100 GB | 80% of 500 GB |

## Estimated Downtime

| Step | Duration |
|------|----------|
| VM Shutdown | 1-2 min |
| Config changes in Proxmox | 5 min |
| VM Boot | 2-5 min |
| Disk expansion | 5-10 min |
| Verification | 5 min |
| **Total** | **15-30 min** |

## Rollback Plan

If issues occur:

1. Shutdown VM in Proxmox
2. Revert CPU/RAM to previous values
3. Start VM
4. Contact support if disk issues

## Post-Upgrade Tasks

- [ ] Verify all services healthy
- [ ] Run website smoke tests
- [ ] Check MycoBrain connectivity
- [ ] Update monitoring dashboards
- [ ] Document new baseline metrics
