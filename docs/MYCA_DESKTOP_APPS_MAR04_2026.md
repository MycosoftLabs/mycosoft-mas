# MYCA Desktop Apps — VM 191 Software Inventory

**Date:** 2026-03-04
**VM:** 192.168.0.191 (myca-191)
**Current State:** Headless Ubuntu 22.04 server with Docker stack
**Goal:** Full autonomous workstation — API + GUI for all services MYCA operates

---

## Current VM 191 Services (Already Running)

| Service | Port | Container | Status |
|---------|------|-----------|--------|
| MYCA Workspace API | 8000 | myca-workspace | Running |
| PostgreSQL 15 | 5432 | myca-postgres | Running |
| Redis 7 | 6379 | myca-redis | Running |
| n8n Workflow Engine | 5678 | myca-n8n | Running |
| Caddy Reverse Proxy | 80/443 | myca-caddy | Running |
| Signal CLI REST API | 8089 | myca-signal-api | Running |

---

## Phase 1: Desktop Environment Foundation

VM 191 is currently headless. MYCA needs a desktop environment for GUI apps.

### Desktop Environment

| Component | Install Method | Notes |
|-----------|---------------|-------|
| **XFCE4** (lightweight DE) | `apt install xfce4 xfce4-goodies` | Low overhead, suitable for server |
| **xRDP** | `apt install xrdp` | Remote desktop access from Morgan's Windows |
| **TigerVNC** | `apt install tigervnc-standalone-server` | Alternative VNC access |
| **PulseAudio** | `apt install pulseaudio` | Audio for voice apps (ElevenLabs, PersonaPlex) |
| **X11 virtual framebuffer** | `apt install xvfb` | Headless browser automation without full DE |

### Browser Automation (Required for browser-use)

| Component | Install Method | Notes |
|-----------|---------------|-------|
| **Chromium** | `apt install chromium-browser` | Primary browser for automation |
| **Firefox** | `apt install firefox` | Backup browser |
| **Chrome for Testing** | Google's testing channel | For Selenium/Playwright |
| **Playwright** | `pip install playwright && playwright install` | Modern browser automation |
| **Selenium + ChromeDriver** | Already in codebase (`mycosoft_mas/integrations/`) | Existing integration |

---

## Phase 2: Development & AI Tools

### Code Editors & AI Assistants

| App | Type | Install Method | Purpose |
|-----|------|---------------|---------|
| **Cursor** | Desktop (Electron) | AppImage/deb from cursor.com | AI-powered IDE for MYCA's own coding |
| **Claude Desktop** | Desktop (Electron) | deb from anthropic.com | Chat/Cowork/Code with Claude |
| **Claude Code** | CLI | `npm install -g @anthropic-ai/claude-code` | Terminal AI coding assistant |
| **VS Code** | Desktop (Electron) | `snap install code` or deb | Fallback IDE |

### Container & Infrastructure

| App | Type | Install Method | Purpose |
|-----|------|---------------|---------|
| **Docker CLI** | CLI | Already installed (cloud-init) | Container management |
| **Docker Compose** | CLI | Already installed (plugin) | Multi-container orchestration |
| **lazydocker** | TUI | `go install github.com/jesseduffield/lazydocker@latest` | Visual Docker management |
| **Portainer** | Web UI | Docker container on port 9443 | Web-based container management |
| **k9s** | TUI | Binary download | Kubernetes management (future) |

---

## Phase 3: Communication Apps

### Messaging Platforms

| App | API Available | GUI Needed | Install Method | Notes |
|-----|:---:|:---:|------|-------|
| **Signal** | Yes (REST API on 8089) | Yes (Desktop) | Flatpak/deb | Already has CLI API; desktop for rich features |
| **WhatsApp** | Yes (Business API) | Yes (Web/Desktop) | Chromium + browser automation | WhatsApp Web via Playwright |
| **Discord** | Yes (Bot + Webhook) | Yes (Desktop) | deb/Flatpak | Bot API for most ops; desktop for voice channels |
| **Slack** | Yes (xoxb/xoxp tokens) | Yes (Desktop) | deb/snap | API for messaging; desktop for huddles/calls |
| **Telegram** | Yes (Bot API) | Optional | `pip install python-telegram-bot` | API sufficient for automation |

### Email & Calendar

| App | API Available | GUI Needed | Install Method | Notes |
|-----|:---:|:---:|------|-------|
| **Gmail** | Yes (Google Workspace API) | Optional | Browser/Thunderbird | Service account impersonation already configured |
| **Google Calendar** | Yes (API) | Optional | Browser | API handles all scheduling |
| **Thunderbird** | N/A | Optional | `apt install thunderbird` | Desktop email client if needed |

