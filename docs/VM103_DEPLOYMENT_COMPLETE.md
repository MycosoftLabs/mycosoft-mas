# VM 103 Deployment Complete - January 17, 2026

## Summary

Successfully deployed Mycosoft sandbox VM on Proxmox with full Docker stack.

## VM Specifications

| Property | Value |
|----------|-------|
| **VM ID** | 103 |
| **Name** | mycosoft-sandbox |
| **IP Address** | 192.168.0.187 |
| **MAC Address** | bc:24:11:9d:9f:55 |
| **OS** | Ubuntu 24.04.2 LTS |
| **Kernel** | 6.8.0-90-generic |
| **CPU** | 4 cores |
| **RAM** | 8 GB |
| **Disk** | 100 GB (local-lvm) |
| **Network** | vmbr0 (bridge) |

## Access Credentials

```
SSH: ssh mycosoft@192.168.0.187
Password: REDACTED_VM_SSH_PASSWORD
```

## Installed Software

| Software | Version |
|----------|---------|
| Docker | 29.1.5 |
| Docker Compose | v5.0.1 |
| Cloudflared | 2025.11.1 |
| OpenSSH Server | Installed |
| QEMU Guest Agent | Installed |

## Running Docker Containers

| Container | Image | Port | Status |
|-----------|-------|------|--------|
| mycosoft-website | node:20-alpine | 3000 | Running |
| mindex-api | python:3.11-slim | 8000 | Running |
| mycobrain-service | python:3.11-slim | 8003 | Running |
| mycosoft-postgres | postgres:15-alpine | 5432 | Running |
| mycosoft-redis | redis:7-alpine | 6379 | Running |

## Service URLs (Local Network)

- Website: http://192.168.0.187:3000
- MINDEX API: http://192.168.0.187:8000
- MycoBrain: http://192.168.0.187:8003
- PostgreSQL: 192.168.0.187:5432
- Redis: 192.168.0.187:6379

## Cloudflare Tunnel Setup (Next Steps)

Cloudflared is installed. To expose services publicly:

```bash
# SSH into VM
ssh mycosoft@192.168.0.187

# Login to Cloudflare (opens browser)
cloudflared tunnel login

# Create tunnel
cloudflared tunnel create mycosoft-sandbox

# Create config file
cat > ~/.cloudflared/config.yml << 'EOF'
tunnel: <TUNNEL_ID>
credentials-file: /home/mycosoft/.cloudflared/<TUNNEL_ID>.json

ingress:
  - hostname: sandbox.mycosoft.com
    service: http://localhost:3000
  - hostname: api-sandbox.mycosoft.com
    service: http://localhost:8000
  - hostname: brain-sandbox.mycosoft.com
    service: http://localhost:8003
  - service: http_status:404
EOF

# Route DNS
cloudflared tunnel route dns mycosoft-sandbox sandbox.mycosoft.com

# Run as service
sudo cloudflared service install
sudo systemctl enable --now cloudflared
```

## Docker Compose Location

```
/home/mycosoft/mycosoft/docker-compose.yml
```

## Common Commands

```bash
# SSH into VM
ssh mycosoft@192.168.0.187

# View running containers
sudo docker ps

# View logs
sudo docker logs mycosoft-website

# Restart stack
cd ~/mycosoft && sudo docker compose restart

# Update stack
cd ~/mycosoft && sudo docker compose pull && sudo docker compose up -d

# Stop stack
cd ~/mycosoft && sudo docker compose down
```

## Proxmox Management

```bash
# Via Proxmox Web UI
https://192.168.0.202:8006

# Via API
curl -k -H "Authorization: PVEAPIToken=root@pam!cursor_mycocomp=9b86f08b-40ff-4eb9-b41b-93bc9e11700f" \
  https://192.168.0.202:8006/api2/json/nodes/pve/qemu/103/status/current

# QEMU Guest Agent commands (from Proxmox host)
qm guest cmd 103 network-get-interfaces
```

## Automation Scripts Created

| Script | Purpose |
|--------|---------|
| `scripts/install_docker_vm.py` | Installs Docker on VM |
| `scripts/deploy_mycosoft_stack.py` | Deploys Docker stack |
| `scripts/install_cloudflared.py` | Installs Cloudflare tunnel |
| `scripts/vm-setup-commands.sh` | Manual setup reference |
| `scripts/proxmox-vm-control.ps1` | Proxmox API control |

## Next Steps for Production (VM 104)

1. Clone VM 103 to VM 104
2. Increase resources (8 CPU, 16 GB RAM, 200 GB disk)
3. Configure production Cloudflare tunnel
4. Set up automated backups
5. Configure monitoring (Prometheus/Grafana)

---

*Deployment completed by Cursor AI on January 17, 2026*
