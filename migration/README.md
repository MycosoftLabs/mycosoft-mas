# Mycosoft Production Migration Guide

This directory contains all scripts and configurations needed to migrate the Mycosoft MAS system to Proxmox VMs.

## Quick Start

### 1. Create VMs in Proxmox

```bash
# On Proxmox server
chmod +x migration/proxmox-vm-setup.sh
./migration/proxmox-vm-setup.sh
```

### 2. Install Ubuntu on VMs

- Boot VM1 and VM2 from Ubuntu 22.04 LTS ISO
- Install Ubuntu (Server for VM1, Desktop for VM2)
- After installation, SSH into each VM and run:

```bash
chmod +x migration/os-setup.sh
./migration/os-setup.sh
```

### 3. Configure Network

```bash
# On VM1 and VM2
chmod +x migration/network-setup.sh
./migration/network-setup.sh
```

### 4. Setup NAS Mount (VM1 only)

```bash
# On VM1
chmod +x migration/nas-setup.sh
./migration/nas-setup.sh
```

### 5. Transfer Codebase

```bash
# On Windows machine
chmod +x migration/codebase-transfer.sh
./migration/codebase-transfer.sh 192.168.1.100 mycosoft
```

### 6. Setup Production Environment (VM1)

```bash
# SSH to VM1
ssh mycosoft@192.168.1.100

# Run setup
cd /opt/mycosoft
chmod +x migration/setup-production.sh
./migration/setup-production.sh
```

### 7. Migrate Databases

```bash
# On Windows machine - Export
chmod +x migration/database-migration.sh
./migration/database-migration.sh export

# Import to VM1
./migration/database-migration.sh import 192.168.1.100 mycosoft
```

### 8. Setup Cloudflare Tunnel (VM1)

```bash
# On VM1
chmod +x migration/cloudflare-tunnel-setup.sh
./migration/cloudflare-tunnel-setup.sh
```

### 9. Setup Daily Backups

```bash
# On Proxmox server or VM1
chmod +x migration/daily-backup.sh

# Add to crontab (daily at 2 AM)
crontab -e
# Add: 0 2 * * * /opt/mycosoft/migration/daily-backup.sh
```

## File Structure

```
migration/
├── README.md                      # This file
├── proxmox-vm-setup.sh           # Create VMs in Proxmox
├── os-setup.sh                   # Ubuntu base setup
├── network-setup.sh               # Network configuration
├── nas-setup.sh                  # NAS mount setup
├── codebase-transfer.sh          # Transfer codebase from Windows
├── database-migration.sh         # Export/import databases
├── docker-compose.prod.yml       # Production Docker Compose
├── cloudflare-tunnel-setup.sh    # Cloudflare tunnel setup
├── daily-backup.sh               # Daily backup script
├── health-check.sh               # Health check script
└── setup-production.sh           # Complete production setup
```

## VM Specifications

### VM1: Production (mycosoft-production)
- RAM: 256GB
- CPU: 16 cores (2 sockets)
- Storage: 2TB SSD
- OS: Ubuntu 22.04 LTS Server
- IP: 192.168.1.100 (adjust as needed)

### VM2: Code Operator (mycosoft-operator)
- RAM: 64GB
- CPU: 8 cores
- Storage: 500GB SSD
- OS: Ubuntu 22.04 LTS Desktop
- IP: 192.168.1.101 (adjust as needed)

## Services

All services run in Docker containers on VM1:

- **Website**: Port 3000
- **MAS Orchestrator**: Port 8001
- **MycoBrain Service**: Port 8003
- **PostgreSQL**: Port 5432
- **Redis**: Port 6379
- **Qdrant**: Port 6333
- **Prometheus**: Port 9090
- **Grafana**: Port 3002
- **n8n**: Port 5678

## Troubleshooting

### Services not starting
```bash
# Check logs
docker-compose -f docker-compose.prod.yml logs -f [service-name]

# Restart service
docker-compose -f docker-compose.prod.yml restart [service-name]
```

### Database connection issues
```bash
# Check PostgreSQL
docker exec mycosoft-postgres psql -U mas -d mas -c "SELECT version();"

# Check Redis
docker exec mycosoft-redis redis-cli PING
```

### Cloudflare tunnel not working
```bash
# Check status
sudo systemctl status cloudflared

# View logs
sudo journalctl -u cloudflared -f
```

### NAS mount issues
```bash
# Check mount
mountpoint /mnt/mycosoft-nas

# Remount
sudo mount -a
```

## Health Checks

Run health check script:
```bash
./migration/health-check.sh
```

## Backup and Restore

### Daily Backups
Backups run automatically at 2 AM daily. To restore:

1. Stop VM in Proxmox
2. Restore from backup in Proxmox UI
3. Start VM
4. Verify services: `./migration/health-check.sh`

### Manual Backup
```bash
./migration/daily-backup.sh
```

## Support

For issues or questions, check:
- Production runbook: `/opt/mycosoft/docs/PRODUCTION_RUNBOOK.md`
- Service logs: `docker-compose -f docker-compose.prod.yml logs`
- System logs: `journalctl -xe`
