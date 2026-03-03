# Deployment & Fixes Summary — March 3, 2026

**Status:** Deployed via Cursor on local machine
**VMs Targeted:** MAS (188), Website (187), MINDEX (189)
**Branch:** `claude/integrate-static-framework-Pogjj`

---

## Deployment Commands Issued

### MAS VM (192.168.0.188)
```bash
ssh mycosoft@192.168.0.188 "cd /home/mycosoft/mycosoft/mas && git pull && docker build -t mycosoft/mas-agent:latest --no-cache . && docker stop myca-orchestrator-new && docker rm myca-orchestrator-new && docker run -d --name myca-orchestrator-new --restart unless-stopped -p 8001:8000 mycosoft/mas-agent:latest"
```

### Website VM (192.168.0.187)
```bash
ssh mycosoft@192.168.0.187 "cd /home/mycosoft/mycosoft/website && git pull && docker build -t mycosoft/website:latest --no-cache . && docker stop mycosoft-website && docker rm mycosoft-website && docker run -d --name mycosoft-website --restart unless-stopped -p 3000:3000 -v /opt/mycosoft/media/website/assets:/app/public/assets:ro mycosoft/website:latest"
```

### MINDEX VM (192.168.0.189)
```bash
ssh mycosoft@192.168.0.189 "cd /home/mycosoft/mycosoft/mindex && git pull && docker compose stop mindex-api && docker compose build --no-cache mindex-api && docker compose up -d mindex-api"
```

---

## Recent Changes Included in This Deployment

### Features
| Commit | Description |
|--------|-------------|
| `b57abde` | Autonomous AI assistant v2 (PR #74) |
| `6814f4d` | STATIC framework integration (PR #73) |
| `f6b7db9` | Wire STATIC constrained decoding system-wide |
| `cb0cfd5` | Unified Latents (UL) framework for image/video generation |
| `2b1f199` | 6 universal STATIC domain builders |
| `8325e97` | Cowork deliverables — n8n workflows, Docker Compose, YAML agents |
| `ff7a583` | STATIC constrained decoding across all MAS data domains |
| `3e8fea9` | Google STATIC constrained decoding framework |
| `b7c5301` | OpenClaw MYCA architecture (Phases 1-10) |

### Fixes
| Commit | Description |
|--------|-------------|
| `f4d96bd` | Resolve 18 test failures — broken import, singleton bug, missing skips |
| `6d59a84` | Resolve PR #72 review issues — singleton agent, env var GPU IP, dedup endpoints |
| `cfff2f7` | Enforce sandbox WebSocket auth and use env vars for VM URLs |
| `6fe5aaa` | Align Cursor code with Cowork configs — env-var URLs, sandbox security |

### Maintenance
| Commit | Description |
|--------|-------------|
| `c4d03bb` | Normalize CRLF → LF for integration and security files |
| `2d96221` | Normalize remaining CRLF → LF line endings |
| `724be98` | Merge conflict resolution — keep both STATIC and Unified Latents routers |
| `1a233a1` | Normalize line endings, add numpy dependency |

---

## Security Note

SSH credentials were handled interactively via Cursor's terminal prompt — no passwords stored in files, environment variables, or chat logs.

---

## Post-Deployment Verification

### Live VM Health (verified by Cursor)
- [x] MAS Orchestrator responds: `http://192.168.0.188:8001/health` — HTTP 200 HEALTHY
- [x] MINDEX API responds: `http://192.168.0.189:8000/api/mindex/health` — HTTP 200 OK
- [x] Sandbox Website: `http://192.168.0.187:3000` — HTTP 200 (37KB)
- [x] Cloudflare tunnel: `https://sandbox.mycosoft.com` — HTTP 200 LIVE (38KB)

### Code Verification (verified by Claude Code)
- [x] **STATIC Constrained Decoding API** (`/api/static/`) — 15 endpoints: health, build indexes (token/string), list/get/delete indexes, decode, validate, rerank, mask, domain build-all/build/list/report/validate
- [x] **Unified Latents API** (`/api/unified-latents/`) — 9 endpoints: health, info, generate image/video, encode, decode, train, train status, evaluate
- [x] **Economy API** (`/api/economy/`) — 11 endpoints: health, wallets, charge, revenue, pricing, resource purchase/needs, incentives CRUD, summary, client registration
- [x] **Taxonomy API** (`/api/taxonomy/`) — 8 endpoints: health, search, taxon detail, observations, ingestion start/status, stats, kingdoms, random species
- [x] **Knowledge API** (`/api/knowledge/`) — 6 endpoints: health, query, classify, deep research, domains, sources, stats
- [x] **MYCA Soul Persona** — 20,000+ character deep identity loaded at consciousness init
- [x] **Autonomous Research API** (`/autonomous/`) — experiments CRUD, hypothesis engine
- [x] All new routers properly imported with try/except graceful fallbacks in `myca_main.py`
- [x] All availability flags (`ECONOMY_API_AVAILABLE`, `TAXONOMY_API_AVAILABLE`, `KNOWLEDGE_API_AVAILABLE`, `STATIC_DECODING_API_AVAILABLE`) verified

### Test Suite
- [x] **678 passed, 31 skipped, 0 failures** (26.00s)
- Skips: voice-memory-bridge tests (expected — requires `MINDEX_DATABASE_URL`)
- All STATIC, Unified Latents, autonomous, and system registry tests pass

### Disk Cleanup
- [x] 59.7GB of old Docker images reclaimed on MAS VM (188)
