# GPU Node Deploy Skill

Deploy containers and workloads to the GPU compute node (mycosoft-gpu01).

## When to Use

- Deploy PersonaPlex/Moshi voice stack (Legion 4080B voice host)
- Deploy Earth2 Studio API (Legion 4080A Earth-2 host, WSL Linux)
- Deploy ML inference containers (optional Docker path)
- Register 24/7 startup on Windows Legions (`scripts/gpu-node/windows/*24x7*.ps1`)
- Check GPU node status

## Topology (UniFi LAN, April 2026)

| Role | IP | SSH user (default) | Services |
|------|-----|-------------------|----------|
| Voice / PersonaPlex / Ollama (Nemotron) | 192.168.0.241 | `owner1` or `mycosoft` | Moshi 8998, Bridge 8999, Ollama 11434 |
| Earth-2 / CREP inference | 192.168.0.249 | `owner2` or `mycosoft` | `earth2_api_server` 8220 (WSL) |

Legacy single-node docs may reference 192.168.0.190; prefer split defaults in `mycosoft_mas/integrations/gpu_node_client.py`.

## Prerequisites

- SSH key configured to each Legion
- NVIDIA driver + `nvidia-smi` on host
- For voice: `Setup-PersonaPlex-VoiceHost.ps1`, `personaplex-repo`, local model weights (real data only)
- For Earth-2: `Invoke-WSLGPUNodeSetup.ps1 -Role Earth2` so `earth2studio` exists in WSL venv

## Commands

### Check GPU Status

```bash
ssh gpu01 "nvidia-smi"
```

### Deploy PersonaPlex Voice Service

```bash
# Build and push image first (from MAS repo)
docker build -t mycosoft/moshi-voice:latest -f services/personaplex-local/Dockerfile.gpu .
docker save mycosoft/moshi-voice:latest | ssh gpu01 "docker load"

# Deploy on GPU node
ssh gpu01 "docker run -d --name moshi-voice \
  --gpus all \
  -p 8998:8998 \
  -e MOSHI_MODEL_PATH=/models \
  --restart unless-stopped \
  mycosoft/moshi-voice:latest"
```

### Deploy Earth2 Inference

```bash
# Build and push image
docker build -t mycosoft/earth2-inference:latest -f services/earth2/Dockerfile .
docker save mycosoft/earth2-inference:latest | ssh gpu01 "docker load"

# Deploy on GPU node
ssh gpu01 "docker run -d --name earth2-inference \
  --gpus all \
  -p 8220:8220 \
  --restart unless-stopped \
  mycosoft/earth2-inference:latest"
```

### Check Running Containers

```bash
ssh gpu01 "docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'"
```

### View Container Logs

```bash
ssh gpu01 "docker logs <container_name> --tail 100"
```

### Stop and Remove Container

```bash
ssh gpu01 "docker stop <container_name> && docker rm <container_name>"
```

### Check GPU Memory

```bash
ssh gpu01 "nvidia-smi --query-gpu=name,memory.used,memory.total,utilization.gpu --format=csv"
```

## 24/7 Windows services (Legions)

On **voice** host (241), after repo + venv + models exist:

```powershell
cd <mycosoft-mas>\scripts\gpu-node\windows
.\Start-LegionVoice-24x7.ps1
# optional: logon startup
.\Register-MycosoftLegionStartup.ps1 -Role Voice
```

On **Earth-2** host (249), after WSL venv + repo in `/root/mycosoft-mas`:

```powershell
.\Start-LegionEarth2API-24x7.ps1
.\Register-MycosoftLegionStartup.ps1 -Role Earth2
```

## Integration

MAS orchestrator (VM 188) and website should point at LAN services:

```env
# MAS: Nemotron / Ollama on voice GPU (not 188 unless Ollama runs there)
NEMOTRON_HOST=192.168.0.241
NEMOTRON_HTTP_PORT=11434
OLLAMA_BASE_URL=http://192.168.0.241:11434

EARTH2_API_URL=http://192.168.0.249:8220

# Website test-voice: bridge on voice host (sandbox/production)
PERSONAPLEX_BRIDGE_URL=http://192.168.0.241:8999
NEXT_PUBLIC_PERSONAPLEX_BRIDGE_URL=http://192.168.0.241:8999
```

## Verification

```bash
# Voice: bridge (from MAS or dev PC)
curl http://192.168.0.241:8999/health

# Earth-2 API
curl http://192.168.0.249:8220/health

# Ollama on voice host
curl http://192.168.0.241:11434/api/tags
```

## Troubleshooting

### Container Won't Start

```bash
# Check Docker logs
ssh gpu01 "docker logs <container_name>"

# Check GPU available
ssh gpu01 "nvidia-smi"

# Check Docker GPU runtime
ssh gpu01 "docker info | grep -i nvidia"
```

### Out of GPU Memory

```bash
# Check what's using memory
ssh gpu01 "nvidia-smi"

# Kill all GPU processes
ssh gpu01 "sudo nvidia-smi --gpu-reset"
```
