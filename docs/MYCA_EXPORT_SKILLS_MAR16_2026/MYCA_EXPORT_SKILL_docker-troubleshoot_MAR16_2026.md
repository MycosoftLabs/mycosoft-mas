# MYCA Export — Skill: Docker Troubleshoot

**Export Date:** MAR16_2026  
**Skill Name:** docker-troubleshoot  
**Purpose:** Debug Docker container issues including crashes, OOM kills, daemon failures, and build errors. Use when containers won't start, keep restarting, or Docker daemon is unresponsive.  
**External Systems:** Base44, Claude, Perplexity, OpenAI, Grok — load when user reports Docker container issues.

---

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
free -m
df -h
docker system df
```

## Common Issues

### Container keeps restarting

```bash
docker inspect <container> --format='{{.State.ExitCode}}'
# Exit code 137 = OOM killed
# Exit code 1 = Application error
# Exit code 0 = Normal exit

dmesg | grep -i "oom\|killed"
```

### Out of memory (OOM)

```bash
docker run -d --memory=2g --memory-swap=4g ...
docker system prune -f
docker builder prune -f
docker image prune -a -f
```

### Docker daemon unresponsive

```bash
sudo systemctl status docker
sudo systemctl restart docker
sudo journalctl -u docker --tail 50
```

### Disk full preventing builds

```bash
docker container prune -f
docker image prune -a -f
docker builder prune -a -f
docker system prune -a -f --volumes
```

### Build failures

```bash
docker build --no-cache -t image:latest .
docker build --progress=plain -t image:latest .
```

## VM-Specific Recovery

### Sandbox VM (187) - Website container crash

```bash
ssh mycosoft@192.168.0.187
docker restart mycosoft-website
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