---

## Phase 4: Google Workspace (Service Account — No TOS Violation)

MYCA accesses Google Workspace via **service account with domain-wide delegation** — no OAuth consent screen needed, no user impersonation that violates TOS.

| Service | API Integration | GUI Alternative | Status |
|---------|----------------|-----------------|--------|
| **Gmail** | `google-api-python-client` | Browser | Config exists in codebase |
| **Google Drive** | `google-api-python-client` | Browser | Config exists |
| **Google Calendar** | `google-api-python-client` | Browser | Config exists |
| **Google Sheets** | `google-api-python-client` | Browser | Via API |
| **Google Docs** | `google-api-python-client` | Browser | Via API |
| **Google Meet** | Calendar API (create links) | Browser | Create meeting links via API |

**Credential location:** `/opt/myca/credentials/google/service-account.json`

---

## Phase 5: Project Management & Knowledge

| App | API Available | GUI Needed | Install Method | Notes |
|-----|:---:|:---:|------|-------|
| **Notion** | Yes (MCP + API) | Optional | Browser | Full API integration exists |
| **Asana** | Yes (REST API) | Optional | Browser | Token-based API access |
| **GitHub** | Yes (gh CLI + API) | Optional | `gh` CLI already available | API + CLI sufficient |
| **Jira** | Yes (REST API) | Optional | Browser | If needed in future |

---

## Phase 6: LLM Provider Access

All LLM providers work via API — no desktop apps needed, but web UIs useful for testing.

| Provider | API Client | GUI Access | Status |
|----------|-----------|------------|--------|
| **Anthropic Claude** | `anthropic` Python SDK | Claude Desktop app | API configured |
| **OpenAI GPT-4** | `openai` Python SDK | Browser (chat.openai.com) | API configured |
| **Google Gemini** | `google-generativeai` SDK | Browser (ai.google.dev) | API configured (primary LLM) |
| **xAI Grok** | REST API | Browser (x.ai) | Can add API key |
| **Ollama** | REST API (192.168.0.188:11434) | Open WebUI | Running on MAS VM |
| **Azure OpenAI** | `openai` Python SDK | Azure Portal (browser) | API configured |

---

## Phase 7: Financial & Market Data

All financial integrations are API-only — no desktop apps required.

| Service | Integration | File | Status |
|---------|------------|------|--------|
| **Mercury Banking** | REST API | `integrations/mercury_client.py` | Configured |
| **Stripe** | REST API | `agents/integrations/stripe_client.py` | Configured |
| **CoinMarketCap** | REST API | `integrations/financial_markets_client.py` | Configured |
| **CoinGecko** | REST API (no key) | `integrations/financial_markets_client.py` | Available |
| **Alpha Vantage** | REST API | `integrations/financial_markets_client.py` | Configured |
| **Polygon.io** | REST API | `integrations/financial_markets_client.py` | Configured |
| **Finnhub** | REST API | `integrations/financial_markets_client.py` | Configured |
| **Yahoo Finance** | `yfinance` Python lib | Various | Available |

---

## Phase 8: Scientific, Environmental & Research Data

All scientific integrations are API-only.

### Biological / Mycological
| Service | Integration | File | Status |
|---------|------------|------|--------|
| **NCBI/PubMed/GenBank** | E-utilities REST API | `integrations/ncbi_client.py` | Configured |
| **ChemSpider** | RSC REST API | `integrations/chemspider_client.py` | Configured |
| **iNaturalist** | REST API | `integrations/inaturalist_client.py` | Configured |
| **Google Scholar** | SerpAPI | `integrations/scholar_client.py` | Configured |
| **PubPeer** | REST API | `integrations/pubpeer_client.py` | Configured |

### Space & Weather
| Service | Integration | File | Status |
|---------|------------|------|--------|
| **NASA DONKI** | REST API | `integrations/space_weather_client.py` | Configured |
| **NASA NEO** | REST API | `integrations/space_weather_client.py` | Configured |
| **NOAA Weather** | REST API | `integrations/space_weather_client.py` | Configured |
| **NOAA Tides & Currents** | REST API | `integrations/earth_science_client.py` | Configured |
| **NOAA Tsunami Alerts** | XML Feed | `integrations/earth_science_client.py` | Configured |
| **USGS Earthquakes** | REST API | `integrations/earth_science_client.py` | Configured |
| **USGS Water Services** | NWIS API | `integrations/earth_science_client.py` | Configured |
| **IRIS Seismic** | FDSN API | `integrations/earth_science_client.py` | Configured |
| **NDBC Buoys** | Real-time data | `integrations/earth_science_client.py` | Configured |
| **USACE CWMS** | Data API | `integrations/earth_science_client.py` | Configured |

