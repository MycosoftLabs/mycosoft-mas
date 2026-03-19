# MYCA Export — Skill: GPU Node Deploy

**Export Date:** MAR16_2026  
**Skill Name:** gpu-node-deploy  
**Purpose:** Deploy containers and workloads to the GPU compute node (mycosoft-gpu01). Use when deploying PersonaPlex/Moshi voice, Earth2 simulation, ML inference, or checking GPU node status.  
**External Systems:** Base44, Claude, Perplexity, OpenAI, Grok — load when user requests GPU workload deployment.

---

## When to Use

- Deploy PersonaPlex/Moshi voice containers
- Deploy Earth2 simulation containers
- Deploy ML inference containers
- Check GPU node status
- Manage GPU workloads

## Prerequisites

- SSH key configured (ssh gpu01)
- GPU node running at 192.168.0.190
- Docker images available

## Commands

### Check GPU Status

```bash
ssh gpu01 "nvidia-smi"
```

### Deploy PersonaPlex Voice Service

```bash
docker build -t mycosoft/moshi-voice:latest -f services/personaplex-local/Dockerfile.gpu .
docker save mycosoft/moshi-voice:latest | ssh gpu01 "docker load"

ssh gpu01 "docker run -d --name moshi-voice \
  --gpus all \
  -p 8998:8998 \
  -e MOSHI_MODEL_PATH=/models \
  --restart unless-stopped \
  mycosoft/moshi-voice:latest"
```

### Deploy Earth2 Inference

```bash
docker build -t mycosoft/earth2-inference:latest -f services/earth2/Dockerfile .
docker save mycosoft/earth2-inference:latest | ssh gpu01 "docker load"

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

## Integration

After deploying, update environment variables:

```env
MOSHI_API_URL=http://192.168.0.190:8998
EARTH2_API_URL=http://192.168.0.190:8220
```

## Verification

```bash
curl http://192.168.0.190:8998/health
curl http://192.168.0.190:8220/health
```

## Troubleshooting

### Container Won't Start

```bash
ssh gpu01 "docker logs <container_name>"
ssh gpu01 "nvidia-smi"
ssh gpu01 "docker info | grep -i nvidia"
```

### Out of GPU Memory

```bash
ssh gpu01 "nvidia-smi"
ssh gpu01 "sudo nvidia-smi --gpu-reset"
```
