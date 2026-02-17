# GPU Node Integration - Feb 13, 2026

## Overview

The `mycosoft-gpu01` GPU compute node (192.168.0.190) is now integrated into the Mycosoft MAS ecosystem. This document describes how to use it from Cursor agents and other system components.

## System Components Created

### 1. Cursor Sub-Agent: `gpu-node-ops`

**File:** `.cursor/agents/gpu-node-ops.md`

Use this agent when you need to:
- Deploy or manage GPU containers
- Check GPU status and memory
- Offload GPU workloads from dev machine
- Debug GPU-related issues

**Usage in chat:** `@gpu-node-ops deploy moshi-voice`

### 2. Skill: `gpu-node-deploy`

**File:** `.cursor/skills/gpu-node-deploy/SKILL.md`

Provides step-by-step instructions for deploying GPU workloads.

### 3. Python Client: `gpu_node_client.py`

**File:** `mycosoft_mas/integrations/gpu_node_client.py`

Programmatic access for MAS agents:

```python
from mycosoft_mas.integrations.gpu_node_client import GPUNodeClient, check_gpu_node

# Quick status check
status = await check_gpu_node()
print(status)  # {'status': 'online', 'gpu': {...}, 'containers': [...]}

# Deploy a service
client = GPUNodeClient()
await client.deploy_service("moshi-voice")

# Check GPU status
gpu = await client.get_gpu_status()
print(f"GPU: {gpu.name}, Utilization: {gpu.utilization_percent}%")

# List containers
containers = await client.list_containers()
```

### 4. MAS API Router

**File:** `mycosoft_mas/core/routers/gpu_node.py`

HTTP API available at `http://192.168.0.188:8001/api/gpu-node/`

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/gpu-node/health` | GET | Router health check |
| `/api/gpu-node/status` | GET | Full GPU node status |
| `/api/gpu-node/reachable` | GET | Check SSH connectivity |
| `/api/gpu-node/gpu` | GET | GPU-specific status |
| `/api/gpu-node/containers` | GET | List all containers |
| `/api/gpu-node/containers/{name}/logs` | GET | Get container logs |
| `/api/gpu-node/containers/{name}/running` | GET | Check if container running |
| `/api/gpu-node/deploy/container` | POST | Deploy custom container |
| `/api/gpu-node/deploy/service` | POST | Deploy known service |
| `/api/gpu-node/deploy/personaplex-split` | POST | Deploy bridge on gpu01 pointing to remote inference host |
| `/api/gpu-node/containers/{name}` | DELETE | Stop and remove container |
| `/api/gpu-node/services` | GET | List known services |
| `/api/gpu-node/services/{name}/health` | GET | Check service health |

## Full PersonaPlex (no edge-tts)

Voice is 100% Moshi with split deployment support:
- **Inference host**: RTX 5090 machine runs Moshi on port 8998
- **Logic host**: gpu01 (1080 Ti Ubuntu) runs PersonaPlex Bridge on port 8999

See `docs/FULL_PERSONAPLEX_NO_EDGE_FEB13_2026.md`.

## Known GPU Services

| Service | Image | Port | Description |
|---------|-------|------|-------------|
| `moshi-voice` | `mycosoft/moshi-voice:latest` | 8998 | Moshi STT + TTS (full PersonaPlex) |
| `earth2-inference` | `mycosoft/earth2-inference:latest` | 8220 | Earth2 simulation |
| `personaplex-bridge` | `mycosoft/personaplex-bridge:latest` | 8999 | PersonaPlex WebSocket bridge |

## Quick Commands

### From Cursor/Terminal

```bash
# Check GPU status
ssh gpu01 "nvidia-smi"

# Deploy Moshi voice
ssh gpu01 "docker run -d --name moshi-voice --gpus all -p 8998:8998 --restart unless-stopped mycosoft/moshi-voice:latest"

# Check running containers
ssh gpu01 "docker ps"

# View logs
ssh gpu01 "docker logs moshi-voice --tail 100"
```

### From Python

```python
import asyncio
from mycosoft_mas.integrations.gpu_node_client import check_gpu_node, deploy_gpu_service

async def main():
    # Quick check
    status = await check_gpu_node()
    print(f"GPU Node: {status['status']}")
    
    # Deploy Moshi
    result = await deploy_gpu_service("moshi-voice")
    print(f"Deploy: {result}")