### Environmental Monitoring
| Service | Integration | File | Status |
|---------|------------|------|--------|
| **OpenAQ** | REST API v2 | `integrations/environmental_client.py` | Configured |
| **EPA AirNow** | REST API | `integrations/environmental_client.py` | Configured |
| **PurpleAir** | REST API v1 | `integrations/environmental_client.py` | Configured |
| **IQAir** | AirVisual API | `integrations/environmental_client.py` | Configured |
| **Safecast** | REST API (radiation) | `integrations/environmental_client.py` | Configured |
| **BreezoMeter** | Air Quality API | `integrations/environmental_client.py` | Configured |
| **Ambee** | Air Quality & Fire APIs | `integrations/environmental_client.py` | Configured |

---

## Phase 9: Infrastructure & Cloud

| App | Type | Install Method | Purpose |
|-----|------|---------------|---------|
| **Proxmox Web UI** | Browser | N/A (access via browser) | VM management |
| **AWS CLI** | CLI | `pip install awscli` | AWS service management |
| **Azure CLI** | CLI | `apt install azure-cli` | Azure resource management |
| **gcloud CLI** | CLI | Google Cloud SDK | GCP management |
| **Terraform** | CLI | Binary download | Infrastructure-as-code |
| **Cloudflare CLI (flarectl)** | CLI | Binary download | DNS/CDN management |

---

## Phase 10: Automation Platform Connectors

### External Automation Hubs (via `integrations/automation_hub_client.py`)

| Platform | Integration | Method | Desktop Needed |
|----------|------------|--------|:--------------:|
| **Zapier** | Webhook triggers | REST webhook | No |
| **IFTTT** | Maker webhooks | REST webhook | No |
| **Make (Integromat)** | Webhook triggers | REST webhook | No |
| **Pipedream** | Workflow API | REST API | No |
| **Activepieces** | Webhook triggers | REST webhook | No |

### n8n (Primary — Already Running on VM 191)

n8n replaces Zapier/IFTTT with self-hosted automation. These are the connector categories MYCA uses:

| Category | n8n Nodes Available | Count |
|----------|-------------------|-------|
| Communication | Slack, Discord, Telegram, Email (IMAP/SMTP), WhatsApp Business | 5 |
| Productivity | Notion, Asana, Google Sheets, Google Drive, Google Calendar | 5 |
| Development | GitHub, GitLab, Docker, SSH, HTTP Request | 5 |
| AI/LLM | OpenAI, Anthropic Claude, Google Gemini, Ollama | 4 |
| Data | PostgreSQL, Redis, MongoDB, Qdrant, Supabase | 5 |
| Cloud | AWS (S3, Lambda, EC2), Azure, Google Cloud | 3 |
| Finance | CoinMarketCap (via HTTP), Polygon (via HTTP) | 2 |
| Monitoring | Prometheus, Grafana, Webhook | 3 |
| Files | Google Drive, Dropbox, S3, Local filesystem | 4 |
| Web | HTTP Request, Webhook, RSS, Web Scraping | 4 |
| **Total** | | **~40** |

### Additional Automation Tools (API/CLI)

| Tool | Type | Purpose | Install |
|------|------|---------|---------|
| **Playwright MCP** | Node.js | Browser automation via MCP | `npm install @anthropic/mcp-playwright` |
| **browser-use** | Python | AI-driven browser automation | `pip install browser-use` |
| **Puppeteer** | Node.js | Headless browser scripting | `npm install puppeteer` |
| **PyAutoGUI** | Python | Desktop GUI automation | `pip install pyautogui` (needs X11) |
| **xdotool** | CLI | X11 window/keyboard automation | `apt install xdotool` |

---

## Phase 11: Voice & Audio

| App | Type | Install Method | Purpose |
|-----|------|---------------|---------|
| **ElevenLabs** | API | `pip install elevenlabs` | TTS voice synthesis (Arabella voice) |
| **PersonaPlex** | Internal | MAS service | Full-duplex voice (Moshi/nat2f) |
| **Twilio** | API | `pip install twilio` | SMS and phone calls |
| **ffmpeg** | CLI | `apt install ffmpeg` | Audio/video processing |
| **PulseAudio** | System | `apt install pulseaudio` | Audio routing for voice apps |
| **ALSA** | System | `apt install alsa-utils` | Low-level audio |

