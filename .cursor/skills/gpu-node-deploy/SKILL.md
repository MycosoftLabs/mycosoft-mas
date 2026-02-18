# GPU Node Deploy Skill

Deploy containers and workloads to the GPU compute node (mycosoft-gpu01).

## When to Use

- Deploy PersonaPlex/Moshi voice containers
- Deploy Earth2 simulation containers
- Deploy ML inference containers
- Check GPU node status
- Manage GPU workloads

## Prerequisites

- SSH key configured (already set up via `ssh gpu01`)
- GPU node running at 192.168.0.190
- Docker images available

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

## Integration

After deploying, update environment variables:

```env
# In website .env.local or MAS .env
MOSHI_API_URL=http://192.168.0.190:8998
EARTH2_API_URL=http://192.168.0.190:8220
```

## Verification

```bash
# Test Moshi health
curl http://192.168.0.190:8998/health

# Test Earth2 health
curl http://192.168.0.190:8220/health
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
