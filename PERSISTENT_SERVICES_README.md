# MYCOSOFT Persistent Services

All services are now configured to run independently of Cursor and will automatically restart if they crash.

## ✅ Current Status

All services are **RUNNING** and being monitored by the watchdog:

- ✅ **Website** (http://localhost:3000) - Next.js dev server
- ✅ **MycoBrain Service** (http://localhost:8003) - Device management API
- ✅ **MINDEX API** (http://localhost:8000) - Fungal knowledge database
- ✅ **MAS Orchestrator** (http://localhost:8001) - Multi-agent system
- ✅ **n8n Workflows** (http://localhost:5678) - Workflow automation
- ✅ **Docker Containers** - All running with `unless-stopped` restart policy

## 🚀 Quick Start

### Start All Services
```powershell
cd C:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas
.\START_MYCOSOFT_PERSISTENT.bat
```

Or use PowerShell:
```powershell
.\scripts\start-all-persistent.ps1
```

### Stop All Services
```powershell
.\scripts\stop-all-services.ps1
```

## 🔄 Service Watchdog

A watchdog script monitors all services every 30 seconds and automatically restarts them if they go down.

**Watchdog Features:**
- Monitors Website (port 3000)
- Monitors MycoBrain Service (port 8003)
- Monitors Docker containers (MINDEX, MAS, n8n)
- Automatically restarts failed services
- Logs all activity to `logs\watchdog.log`

The watchdog runs in the background and will keep services running even if:
- Cursor crashes
- You close the terminal
- A service crashes
- System restarts (if auto-start is configured)

## 📋 Log Files

All service logs are in `C:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas\logs\`:

- `website.log` - Next.js website output
- `mycobrain-service.log` - MycoBrain service output
- `watchdog.log` - Watchdog monitoring activity

## 🔧 Auto-Start on Boot (Optional)

To automatically start all services when Windows boots:

1. **Run as Administrator:**
   ```powershell
   cd C:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas
   .\scripts\setup-autostart.ps1
   ```

2. This creates a Windows Scheduled Task that runs on startup.

3. **To remove auto-start:**
   ```powershell
   Unregister-ScheduledTask -TaskName "MYCOSOFT-Services-AutoStart" -Confirm:$false
   ```

## 🐛 Troubleshooting

### Services Not Starting

1. **Check logs:**
   ```powershell
   Get-Content logs\watchdog.log -Tail 50
   Get-Content logs\website.log -Tail 50
   Get-Content logs\mycobrain-service.log -Tail 50
   ```

2. **Check if ports are in use:**
   ```powershell
   netstat -ano | findstr "3000 8003 8000 8001 5678"
   ```

3. **Manually restart a service:**
   - Website: Kill process on port 3000, watchdog will restart it
   - MycoBrain: Kill Python process with mycobrain_service, watchdog will restart it
   - Docker: `docker-compose up -d`

### Watchdog Not Running

Check if watchdog process is running:
```powershell
Get-Process powershell | Where-Object {
    $_.CommandLine -like "*service-watchdog*"
}
```

If not running, start it:
```powershell
.\scripts\service-watchdog.ps1 -StartNow
```

### Docker Issues

If Docker containers aren't starting:
```powershell
# Check Docker Desktop is running
docker info

# Restart containers
docker-compose up -d
docker-compose -f docker-compose.mindex.yml up -d
docker-compose -f docker-compose.integrations.yml up -d
```

## 📊 Service Endpoints

| Service | URL | Status Check |
|---------|-----|--------------|
| Website | http://localhost:3000 | Browser |
| MycoBrain | http://localhost:8003/health | `/health` |
| MINDEX | http://localhost:8000/health | `/health` |
| MAS API | http://localhost:8001/health | `/health` |
| n8n | http://localhost:5678 | Browser |

## 🔒 Persistence Features

1. **Docker Containers**: All have `restart: unless-stopped` policy
2. **Watchdog**: Monitors and restarts services every 30 seconds
3. **Auto-Start**: Optional Windows Task Scheduler integration
4. **Logging**: All services log to persistent files

## ⚠️ Important Notes

- **Cursor Independence**: All services run independently of Cursor
- **Background Processes**: Services run in hidden PowerShell windows
- **Resource Usage**: Monitor CPU/memory if issues occur
- **Port Conflicts**: Ensure no other applications use ports 3000, 8000, 8001, 8003, 5678

## 🎯 Next Steps

1. ✅ Services are running
2. ✅ Watchdog is monitoring
3. ⚠️ (Optional) Set up auto-start on boot: `.\scripts\setup-autostart.ps1`

All services will now stay running even if Cursor crashes or you close the IDE!





























