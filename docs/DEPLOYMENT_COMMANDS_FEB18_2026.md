# Deployment Commands – Copy-Paste for Agent (Feb 18, 2026)

## Quick: Automated Script

```powershell
cd C:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website
Get-Content ".credentials.local" | ForEach-Object { if ($_ -match "^([^#=]+)=(.*)$") { [Environment]::SetEnvironmentVariable($matches[1].Trim(), $matches[2].Trim(), "Process") } }
python _rebuild_sandbox.py
```

---

## Manual: SSH Commands (if script fails)

```bash
ssh mycosoft@192.168.0.187
```

Then on VM:

```bash
cd /opt/mycosoft/website
git fetch origin
git reset --hard origin/main
docker build -t mycosoft-always-on-mycosoft-website:latest --no-cache .
docker stop mycosoft-website 2>/dev/null || true
docker rm mycosoft-website 2>/dev/null || true
docker run -d --name mycosoft-website -p 3000:3000 \
  -v /opt/mycosoft/media/website/assets:/app/public/assets:ro \
  -e MAS_API_URL=http://192.168.0.188:8001 \
  -e MYCOBRAIN_SERVICE_URL=http://192.168.0.187:8003 \
  -e MYCOBRAIN_API_URL=http://192.168.0.187:8003 \
  --restart unless-stopped mycosoft-always-on-mycosoft-website:latest
sleep 10
curl -s -o /dev/null -w "%{http_code}" http://localhost:3000
```

---

## Post-Deploy

- **Cloudflare:** Purge Everything
- **Verify:** https://sandbox.mycosoft.com/