asyncio.run(main())
```

### From MAS API (curl)

```bash
# Check status
curl http://192.168.0.188:8001/api/gpu-node/status

# Deploy service
curl -X POST http://192.168.0.188:8001/api/gpu-node/deploy/service \
  -H "Content-Type: application/json" \
  -d '{"service_name": "moshi-voice"}'

# Deploy split PersonaPlex:
# - inference host (5090 machine): 192.168.0.172:8998
# - logic/bridge host (gpu01): 192.168.0.190:8999
curl -X POST http://192.168.0.188:8001/api/gpu-node/deploy/personaplex-split \
  -H "Content-Type: application/json" \
  -d '{"inference_host":"192.168.0.172","inference_port":8998}'

# Check GPU
curl http://192.168.0.188:8001/api/gpu-node/gpu
```

## Network Integration

| Node | IP | Can Access GPU Node? | How |
|------|-----|---------------------|-----|
| Dev Machine | 192.168.0.x | Yes | SSH, HTTP |
| MAS VM (188) | 192.168.0.188 | Yes | HTTP API, SSH |
| MINDEX VM (189) | 192.168.0.189 | Yes | HTTP |
| Sandbox VM (187) | 192.168.0.187 | Yes | HTTP |
| n8n | 192.168.0.188:5678 | Yes | HTTP nodes |

## Environment Variables

For services that need to connect to GPU node:

```env
# In website .env.local or MAS .env
MOSHI_API_URL=http://192.168.0.190:8998
EARTH2_API_URL=http://192.168.0.190:8220
GPU_NODE_IP=192.168.0.190
```

## Port Assignments on GPU Node

| Port | Service | Status |
|------|---------|--------|
| 22 | SSH | Always on |
| 8998 | Moshi Voice | When deployed |
| 8999 | PersonaPlex Bridge | When deployed |
| 8220 | Earth2 Inference | When deployed |

## Making the API Available (MAS Restart)

The GPU node router is registered in `myca_main.py`. **For the API to be live, MAS on VM 188 must be restarted** after the code is deployed:

```bash
# On MAS VM (192.168.0.188)
sudo systemctl restart mas-orchestrator
# Or if running in Docker:
# docker stop myca-orchestrator-new && docker rm myca-orchestrator-new && docker run -d ...
```

Then verify:

```bash
curl http://192.168.0.188:8001/api/gpu-node/health
# Expected: {"status":"healthy","service":"gpu-node-router"}

curl http://192.168.0.188:8001/api/gpu-node/services
# Expected: list of moshi-voice, earth2-inference, personaplex-bridge
```

## Voice System Integration

For the **split voice architecture** (Moshi on 5090, PersonaPlex Bridge on gpu01, test-voice on website), see:

- **Voice stack (files, devices, SSH):** `docs/VOICE_SYSTEM_FILES_DEVICES_SSH_FEB13_2026.md`
- **Remote 5090 plan:** `docs/REMOTE_5090_INFERENCE_SPLIT_PLAN_FEB13_2026.md`
- **Verify script:** `scripts/voice-system-verify-and-start.ps1`

The GPU node API can deploy `personaplex-bridge` and `moshi-voice` on gpu01; for split setup (inference on 5090, bridge on gpu01), use SSH tunnel and run the bridge process manually as in the voice system doc.

## Troubleshooting

### Cannot Connect to GPU Node

```bash
# Test SSH
ssh -v gpu01

# Check node is up (from any VM)
ping 192.168.0.190

# Check SSH service
nc -zv 192.168.0.190 22
```

### GPU Not Available in Container

```bash
# Check NVIDIA runtime
ssh gpu01 "docker info | grep -i nvidia"

# Check GPU accessible
ssh gpu01 "nvidia-smi"

# Restart Docker
ssh gpu01 "sudo systemctl restart docker"
```

### Container Won't Start

```bash
# Check logs
ssh gpu01 "docker logs <container_name>"

# Check GPU memory
ssh gpu01 "nvidia-smi"

# Clear stopped containers
ssh gpu01 "docker system prune -f"
```

## Future Enhancements

1. **Auto-discovery** - MAS device registry integration for automatic GPU node registration
2. **Load balancing** - Route GPU tasks to least-loaded node (when more nodes added)
3. **Health monitoring** - Prometheus metrics from GPU node
4. **n8n integration** - GPU workload workflows
5. **Website UI** - GPU node dashboard on mycosoft.com
