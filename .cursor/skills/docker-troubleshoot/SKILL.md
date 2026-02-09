---
name: docker-troubleshoot
description: Debug Docker container issues including crashes, OOM kills, daemon failures, and build errors. Use when containers won't start, keep restarting, or Docker daemon is unresponsive.
---

# Docker Troubleshooting

## Quick Diagnosis

### Step 1: Check container status

```bash
docker ps -a --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```

Look for containers in `Exited`, `Restarting`, or `Dead` state.

### Step 2: Check container logs

```bash
docker logs <container_name> --tail 100
docker logs <container_name> --tail 100 --timestamps
```

### Step 3: Check system resources

```bash
# Memory
free -m
# Disk
df -h
# Docker disk usage
docker system df
```

## Common Issues

### Container keeps restarting

```bash
# Check exit code
docker inspect <container> --format='{{.State.ExitCode}}'
# Exit code 137 = OOM killed
# Exit code 1 = Application error
# Exit code 0 = Normal exit

# Check OOM kills
dmesg | grep -i "oom\|killed"
```

### Out of memory (OOM)

```bash
# Add memory limits to container
docker run -d --memory=2g --memory-swap=4g ...

# Clean up Docker cache
docker system prune -f
docker builder prune -f
docker image prune -a -f
```

### Docker daemon unresponsive

```bash
# Check daemon status
sudo systemctl status docker

# Restart Docker daemon
sudo systemctl restart docker

# If daemon won't start, check logs
sudo journalctl -u docker --tail 50
```

### Disk full preventing builds

```bash
# Remove all stopped containers
docker container prune -f
# Remove unused images
docker image prune -a -f
# Remove build cache
docker builder prune -a -f
# Nuclear option (removes everything)
docker system prune -a -f --volumes
```

### Build failures

```bash
# Build with no cache
docker build --no-cache -t image:latest .
# Build with verbose output
docker build --progress=plain -t image:latest .
```

## VM-Specific Recovery

### Sandbox VM (187) - Website container crash

```bash
ssh mycosoft@192.168.0.187
docker restart mycosoft-website
# If restart fails, rebuild using deploy-website-sandbox skill
```

### MAS VM (188) - Orchestrator crash

```bash
ssh mycosoft@192.168.0.188
docker restart myca-orchestrator-new
# Or: sudo systemctl restart mas-orchestrator
```

## Prevention

- Set memory limits on all containers
- Run `docker system prune -f` after rebuilds
- Monitor disk space (`df -h`) before building
- Use `--restart unless-stopped` for production containers
