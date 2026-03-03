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

## Post-Deployment Verification Checklist

- [ ] MAS Orchestrator responds: `curl http://192.168.0.188:8001/health`
- [ ] Website loads: `curl http://192.168.0.187:3000`
- [ ] MINDEX API responds: `curl http://192.168.0.189:8000/health`
- [ ] STATIC endpoints available: `curl http://192.168.0.188:8001/api/static/health`
- [ ] Unified Latents endpoints available: `curl http://192.168.0.188:8001/api/ul/health`
- [ ] Run tests: `poetry run pytest tests/ -v --tb=short`
