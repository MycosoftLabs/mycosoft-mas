# Request Flow Architecture - March 5, 2026

## Overview

This document describes request flows across the Mycosoft platform: Browser → Cloudflare → VMs → Services.

---

## 1. Website (Public Traffic)

```
User Browser
    → Cloudflare (DNS + CDN + Tunnel)
    → Sandbox VM (192.168.0.187:3000)
    → Docker: mycosoft-website (Next.js)
```

- **URL:** https://sandbox.mycosoft.com (or mycosoft.com)
- **Cloudflare:** Handles SSL, caching, DDoS. Tunnel routes to 187:3000.
- **VM 187:** Website container; NAS mount for /public/assets (videos, images).

---

## 2. Website → MAS (Internal API)

```
Website (187)
    → HTTP GET/POST
    → MAS VM (192.168.0.188:8001)
    → MAS Orchestrator (FastAPI)
```

- **Endpoints:** /health, /api/agents/*, /api/memory/*, /api/tasks/*, etc.
- **Config:** `MAS_API_URL=http://192.168.0.188:8001` in website `.env.local`.

---

## 3. Website → MINDEX (Internal API)

```
Website (187)
    → HTTP GET
    → MINDEX VM (192.168.0.189:8000)
    → MINDEX API (FastAPI)
```

- **Endpoints:** /health, /api/species/*, /api/compounds/*, etc.
- **Config:** `MINDEX_API_URL=http://192.168.0.189:8000`.

---

## 4. MAS → MINDEX (Backend)

```
MAS (188)
    → HTTP
    → MINDEX (189:8000)
    → Postgres (189:5432), Redis (189:6379), Qdrant (189:6333)
```

- **Purpose:** Memory, species data, vector search.

---

## 5. MycoBrain → MAS (Device Heartbeat)

```
MycoBrain Service (187:8003 or local 8003)
    → POST /api/devices/heartbeat
    → MAS (188:8001)
```

- **Frequency:** Every 30 seconds.
- **Purpose:** Device registration, network visibility.

---

## 6. n8n Workflows

- **MAS n8n:** 192.168.0.188:5678 (orchestrator workflows)
- **MYCA n8n:** 192.168.0.191:5679 (MYCA workspace)
- Workflows can trigger MAS API, MINDEX, Website webhooks.

---

## VM Layout Summary

| VM   | IP            | Role              | Key Ports              |
|------|---------------|-------------------|------------------------|
| 187  | 192.168.0.187 | Sandbox, Website  | 3000, 8003             |
| 188  | 192.168.0.188 | MAS, n8n, Ollama  | 8001, 5678, 11434      |
| 189  | 192.168.0.189 | MINDEX            | 8000, 5432, 6379, 6333 |
| 190  | 192.168.0.190 | GPU node          | TBD                    |
| 191  | 192.168.0.191 | MYCA workspace    | 5679, 443, 8089        |
