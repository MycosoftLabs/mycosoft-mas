# Mycosoft Master Installation Guide

*The Complete Guide to Deploying Mycosoft on a Fresh VM*

*Created: January 17, 2026*

---

## 📋 Overview

This master guide provides a complete walkthrough for deploying the entire Mycosoft system from scratch on a Proxmox VM.

### What Gets Deployed

| Stack | Services | Purpose |
|-------|----------|---------|
| **Always-On** | PostgreSQL, Redis, MINDEX API, Grafana, Prometheus | Core infrastructure (24/7) |
| **MAS** | n8n, MAS Orchestrator, MycoBrain, Myca Agent | AI agents & automation |
| **Website** | Next.js, CREP Collectors (Aircraft, Vessel, Satellite) | Public-facing website |
| **Infrastructure** | Cloudflare Tunnel, UFW Firewall, Fail2ban | Security & networking |

### Time Estimates

| Phase | Duration |
|-------|----------|
| VM Creation | 5 minutes |
| Ubuntu Installation | 10-15 minutes |
| Post-Install Setup | 10 minutes |
| Repository Transfer | 5-15 minutes |
| Docker Build | 15-30 minutes |
| Cloudflare Tunnel | 10 minutes |
| Testing | 10 minutes |
| **Total** | **~1-1.5 hours** |

---

## 🎯 Quick Start (TL;DR)

```bash
# 1. After Ubuntu installs, SSH in
ssh mycosoft@<VM_IP>

# 2. Run automated setup
curl -sSL https://raw.githubusercontent.com/MYCOSOFT/mycosoft-mas/main/scripts/setup-vm.sh | bash

# 3. Log out and back in
exit
ssh mycosoft@<VM_IP>

# 4. Clone repositories
cd /opt/mycosoft
git clone <your-mas-repo> mas
git clone <your-website-repo> website

# 5. Configure environment
cp mas/.env.example mas/.env
cp website/.env.local.example website/.env.local
# Edit both files with your secrets

# 6. Start everything
/opt/mycosoft/scripts/start-all.sh

# 7. Set up Cloudflare tunnel
cloudflared tunnel login
cloudflared tunnel create mycosoft-sandbox
# Configure routes...
```

---

## 📚 Detailed Documentation

### Phase 1: VM Creation

📄 **Reference:** `docs/PROXMOX_VM_SPECIFICATIONS.md`

| Setting | Sandbox (103) | Production (104) |
|---------|--------------|------------------|
| OS | Ubuntu 24.04.2 LTS | Ubuntu 24.04.2 LTS |
| CPU | 8 cores | 16 cores |
| RAM | 32 GB | 64 GB |
| Disk | 256 GB | 500 GB |
| BIOS | OVMF (UEFI) | OVMF (UEFI) |

### Phase 2: Ubuntu Installation

📄 **Reference:** `docs/SESSION_VM_CREATION_JAN17_2026.md`

During installation, configure:
- Language: English
- Keyboard: Your layout
- Network: DHCP (or static)
- Storage: Use entire disk with LVM
- Profile: 
  - Name: `Mycosoft Admin`
  - Server name: `mycosoft-sandbox`
  - Username: `mycosoft`
  - Password: Strong password
- OpenSSH: Install server

### Phase 3: Post-Installation Setup

📄 **Reference:** `docs/VM_POST_INSTALLATION_GUIDE.md`

```bash
# Automated (recommended)
curl -sSL https://raw.githubusercontent.com/MYCOSOFT/mycosoft-mas/main/scripts/setup-vm.sh | bash

# What this does:
# - Updates system packages
# - Installs Docker & Docker Compose
# - Creates /opt/mycosoft directory structure
# - Configures UFW firewall
# - Installs helper scripts
# - Enables fail2ban
```

### Phase 4: Deploy Stacks

📄 **Reference:** `docs/MYCOSOFT_STACK_DEPLOYMENT.md`

#### Transfer Code from Windows

```powershell
# From Windows PowerShell
$VM_IP = "192.168.0.XXX"

# Transfer MAS repository
scp -r "C:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas\*" mycosoft@${VM_IP}:/opt/mycosoft/mas/

# Transfer Website repository
scp -r "C:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website\*" mycosoft@${VM_IP}:/opt/mycosoft/website/
```

#### Configure Environment

```bash
# On VM
cd /opt/mycosoft/mas
cp .env.example .env
nano .env  # Edit with your secrets

cd /opt/mycosoft/website
cp .env.local.example .env.local
nano .env.local  # Edit with your secrets
```

#### Start Services

```bash
# Start in order
/opt/mycosoft/scripts/start-all.sh

# Verify
/opt/mycosoft/scripts/health-check.sh
```

### Phase 5: Cloudflare Tunnel

📄 **Reference:** `docs/CLOUDFLARE_TUNNEL_SETUP.md`

```bash
# Install cloudflared
curl -L --output cloudflared.deb https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
sudo dpkg -i cloudflared.deb

# Authenticate
cloudflared tunnel login

# Create tunnel
cloudflared tunnel create mycosoft-sandbox

# Configure routes (see full guide for config.yml)
# ...

# Install as service
sudo cloudflared service install
sudo systemctl enable cloudflared
sudo systemctl start cloudflared
```

