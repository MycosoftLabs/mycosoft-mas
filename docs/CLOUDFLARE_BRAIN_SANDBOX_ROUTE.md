# Cloudflare Tunnel Configuration for brain-sandbox

This document describes the Cloudflare tunnel routes for the MycoBrain service.

## Current Status: ✅ CONFIGURED

The routes are configured via **Cloudflare Dashboard** (not config.yml):

| # | Hostname | Path | Service |
|---|----------|------|---------|
| 1 | sandbox.mycosoft.com | * | http://localhost:3000 |
| 2 | api-sandbox.mycosoft.com | * | http://localhost:8000 |
| 3 | brain-sandbox.mycosoft.com | * | http://localhost:8003 |

**Note:** Routes are managed via Cloudflare Zero Trust Dashboard, not the local config.yml file.

## Verify Configuration

Test the routes:
```bash
# From VM
curl http://localhost:8003/health

# From external
curl https://brain-sandbox.mycosoft.com/health
curl https://sandbox.mycosoft.com/api/mycobrain/health
```

## Port Mapping

| Service    | Internal Port | External URL                              |
|------------|---------------|-------------------------------------------|
| Website    | 3000          | https://sandbox.mycosoft.com/             |
| MINDEX API | 8000          | https://api-sandbox.mycosoft.com/         |
| MycoBrain  | 8003          | https://brain-sandbox.mycosoft.com/       |

## Verification Script

Run this on the VM to verify the configuration:

```bash
#!/bin/bash
echo "=== MycoBrain Health Check ==="

# Check if MycoBrain is running
if curl -sf http://localhost:8003/health > /dev/null; then
    echo "[OK] MycoBrain is running on port 8003"
else
    echo "[FAIL] MycoBrain is not responding on port 8003"
fi

# Check Cloudflared status
if systemctl is-active --quiet cloudflared; then
    echo "[OK] Cloudflared is running"
else
    echo "[FAIL] Cloudflared is not running"
fi

# Test external access
echo ""
echo "Testing external URLs..."
curl -sf https://brain-sandbox.mycosoft.com/health && echo "[OK] brain-sandbox accessible" || echo "[FAIL] brain-sandbox not accessible"
```

## Troubleshooting

### 502 Bad Gateway
- MycoBrain container is not running
- Check: `docker ps | grep mycobrain`

### 404 Not Found
- Ingress rule missing or misconfigured
- Check cloudflared logs: `journalctl -u cloudflared -n 50`

### Connection Refused
- MycoBrain not listening on correct port
- Check: `curl http://localhost:8003/health`
