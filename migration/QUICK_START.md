# Quick Start Guide - Proxmox Production Migration

This guide provides the fastest path to migrate Mycosoft MAS to production Proxmox VMs.

## Prerequisites

- Proxmox server with 384GB+ RAM available
- NAS accessible on network
- Cloudflare account
- Ubuntu 22.04 LTS ISO downloaded
- SSH access to Proxmox server

## Step-by-Step Execution

### 1. Create VMs (5 minutes)

**On Proxmox server:**

```bash
# Copy migration scripts to Proxmox
scp -r migration/ root@proxmox-server:/root/

# Create VMs
ssh root@proxmox-server
cd /root/migration
chmod +x proxmox-vm-setup.sh
./proxmox-vm-setup.sh
```

**Or use Proxmox Web UI:**
- Create VM1: 256GB RAM, 16 cores, 2TB disk
- Create VM2: 64GB RAM, 8 cores, 500GB disk
- Attach Ubuntu 22.04 ISO to both VMs

### 2. Install Ubuntu (30 minutes)

**For each VM:**
1. Boot from ISO
2. Install Ubuntu (Server for VM1, Desktop for VM2)
3. Enable SSH during installation
4. Note the IP addresses assigned

### 3. Base Setup (10 minutes per VM)

**On VM1:**
```bash
# Transfer scripts
scp -r migration/ mycosoft@VM1_IP:/opt/mycosoft/

# Run setup
ssh mycosoft@VM1_IP
cd /opt/mycosoft/migration
chmod +x *.sh
./os-setup.sh
```

**On VM2:**
```bash
# Same process
scp -r migration/ mycosoft@VM2_IP:/home/mycosoft/
ssh mycosoft@VM2_IP
cd ~/migration
chmod +x *.sh
./os-setup.sh
```

### 4. Configure Network (5 minutes per VM)

**On each VM:**
```bash
./network-setup.sh
# Follow prompts to set static IP
```

### 5. Setup NAS (5 minutes, VM1 only)

**On VM1:**
```bash
./nas-setup.sh
# Follow prompts to configure NAS mount
```

### 6. Transfer Codebase (10-30 minutes)

**On Windows machine:**
```powershell
# Option 1: PowerShell script
cd migration
.\transfer-codebase.ps1 -VM1IP 192.168.1.100

# Option 2: Manual SCP
scp -r C:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas\* mycosoft@192.168.1.100:/opt/mycosoft/
```

### 7. Setup Production (15 minutes)

**On VM1:**
```bash
cd /opt/mycosoft
chmod +x migration/setup-production.sh

# Edit .env file first
nano .env  # Add your passwords and API keys

# Run setup
./migration/setup-production.sh
```

### 8. Migrate Databases (15 minutes)

**On Windows machine:**
```powershell
cd migration
.\database-migration.sh export
.\database-migration.sh import 192.168.1.100 mycosoft
```

**Or manually:**
```bash
# Export on Windows
docker exec mycosoft-postgres pg_dump -U mas mas > mas_backup.sql

# Import on VM1
scp mas_backup.sql mycosoft@192.168.1.100:/tmp/
ssh mycosoft@192.168.1.100
docker exec -i mycosoft-postgres psql -U mas -d mas < /tmp/mas_backup.sql
```

### 9. Setup Cloudflare Tunnel (10 minutes)

**On VM1:**
```bash
cd /opt/mycosoft/migration
./cloudflare-tunnel-setup.sh
# Follow prompts to authenticate and configure
```

### 10. Setup Backups (5 minutes)

**On Proxmox server or VM1:**
```bash
# Add to crontab
crontab -e
# Add: 0 2 * * * /opt/mycosoft/migration/daily-backup.sh
```

### 11. Setup VM2 (10 minutes)

**On VM2:**
```bash
cd ~/migration
./vm2-setup.sh
# Follow prompts
```

### 12. Verify Everything (5 minutes)

**On VM1:**
```bash
cd /opt/mycosoft
./migration/health-check.sh
```

**Test external access:**
- https://mycosoft.com (should work via Cloudflare)

## Total Time Estimate

- **Minimum**: 2-3 hours (if everything goes smoothly)
- **Realistic**: 4-6 hours (with troubleshooting)
- **Maximum**: 8-10 hours (if issues arise)

## Troubleshooting

### Services not starting
```bash
# Check logs
docker-compose -f docker-compose.prod.yml logs -f

# Restart
docker-compose -f docker-compose.prod.yml restart
```

### Can't connect to VM
- Check Proxmox console
- Verify network configuration
- Check firewall rules

### Database import fails
- Ensure PostgreSQL container is running
- Check file permissions
- Verify database credentials

## Next Steps

1. **Monitor for 24 hours** - Watch logs and metrics
2. **Test all features** - Verify everything works
3. **Update DNS** - If not done during Cloudflare setup
4. **Document issues** - Note any problems encountered
5. **Train team** - Share access and procedures

## Support

- **Runbook**: See `PRODUCTION_RUNBOOK.md`
- **Checklist**: See `MIGRATION_CHECKLIST.md`
- **Full Guide**: See `README.md`

## Emergency Rollback

If something goes wrong:

1. **Stop VM in Proxmox**
2. **Restore from backup** (if available)
3. **Or restore databases** from backups
4. **Contact support** if needed

---

**Good luck with your migration!**
