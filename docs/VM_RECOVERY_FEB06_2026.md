# VM Recovery Report - February 6, 2026

## Issue
The Sandbox VM (192.168.0.187) Docker daemon crashed with:
- 54GB memory usage from corrupted Docker state
- Stale buildkit mounts (read-only file system errors)
- Panic: nil pointer dereference in dockerd
- Website container not running

## Resolution Steps

1. **VM Reboot** - Required to clear corrupted Docker memory and stale mounts
2. **Docker Restart** - Clean state after reboot, memory down to 1.6GB
3. **Website Container** - Started using existing image with correct environment variables

## Key Configuration

```bash
docker run -d --name mycosoft-website \
  -p 3000:3000 \
  -e NODE_ENV=production \
  -e MYCOBRAIN_SERVICE_URL=http://192.168.0.172:8765 \
  -e MAS_API_URL=http://mycosoft-mas-mas-orchestrator-1:8000 \
  -e N8N_LOCAL_URL=http://mycosoft-mas-n8n-1:5678 \
  -e MINDEX_API_BASE_URL=http://mindex-api:8000 \
  -e MINDEX_API_URL=http://mindex-api:8000 \
  -e MINDEX_API_KEY=local-dev-key \
  --restart unless-stopped \
  mycosoft-always-on-mycosoft-website:latest
```

## Current Status

| Component | Status | Details |
|-----------|--------|---------|
| VM | Running | 192.168.0.187, 1.6GB/62GB memory |
| Docker | Running | Clean state |
| Website | Running | Port 3000, healthy |
| MycoBrain | Connected | COM7 device via 192.168.0.172:8765 |
| sandbox.mycosoft.com | Working | 200 OK |

## MycoBrain Device

- **Port**: COM7
- **Device ID**: mycobrain-10:B4:1D:E3:3B:C4
- **Status**: Connected with live BME688 sensor data
- **Route**: sandbox.mycosoft.com → Cloudflare → VM:3000 → 192.168.0.172:8765

## Lessons Learned

1. Docker buildkit can leave stale mounts that cause read-only errors
2. K3s (Kubernetes) was consuming resources - disabled
3. Always use existing images when compose build fails due to missing files
4. VM reboot is sometimes the cleanest solution for corrupted Docker state
