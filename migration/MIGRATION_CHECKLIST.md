# Mycosoft Production Migration Checklist

Use this checklist to track migration progress.

## Pre-Migration

- [ ] Proxmox server accessible
- [ ] Sufficient resources available (384GB RAM, storage)
- [ ] NAS accessible and configured
- [ ] Network plan documented (IP addresses, gateway)
- [ ] Cloudflare account ready
- [ ] All API keys collected
- [ ] Backup of current system completed

## VM Creation

- [ ] VM1 created in Proxmox (256GB RAM, 16 cores, 2TB disk)
- [ ] VM2 created in Proxmox (64GB RAM, 8 cores, 500GB disk)
- [ ] Ubuntu 22.04 ISO downloaded
- [ ] VM1 booted from ISO
- [ ] VM2 booted from ISO

## OS Installation

- [ ] Ubuntu Server installed on VM1
- [ ] Ubuntu Desktop installed on VM2
- [ ] SSH enabled on both VMs
- [ ] Base setup script run on VM1 (`os-setup.sh`)
- [ ] Base setup script run on VM2 (`os-setup.sh`)

## Network Configuration

- [ ] VM1 static IP configured (192.168.1.100)
- [ ] VM2 static IP configured (192.168.1.101)
- [ ] Network connectivity tested
- [ ] Firewall rules configured on VM1
- [ ] DNS resolution working

## NAS Setup

- [ ] NAS mount configured on VM1
- [ ] Data directories created on NAS
- [ ] Mount tested and persistent
- [ ] Permissions configured

## Codebase Migration

- [ ] Codebase transferred to VM1
- [ ] Files verified on VM1
- [ ] Git repositories synced
- [ ] Environment variables configured

## Docker Setup

- [ ] Docker installed on VM1
- [ ] Docker Compose installed
- [ ] Production docker-compose.yml created
- [ ] .env file configured with passwords

## Database Migration

- [ ] PostgreSQL backup created from local
- [ ] Redis backup created from local
- [ ] Qdrant backup created from local
- [ ] Backups transferred to VM1
- [ ] PostgreSQL restored on VM1
- [ ] Redis restored on VM1
- [ ] Qdrant restored on VM1
- [ ] Database connections verified

## Service Deployment

- [ ] Infrastructure services started (PostgreSQL, Redis, Qdrant)
- [ ] MAS Orchestrator built and started
- [ ] Website built and started
- [ ] MycoBrain service started
- [ ] Voice services started
- [ ] Monitoring services started (Prometheus, Grafana)
- [ ] n8n started
- [ ] All services healthy

## Cloudflare Tunnel

- [ ] Cloudflared installed on VM1
- [ ] Cloudflare authentication completed
- [ ] Tunnel created
- [ ] Configuration file created
- [ ] DNS routes configured
- [ ] Tunnel service running
- [ ] External access tested

## Backup Setup

- [ ] Backup script created
- [ ] Cron job configured
- [ ] Backup storage verified
- [ ] Manual backup tested
- [ ] Restore procedure tested

## VM2 Setup

- [ ] VS Code installed
- [ ] Cursor IDE installed (if available)
- [ ] Development tools installed
- [ ] Access to VM1 configured
- [ ] Connectivity tested

## Verification

- [ ] Health check script created
- [ ] All services responding
- [ ] Website accessible internally
- [ ] Website accessible via Cloudflare
- [ ] API endpoints working
- [ ] Database queries successful
- [ ] Monitoring dashboards accessible

## Documentation

- [ ] Production runbook created
- [ ] Migration documentation complete
- [ ] Troubleshooting guide created
- [ ] Contact information documented

## Post-Migration

- [ ] DNS records updated (if needed)
- [ ] SSL certificates verified
- [ ] Monitoring alerts configured
- [ ] Team trained on new infrastructure
- [ ] Old system decommissioned (after verification period)

## Rollback Plan

- [ ] Rollback procedure documented
- [ ] Backup restoration tested
- [ ] Emergency contacts updated

---

## Notes

- Migration should be completed in single session if possible
- Test each step before proceeding to next
- Keep backups of everything
- Document any issues encountered
- Verify all services before considering migration complete