---

## Phase 12: Security & Monitoring

| App | Type | Install Method | Purpose |
|-----|------|---------------|---------|
| **Grafana** | Web UI | Docker container | Metrics dashboards |
| **Prometheus** | Service | Docker container | Metrics collection |
| **Fail2Ban** | System | `apt install fail2ban` | Brute-force protection |
| **ClamAV** | System | `apt install clamav` | Malware scanning |
| **htop** | TUI | Already installed (cloud-init) | Process monitoring |
| **Netdata** | Web UI | Docker or install script | Real-time system monitoring |

---

## Installation Priority Matrix

### Tier 1 — Critical (Install First)
1. Desktop Environment (XFCE4 + xRDP) — enables all GUI apps
2. Chromium + Playwright — browser automation foundation
3. Cursor — MYCA's primary IDE
4. Claude Desktop — AI assistant interface
5. Claude Code CLI — terminal AI assistant

### Tier 2 — High Priority
6. Signal Desktop — encrypted messaging GUI
7. Discord Desktop — voice channels + rich messaging
8. Slack Desktop — team communication
9. Portainer — Docker web UI
10. browser-use / Playwright MCP — AI browser automation

### Tier 3 — Medium Priority
11. WhatsApp Web (via browser automation)
12. AWS CLI + Azure CLI + gcloud
13. Grafana + Prometheus (monitoring stack)
14. Thunderbird (email client)
15. VS Code (backup IDE)

### Tier 4 — Nice to Have
16. lazydocker (Docker TUI)
17. Netdata (system monitoring)
18. Terraform (IaC)
19. k9s (Kubernetes TUI)

---

## Docker Compose Extension for Desktop Services

Add these services to `docker-compose.myca-workspace.yml`:

```yaml
  # Portainer — Docker Management Web UI
  portainer:
    image: portainer/portainer-ce:latest
    container_name: myca-portainer
    ports:
      - "9443:9443"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - portainer_data:/data
    restart: unless-stopped
    networks:
      - myca-net

  # Grafana — Monitoring Dashboard
  grafana:
    image: grafana/grafana:latest
    container_name: myca-grafana
    ports:
      - "3001:3000"
    environment:
      GF_SECURITY_ADMIN_PASSWORD: ${GRAFANA_PASSWORD:-changeme}
    volumes:
      - grafana_data:/var/lib/grafana
    restart: unless-stopped
    networks:
      - myca-net
```

---

## What Does NOT Need a Desktop App

These services work entirely via API/CLI and do not need GUI apps:

| Service | Why No GUI Needed |
|---------|-------------------|
| PostgreSQL, Redis, Qdrant | Accessed via client libraries |
| All LLM Providers | REST API / Python SDK |
| Scientific APIs (NCBI, NASA, NOAA) | REST API |
| Financial APIs | REST API |
| n8n | Already has web UI on port 5678 |
| Cloudflare | REST API / flarectl CLI |
| Supabase | REST API |
| Docker | CLI + Portainer web UI |
| Git/GitHub | CLI + `gh` command |

---

## Total App Count Summary

| Category | API/CLI Only | Needs GUI | Both Available |
|----------|:-----------:|:---------:|:--------------:|
| Communication | 2 | 4 | 4 |
| Development | 2 | 2 | 1 |
| AI/LLM | 6 | 2 | 2 |
| Productivity | 3 | 0 | 3 |
| Financial | 8 | 0 | 0 |
| Scientific/Environmental | 22 | 0 | 0 |
| Infrastructure | 5 | 0 | 2 |
| Voice/Audio | 3 | 0 | 0 |
| Browser/Automation | 0 | 1 | 4 |
| Automation Hubs | 5 | 0 | 0 |
| Monitoring | 0 | 0 | 3 |
| **Total** | **56** | **9** | **19** |

**Grand total: 84 apps/services across MYCA's workspace**
**External integrations discovered in codebase: 66+**

---

## Implementation Notes

1. **Desktop environment must be installed on the bare metal VM** — not inside Docker
2. **xRDP enables remote access** from Morgan's Windows machine
3. **Xvfb provides headless X11** for browser automation without a monitor
4. **PulseAudio is required** for voice features (ElevenLabs, PersonaPlex)
5. **Service account auth** for Google Workspace avoids OAuth TOS issues
6. **n8n replaces Zapier/IFTTT** — all automation runs self-hosted
7. **browser-use + Playwright** gives MYCA human-like web interaction capability
