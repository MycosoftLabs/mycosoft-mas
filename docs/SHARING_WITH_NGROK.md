# 🌐 Sharing MAS with Claude Desktop & Collaborators

This guide explains how to expose your local MAS (Mycosoft Agent System) to the internet using ngrok, allowing Claude Desktop, Garret, or anyone else to interact with your system remotely.

## Quick Start

### Option 1: One-Click Start (Recommended)
```powershell
# From the MAS directory, run:
.\scripts\ngrok-start.bat
```

### Option 2: PowerShell Script
```powershell
# Expose all running services
.\scripts\start_ngrok_tunnels.ps1 -All

# Or expose specific services
.\scripts\start_ngrok_tunnels.ps1 -Website -MycoBrain
```

## First Time Setup

1. **Sign up for ngrok** (free): https://ngrok.com
2. **Get your auth token**: https://dashboard.ngrok.com/get-started/your-authtoken
3. **Run the script** - it will prompt for your token on first run

Or manually configure:
```powershell
ngrok config add-authtoken YOUR_TOKEN_HERE
```

## Available Services

| Service | Port | Description |
|---------|------|-------------|
| Website | 3002 | Main MAS web interface |
| Dashboard | 3100 | MYCA UniFi-style agent dashboard |
| MAS Orchestrator | 8001 | Core orchestration API |
| MycoBrain | 8003 | ESP32 device management |
| n8n | 5678 | Automation workflows |
| MINDEX | 8000 | Species/taxonomy search |

## Script Options

```powershell
# Start tunnels for all running services
.\scripts\start_ngrok_tunnels.ps1 -All

# Start specific service tunnels
.\scripts\start_ngrok_tunnels.ps1 -Website
.\scripts\start_ngrok_tunnels.ps1 -MycoBrain
.\scripts\start_ngrok_tunnels.ps1 -Website -MAS -MycoBrain

# Check status of services and tunnels
.\scripts\start_ngrok_tunnels.ps1 -Status

# Stop all tunnels
.\scripts\start_ngrok_tunnels.ps1 -Stop

# Provide auth token directly
.\scripts\start_ngrok_tunnels.ps1 -All -AuthToken "your_token_here"
```

## Sharing with Claude Desktop

Once tunnels are running, you'll see output like:

```
═══════════════════════════════════════════════════════════════
                    🎉 TUNNELS ARE LIVE! 🎉                     
═══════════════════════════════════════════════════════════════

  🍄 MAS Website
     Local:  http://localhost:3002
     Public: https://abc123.ngrok-free.app

  🍄 MycoBrain Service
     Local:  http://localhost:8003
     Public: https://def456.ngrok-free.app
```

**Share the `Public` URLs with Claude Desktop or collaborators!**

### For Claude Desktop Users

Add these URLs to your Claude Desktop MCP configuration:

```json
{
  "mcpServers": {
    "mycosoft-mas": {
      "url": "https://abc123.ngrok-free.app"
    }
  }
}
```

## Monitoring

- **ngrok Dashboard**: http://localhost:4040 (local web interface)
- **Request Inspector**: See all incoming requests in real-time
- **Replay Requests**: Debug by replaying failed requests

## Important Notes

### Free Tier Limitations
- URLs change each time you restart ngrok
- Limited to 1 ngrok agent process
- Rate limited to 40 connections/minute

### For Permanent URLs
Upgrade to ngrok Pro for:
- Static/reserved domains
- Multiple simultaneous tunnels
- Higher rate limits
- Custom domains

### Security Considerations
- Anyone with the URL can access your services
- URLs are randomly generated but not secret
- Consider adding authentication to your services
- Tunnels are encrypted (HTTPS)

## Troubleshooting

### "ngrok not found"
```powershell
# Reinstall ngrok
winget install ngrok.ngrok

# Refresh your terminal or run:
$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
```

### "Auth token required"
```powershell
# Get your token from https://dashboard.ngrok.com/get-started/your-authtoken
ngrok config add-authtoken YOUR_TOKEN
```

### "Port not available"
Make sure your MAS services are running:
```powershell
# Check service status
.\scripts\start_ngrok_tunnels.ps1 -Status
```

### "Too many tunnels"
Free ngrok only allows one tunnel at a time. Either:
- Upgrade to ngrok Pro
- Use the multi-tunnel config (script handles this)
- Start tunnels one at a time

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        INTERNET                              │
│                                                              │
│   Claude Desktop ──────┐                                    │
│   Garret's Browser ────┼──► ngrok Cloud                     │
│   Other Collaborators ─┘        │                           │
└─────────────────────────────────┼───────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────┐
│                    YOUR WINDOWS MACHINE                      │
│                                                              │
│   ┌──────────────┐     ┌─────────────────────────────────┐  │
│   │  ngrok agent │────►│  MAS Services                   │  │
│   │  (tunnels)   │     │  ├── Website (:3002)            │  │
│   └──────────────┘     │  ├── Dashboard (:3100)          │  │
│                        │  ├── MAS Orchestrator (:8001)   │  │
│                        │  ├── MycoBrain (:8003)          │  │
│                        │  ├── n8n (:5678)                │  │
│                        │  └── MINDEX (:8000)             │  │
│                        └─────────────────────────────────┘  │
│                                                              │
│   ┌──────────────────────────────────────────────────────┐  │
│   │  Physical Devices                                     │  │
│   │  └── MycoBrain ESP32-S3 (COM5) with BME688 sensors   │  │
│   └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## Support

- ngrok Documentation: https://ngrok.com/docs
- MAS Issues: Check the project's GitHub issues
- Discord: Join the Mycosoft community

---

*Happy sharing! 🍄*

