# Mycosoft VM Quick Reference Card

*Print this for quick access to common commands*

---

## 🚀 Service Management

```bash
# Start all services
/opt/mycosoft/scripts/start-all.sh

# Stop all services
/opt/mycosoft/scripts/stop-all.sh

# Health check
/opt/mycosoft/scripts/health-check.sh

# View logs (all)
docker compose logs -f

# View specific service logs
docker compose logs -f website
docker compose logs -f n8n
docker compose logs -f mindex-api

# Restart specific service
docker compose restart <service_name>
```

---

## 📊 System Status

```bash
# Container status
docker ps

# Resource usage
docker stats --no-stream

# Disk space
df -h

# Memory
free -h

# CPU load
htop
```

---

## 🔧 Troubleshooting

```bash
# Restart Docker
sudo systemctl restart docker

# Check Cloudflare tunnel
sudo systemctl status cloudflared
sudo journalctl -u cloudflared -f

# Check firewall
sudo ufw status

# Test endpoints
curl http://localhost:3000/api/health
curl http://localhost:8000/health
curl http://localhost:5678/healthz
```

---

## 💾 Backups

```bash
# Database backup
/opt/mycosoft/scripts/backup-database.sh

# List backups
ls -la /opt/mycosoft/backups/postgres/

# Manual database export
docker exec mycosoft-postgres pg_dump -U mycosoft mycosoft_mas > backup.sql
```

---

## 🌐 Network

```bash
# VM IP address
hostname -I

# Test external connectivity
curl -I https://mycosoft.com

# Check open ports
sudo ss -tlnp
```

---

## 📁 Important Paths

| Path | Description |
|------|-------------|
| `/opt/mycosoft/` | Main installation directory |
| `/opt/mycosoft/mas/` | MAS repository |
| `/opt/mycosoft/website/` | Website repository |
| `/opt/mycosoft/backups/` | Backup storage |
| `/opt/mycosoft/logs/` | Application logs |
| `/opt/mycosoft/scripts/` | Helper scripts |
| `/opt/mycosoft/cloudflared/` | Tunnel configuration |

---

## 🔑 Service Ports

| Port | Service |
|------|---------|
| 3000 | Website (Next.js) |
| 5678 | n8n Workflows |
| 8000 | MINDEX API |
| 8001 | MAS Orchestrator |
| 8003 | MycoBrain |
| 3002 | Grafana |
| 9090 | Prometheus |
| 5432 | PostgreSQL |
| 6379 | Redis |

---

## 🔗 URLs

| Service | Internal | External |
|---------|----------|----------|
| Website | http://localhost:3000 | https://mycosoft.com |
| API | http://localhost:8000 | https://api.mycosoft.com |
| n8n | http://localhost:5678 | https://n8n.mycosoft.com |
| Grafana | http://localhost:3002 | https://grafana.mycosoft.com |

---

## 🆘 Emergency Commands

```bash
# Force stop all containers
docker stop $(docker ps -q)

# Remove all containers (DANGEROUS)
docker rm $(docker ps -aq)

# Restart VM (from SSH)
sudo reboot

# Check system logs
sudo journalctl -xe
```

---

*VM 103: mycosoft-sandbox | VM 104: mycosoft-prod*
*Last Updated: January 17, 2026*
