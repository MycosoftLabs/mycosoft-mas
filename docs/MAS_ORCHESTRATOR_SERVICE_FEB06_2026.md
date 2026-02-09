# MAS Orchestrator Service Configuration
**Date:** February 6, 2026  
**Status:** ALWAYS ON - Systemd Service  
**VM:** 192.168.0.188

---

## Service Status

The MAS Orchestrator is now configured as a systemd service that:
- **Starts automatically on boot**
- **Restarts automatically if it crashes**
- **Runs continuously 24/7**

---

## Service Details

| Property | Value |
|----------|-------|
| Service Name | `mas-orchestrator` |
| Port | 8001 |
| Host | 192.168.0.188 |
| User | mycosoft |
| Working Directory | `/home/mycosoft/mycosoft/mas` |
| Python | `/home/mycosoft/mycosoft/mas/venv/bin/python` |
| Entry Point | `mycosoft_mas.core.myca_main` |

---

## Endpoints

| Endpoint | Description |
|----------|-------------|
| `http://192.168.0.188:8001/health` | Health check |
| `http://192.168.0.188:8001/docs` | API documentation (Swagger) |
| `http://192.168.0.188:8001/scientific/*` | Scientific API |
| `http://192.168.0.188:8001/bio/*` | Bio-computing API |
| `http://192.168.0.188:8001/autonomous/*` | Autonomous experiments API |

---

## Service Management

### Check Status
```bash
ssh mycosoft@192.168.0.188 "systemctl status mas-orchestrator"
```

### Restart Service
```bash
ssh mycosoft@192.168.0.188 "sudo systemctl restart mas-orchestrator"
```

### View Logs
```bash
ssh mycosoft@192.168.0.188 "sudo journalctl -u mas-orchestrator -f"
```

### Stop Service (not recommended)
```bash
ssh mycosoft@192.168.0.188 "sudo systemctl stop mas-orchestrator"
```

---

## Systemd Service File

Location: `/etc/systemd/system/mas-orchestrator.service`

```ini
[Unit]
Description=MYCA MAS Orchestrator
After=network.target

[Service]
Type=simple
User=mycosoft
WorkingDirectory=/home/mycosoft/mycosoft/mas
Environment=PYTHONPATH=/home/mycosoft/mycosoft/mas
ExecStart=/home/mycosoft/mycosoft/mas/venv/bin/python -m mycosoft_mas.core.myca_main
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

---

## VM Credentials

| Property | Value |
|----------|-------|
| Host | 192.168.0.188 |
| Username | mycosoft |
| Password | REDACTED_VM_SSH_PASSWORD |
| SSH | `ssh mycosoft@192.168.0.188` |

---

## Health Check

Quick verification that the service is running:

```python
import urllib.request
response = urllib.request.urlopen('http://192.168.0.188:8001/health')
print(response.read().decode())
# {"status":"ok","service":"mas","version":"0.1.0"}
```

---

## Troubleshooting

### Service not starting
```bash
# Check logs
ssh mycosoft@192.168.0.188 "sudo journalctl -u mas-orchestrator -n 50"

# Check Python environment
ssh mycosoft@192.168.0.188 "/home/mycosoft/mycosoft/mas/venv/bin/python -c 'import mycosoft_mas'"
```

### Port not listening
```bash
# Check if port is in use
ssh mycosoft@192.168.0.188 "ss -tlnp | grep 8001"

# Kill any rogue processes
ssh mycosoft@192.168.0.188 "sudo fuser -k 8001/tcp"
```

### Restart after code changes
```bash
# Pull latest code and restart
ssh mycosoft@192.168.0.188 "cd /home/mycosoft/mycosoft/mas && git pull && sudo systemctl restart mas-orchestrator"
```

---

## Setup Script

The setup script used to configure this service is at:
`mycosoft-mas/_setup_mas_vm.py`

To re-run setup:
```bash
python _setup_mas_vm.py
```

---

## Next Steps

Now that the MAS Orchestrator is always running:
1. The scientific dashboard will show live data
2. API calls from the website will succeed
3. Autonomous experiments can run
4. Bio-compute jobs will process

The website at `http://localhost:3010/scientific` should now show real data instead of cached/fallback data.
