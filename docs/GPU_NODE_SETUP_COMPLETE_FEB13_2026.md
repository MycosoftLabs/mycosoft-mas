# GPU Node Setup Complete - Feb 13, 2026

## System Summary

| Property | Value |
|----------|-------|
| **Hostname** | `mycosoft-gpu01` |
| **IP Address** | `192.168.0.190` (static via DHCP reservation) |
| **OS** | Ubuntu 22.04.5 LTS Server |
| **Kernel** | 5.15.0-170-generic |
| **GPU** | NVIDIA GeForce GTX 1080 Ti (11GB VRAM) |
| **NVIDIA Driver** | 535.288.01 |
| **CUDA Version** | 12.2 |
| **Docker** | 29.2.1 with NVIDIA Container Toolkit |

## Quick Access

```bash
# From any terminal on your main PC:
ssh gpu01

# Or explicitly:
ssh mycosoft@192.168.0.190
```

## Security Configuration

- **SSH**: Key-based authentication only (password disabled)
- **Firewall (UFW)**: Active, only port 22 (SSH) allowed
- **Root Login**: Disabled
- **Unattended Upgrades**: Enabled

## Installed Tools

| Tool | Purpose |
|------|---------|
| `htop` | Process monitoring |
| `nvtop` | GPU monitoring |
| `tmux` | Terminal multiplexer |
| `git` | Version control |
| `curl`, `wget` | HTTP clients |
| `jq` | JSON processing |
| `python3`, `pip3`, `venv` | Python environment |

## Validation Commands

```bash
# Check GPU
nvidia-smi

# Check Docker GPU access
docker run --rm --gpus all nvidia/cuda:12.2.0-base-ubuntu22.04 nvidia-smi

# Check services
systemctl status docker
systemctl status ssh

# Check firewall
sudo ufw status verbose

# Monitor GPU in real-time
nvtop
```

## Network Configuration

| Service | IP | Purpose |
|---------|-----|---------|
| Sandbox VM | 192.168.0.187 | Website Docker |
| MAS VM | 192.168.0.188 | Multi-Agent System |
| MINDEX VM | 192.168.0.189 | Database + Vector Store |
| **GPU Node** | 192.168.0.190 | GPU Compute |

## Files Created

| File | Location | Purpose |
|------|----------|---------|
| Bootstrap script | `scripts/gpu-node/mycosoft-gpu-node-bootstrap.sh` | Automated setup |
| SSH helper | `scripts/gpu-node/ssh_helper.py` | Remote management |
| Runbook | `scripts/gpu-node/GPU_NODE_RUNBOOK_FEB12_2026.md` | Installation steps |

## Next Steps for GPU Workloads

1. **PersonaPlex/Moshi**: Deploy voice processing container
2. **Earth2**: Deploy Earth2 simulation container
3. **n8n Integration**: Configure n8n to route GPU tasks to this node

## Maintenance Commands

```bash
# Update system
ssh gpu01 "sudo apt update && sudo apt upgrade -y"

# Check disk space
ssh gpu01 "df -h"

# View logs
ssh gpu01 "sudo journalctl -xe"

# Reboot
ssh gpu01 "sudo reboot"
```

## Troubleshooting

### SSH Connection Issues
```bash
# Test with verbose output
ssh -v gpu01

# Check if SSH service is running (from another node)
curl -s --connect-timeout 5 telnet://192.168.0.190:22
```

### GPU Not Detected
```bash
# Check driver loaded
ssh gpu01 "lsmod | grep nvidia"

# Reload driver
ssh gpu01 "sudo modprobe nvidia"
```

### Docker GPU Issues
```bash
# Check NVIDIA runtime configured
ssh gpu01 "docker info | grep -i nvidia"

# Restart Docker
ssh gpu01 "sudo systemctl restart docker"
```

---

**Setup completed**: February 13, 2026
**Setup by**: MYCA Coding Agent via Cursor