### Phase 6: Maintenance

📄 **Reference:** `docs/VM_MAINTENANCE_BACKUP_GUIDE.md`

```bash
# Daily health check (automated via cron)
/opt/mycosoft/scripts/health-check.sh

# Database backups (automated via cron)
/opt/mycosoft/scripts/backup-database.sh

# Weekly updates
/opt/mycosoft/scripts/weekly-update.sh
```

---

## 🗂️ Complete Document List

### Core Deployment Guides

| Document | Purpose |
|----------|---------|
| `MASTER_INSTALLATION_GUIDE.md` | This overview document |
| `PROXMOX_VM_SPECIFICATIONS.md` | VM hardware specifications |
| `SESSION_VM_CREATION_JAN17_2026.md` | VM creation session log |
| `VM_POST_INSTALLATION_GUIDE.md` | Ubuntu post-install setup |
| `MYCOSOFT_STACK_DEPLOYMENT.md` | Docker stack deployment |
| `CLOUDFLARE_TUNNEL_SETUP.md` | Secure public access |
| `VM_MAINTENANCE_BACKUP_GUIDE.md` | Ongoing maintenance |
| `VM_QUICK_REFERENCE.md` | Printable command reference |

### API & Integration Guides

| Document | Purpose |
|----------|---------|
| `PROXMOX_UNIFI_API_REFERENCE.md` | Infrastructure API reference |
| `N8N_INTEGRATION_GUIDE.md` | n8n workflow integration |
| `CREP_INFRASTRUCTURE_DEPLOYMENT.md` | CREP data collectors |

### Scripts

| Script | Purpose |
|--------|---------|
| `scripts/setup-vm.sh` | Automated VM setup |
| (Built-in) `health-check.sh` | Service health monitoring |
| (Built-in) `start-all.sh` | Start all services |
| (Built-in) `stop-all.sh` | Stop all services |
| (Built-in) `backup-database.sh` | Database backup |

---

## ✅ Deployment Checklist

### Pre-Deployment

- [ ] Proxmox server accessible at 192.168.0.202
- [ ] Ubuntu 24.04.2 ISO available in Proxmox storage
- [ ] Cloudflare account with mycosoft.com domain
- [ ] GitHub access (if using private repos)
- [ ] API keys ready (OpenAI, Anthropic, etc.)

### VM Creation (Phase 1-2)

- [ ] VM 103 created with correct specifications
- [ ] Ubuntu Server 24.04.2 LTS installed
- [ ] SSH server installed during setup
- [ ] Username: `mycosoft`, strong password set

### System Setup (Phase 3)

- [ ] System updated (`apt update && apt upgrade`)
- [ ] Docker installed and running
- [ ] User added to docker group
- [ ] Directory structure created at `/opt/mycosoft/`
- [ ] UFW firewall configured
- [ ] Fail2ban enabled

### Application Deployment (Phase 4)

- [ ] MAS repository transferred to `/opt/mycosoft/mas/`
- [ ] Website repository transferred to `/opt/mycosoft/website/`
- [ ] Environment files configured (.env, .env.local)
- [ ] Always-On stack running (postgres, redis, mindex-api)
- [ ] MAS stack running (n8n, orchestrator, mycobrain)
- [ ] Website stack running (website, CREP collectors)
- [ ] All health checks passing

### Public Access (Phase 5)

- [ ] Cloudflared installed
- [ ] Tunnel created and authenticated
- [ ] Config.yml configured with routes
- [ ] DNS records created in Cloudflare
- [ ] Cloudflared running as service
- [ ] External URLs accessible

### Production Readiness

- [ ] Backup scripts configured in cron
- [ ] Monitoring alerts configured
- [ ] Documentation reviewed
- [ ] Team access configured
- [ ] Production VM (104) cloned from sandbox

---

## 🆘 Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| Docker permission denied | Log out and back in after `usermod -aG docker $USER` |
| Container won't start | Check logs: `docker compose logs <service>` |
| Port already in use | Find process: `sudo ss -tlnp \| grep <port>` |
| Cloudflare tunnel fails | Check credentials: `~/.cloudflared/` |
| SSH connection refused | Verify VM IP and firewall: `sudo ufw status` |

### Getting Help

1. Check service logs: `docker compose logs -f`
2. Check system logs: `sudo journalctl -xe`
3. Run health check: `/opt/mycosoft/scripts/health-check.sh`
4. Review documentation in `/opt/mycosoft/mas/docs/`

---

## 📞 Support

- **Documentation:** `/opt/mycosoft/mas/docs/`
- **Health Check:** `/opt/mycosoft/scripts/health-check.sh`
- **Logs:** `/opt/mycosoft/logs/`

---

*Document Version: 1.0*  
*Last Updated: January 17, 2026*
*VM Target: Ubuntu Server 24.04.2 LTS on Proxmox VE 8.4*
