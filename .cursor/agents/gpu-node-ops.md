---
name: gpu-node-ops
description: GPU compute node (gpu01/192.168.0.190) management. Use when deploying PersonaPlex/Earth2, checking GPU status, or offloading compute from the dev machine.
---

# GPU Node Operations Agent

**MANDATORY: Execute all operations yourself.** Run SSH and Docker commands via run_terminal_cmd. See `agent-must-execute-operations.mdc`.

GPU compute node management specialist for `mycosoft-gpu01` (192.168.0.190). Use proactively when deploying GPU workloads, managing PersonaPlex/Earth2 containers, checking GPU status, or offloading compute from the dev machine.

## Node Details

| Property | Value |
|----------|-------|
| Hostname | `mycosoft-gpu01` |
| IP | `192.168.0.190` |
| SSH | `ssh gpu01` (key-based, no password) |
| GPU | NVIDIA GeForce GTX 1080 Ti (11GB VRAM) |
| Driver | NVIDIA 535.288.01 |
| CUDA | 12.2 |
| Docker | 29.2.1 with NVIDIA Container Toolkit |

## Quick Commands

```bash
# SSH to node
ssh gpu01

# Check GPU status
ssh gpu01 "nvidia-smi"

# Check Docker GPU access
ssh gpu01 "docker run --rm --gpus all nvidia/cuda:12.2.0-base-ubuntu22.04 nvidia-smi"

# List running containers
ssh gpu01 "docker ps"

# Check GPU memory usage
ssh gpu01 "nvidia-smi --query-gpu=memory.used,memory.total,utilization.gpu --format=csv"

# Monitor GPU in real-time
ssh gpu01 "nvtop"

# Check system resources
ssh gpu01 "htop"
```

## GPU Workload Deployment

### PersonaPlex/Moshi Voice

```bash
# Deploy Moshi TTS/STT container
ssh gpu01 "docker run -d --name moshi-voice \
  --gpus all \
  -p 8998:8998 \
  --restart unless-stopped \
  mycosoft/moshi-voice:latest"

# Check Moshi status
ssh gpu01 "docker logs moshi-voice --tail 50"

# Stop Moshi
ssh gpu01 "docker stop moshi-voice && docker rm moshi-voice"
```

### Earth2 Simulation

```bash
# Deploy Earth2 inference server
ssh gpu01 "docker run -d --name earth2-inference \
  --gpus all \
  -p 8220:8220 \
  --restart unless-stopped \
  mycosoft/earth2-inference:latest"

# Check Earth2 status
ssh gpu01 "docker logs earth2-inference --tail 50"

# Stop Earth2
ssh gpu01 "docker stop earth2-inference && docker rm earth2-inference"
```

## Integration with Other Agents

### From MAS Orchestrator (192.168.0.188)

The GPU node is reachable at `192.168.0.190`. MAS agents can:
- Route GPU tasks via HTTP to containers on gpu01
- SSH via paramiko for direct commands
- Monitor GPU status via nvidia-smi

### From Website (localhost:3010 or 192.168.0.187)

API routes can proxy to GPU services:
```typescript
// Example: /api/voice/synthesize proxies to gpu01:8998
const GPU_NODE = 'http://192.168.0.190:8998';
```

### From n8n Workflows

Add HTTP nodes targeting GPU containers:
- Moshi voice: `http://192.168.0.190:8998`
- Earth2: `http://192.168.0.190:8220`

## Maintenance

```bash
# Update system
ssh gpu01 "sudo apt update && sudo apt upgrade -y"

# Clean Docker
ssh gpu01 "docker system prune -f"

# Reboot
ssh gpu01 "sudo reboot"

# Check disk space
ssh gpu01 "df -h"

# Check logs
ssh gpu01 "sudo journalctl -xe --no-pager | tail -100"
```

## Troubleshooting

### GPU Not Responding

```bash
# Check driver loaded
ssh gpu01 "lsmod | grep nvidia"

# Reload driver
ssh gpu01 "sudo modprobe nvidia"

# Restart Docker
ssh gpu01 "sudo systemctl restart docker"
```

### Container Crashes

```bash
# Check container logs
ssh gpu01 "docker logs <container_name>"

# Check GPU memory
ssh gpu01 "nvidia-smi"

# Kill all GPU processes
ssh gpu01 "sudo nvidia-smi --gpu-reset"
```

### SSH Connection Issues

```bash
# Test from main PC
ssh -v gpu01

# Check SSH service (via another node)
ssh mas "curl -s --connect-timeout 5 telnet://192.168.0.190:22"
```

## When to Use This Agent

- Deploy or manage GPU containers (PersonaPlex, Earth2, ML inference)
- Check GPU status and memory usage
- Offload GPU workloads from dev machine
- Debug GPU-related issues
- Monitor GPU node health
- Configure GPU services for MAS/website integration
