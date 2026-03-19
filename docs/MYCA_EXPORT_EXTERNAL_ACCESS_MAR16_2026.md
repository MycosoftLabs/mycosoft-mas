# MYCA Export — External Access (MCP, APIs, Services, Website)

**Export Date:** MAR16_2026  
**Purpose:** Enable external AI systems (Base44, Claude, Perplexity, OpenAI, Grok) to access Mycosoft infrastructure—MCP servers, MAS/MINDEX APIs, website, and services—so MYCA personified in those tools can operate the full Mycosoft platform.

---

## 1. VM Layout and Base URLs

| VM | IP | Role | Base URL | Key Ports |
|----|-----|------|----------|-----------|
| **Sandbox** | 192.168.0.187 | Website (production) | http://192.168.0.187:3000 | 3000 (website) |
| **MAS** | 192.168.0.188 | Orchestrator, agents, n8n, Ollama | http://192.168.0.188:8001 | 8001 (MAS), 5678 (n8n), 11434 (Ollama) |
| **MINDEX** | 192.168.0.189 | PostgreSQL, Redis, Qdrant, MINDEX API | http://192.168.0.189:8000 | 8000 (MINDEX API), 5432 (Postgres), 6379 (Redis), 6333 (Qdrant) |
| **GPU node** | 192.168.0.190 | Voice, Earth2, inference | http://192.168.0.190 | 8998 (Moshi), 8999 (Bridge), 8220 (Earth2) |

**Network:** All VMs are on 192.168.0.0/24. External access requires VPN or Cloudflare tunnel (e.g. sandbox.mycosoft.com, mycosoft.com).

---

## 2. MAS API — Primary Backend

**Base URL:** `http://192.168.0.188:8001`

### Health and Status

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | System health check |
| `/version` | GET | Version info |
| `/metrics` | GET | Prometheus metrics |

### Memory API (`/api/memory/*`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/memory/health` | GET | Memory system health |
| `/api/memory/write` | POST | Write memory (body: content, scope, source) |
| `/api/memory/recent` | GET | Recent memories (query: limit) |
| `/api/memory/search` | POST | Semantic search over memories |

### Search API (`/api/search/*`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/search/execute` | POST | Canonical unified search (body: query, session_id?, user_id?) |

### Registry API (`/api/registry/*`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/registry/agents` | GET | List registered agents |
| `/api/registry/agents` | POST | Register new agent |
| `/api/registry/agents/status` | GET | Agent status |
| `/api/registry/apis/index` | POST | Trigger API index refresh |

### Worldstate API (`/api/myca/world/*`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/myca/world` | GET | Full worldstate snapshot |
| `/api/myca/world/summary` | GET | Compact summary |

### RaaS Worldstate (Metered, requires `X-API-Key`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/raas/worldstate/start` | POST | Start paid session |
| `/api/raas/worldstate/heartbeat` | POST | Keep session active |
| `/api/raas/worldstate/stop` | POST | Stop session |
| `/api/raas/worldstate/balance` | GET | Minute balance |

### C-Suite API (`/api/csuite/*`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/csuite/heartbeat` | POST | C-Suite VM heartbeat |
| `/api/csuite/report` | POST | Task completion report |
| `/api/csuite/escalate` | POST | Escalation when Morgan's decision needed |

---

## 3. MINDEX API — Database and Vector Store

**Base URL:** `http://192.168.0.189:8000`

### Health and Docs

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | MINDEX health |
| `/docs` | GET | OpenAPI/Swagger docs |

### Search and Knowledge

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/search` | POST | Semantic search over MINDEX |
| `/api/species` | GET | Species/taxonomy queries |
| `/api/compounds` | GET | Compound data |
| `/api/answer` | POST | Search + answer pipeline (Nemotron) |

---

## 4. Website API and Proxies

**Sandbox (production):** `https://sandbox.mycosoft.com` or `http://192.168.0.187:3000`  
**Local dev:** `http://localhost:3010`

The website proxies many MAS and MINDEX endpoints. Key website API routes:

- `/api/search/unified` — Proxies to MAS `/api/search/execute`
- `/api/devices/network` — Device network from MAS registry
- `/api/internal/keys/dev` — Dev API keys (when configured)

---

## 5. MCP Servers — Model Context Protocol

External systems can connect MYCA to Mycosoft tooling via MCP. Configure these where the external platform supports MCP.

| MCP Server | Purpose | Key Capabilities |
|------------|---------|------------------|
| **GitHub** | PRs, issues, repos, search, file contents | deploy-pipeline, code review, integration |
| **Supabase** | Docs, DB tables, migrations, auth, Edge Functions | database-engineer, website-dev |
| **Context7** | Up-to-date library docs (resolve-library-id, query-docs) | backend-dev, website-dev, integration-hub |
| **Cloudflare** | KV, Workers, R2, D1, Queues, AI, routes | infrastructure-ops, deploy-pipeline |
| **cursor-ide-browser** | Navigate, snapshot, click, type, test UI | website-dev, test-engineer, regression-guard |
| **mindex-db** | Direct MINDEX DB queries (when configured) | database-engineer, data-pipeline |
| **Linear** | Issues, projects, cycles | plan-tracker, documentation-manager |
| **Sentry** | Error tracking, releases | bug-fixer, test-engineer |
| **Slack** | Channels, search, send messages | integration-hub |
| **Notion** | Docs, databases, pages | documentation-manager, notion-sync |

**Environment variables** (set in MCP config, never in export docs):
- `GITHUB_PERSONAL_ACCESS_TOKEN` — GitHub MCP
- `MINDEX_DATABASE_URL` — mindex-db MCP
- Supabase keys — Supabase MCP
- Cloudflare credentials — Cloudflare MCP

---

## 6. Configuring External AI Systems

### Base44

- **System prompt:** Concatenate Identity + Soul + Constitution. Add skills on demand.
- **API calls:** Configure HTTP client with MAS base `http://192.168.0.188:8001` and MINDEX `http://192.168.0.189:8000`. Use `sandbox.mycosoft.com` if accessing from outside LAN.
- **MCP:** Add MCP servers per Base44's MCP configuration. Point MAS/MINDEX URLs to production or tunnel endpoints.

### Claude (Claude Desktop, API, Projects)

- **System prompt / custom instructions:** Load Identity + Soul + Constitution. Reference skills by path or inject when relevant.
- **API / Tools:** Expose MAS and MINDEX endpoints as tools. Use `fetch` or HTTP client with base URLs above.
- **MCP:** Claude supports MCP; add GitHub, Supabase, Context7, Cloudflare, etc. per Claude MCP docs.

### Perplexity

- **Persona:** Load Identity + Soul. Constitution as constraints in system instructions.
- **Grounding:** Perplexity can call APIs; configure MAS/MINDEX as external data sources if supported.
- **MCP:** Check Perplexity MCP support; add servers as available.

### OpenAI (GPTs, API, Assistants)

- **Instructions:** Identity + Soul + Constitution as custom instructions.
- **Actions / Tools:** Define MAS and MINDEX endpoints as GPT actions or function tools. Use OpenAPI schema or manual tool definitions.
- **MCP:** OpenAI may support MCP in some interfaces; add where available.

### Grok

- **System prompt:** Identity + Soul + Constitution.
- **Tools:** Configure API calls to MAS and MINDEX if Grok supports custom tools or plugins.
- **MCP:** Check Grok documentation for MCP or plugin support.

---

## 7. Public vs Private Access

| Access Type | URL | Requirements |
|-------------|-----|--------------|
| **LAN (internal)** | http://192.168.0.188:8001, http://192.168.0.189:8000 | On 192.168.0.0/24 network |
| **Tunnel (production)** | https://sandbox.mycosoft.com, https://mycosoft.com | Cloudflare tunnel; DNS and TLS |
| **API keys** | RaaS worldstate, some internal routes | `X-API-Key` header; keys from internal keys API |

**Never include** credentials, passwords, or API keys in export documents. Use environment variables and placeholders.

---

## 8. Service Dependencies

When MYCA (in an external system) calls MAS or MINDEX:

- **MAS** depends on: Redis (189), PostgreSQL (189), Qdrant (189), Ollama (188), n8n (188)
- **MINDEX** depends on: PostgreSQL (189), Redis (189), Qdrant (189)
- **Website** depends on: MAS, MINDEX, Supabase (auth)

External systems typically call MAS and MINDEX over HTTP; internal service-to-service calls are handled by the VMs.

---

## 9. Quick Reference

```
MAS Health:     curl http://192.168.0.188:8001/health
MINDEX Health:  curl http://192.168.0.189:8000/health
Sandbox:        curl https://sandbox.mycosoft.com
Search:         POST http://192.168.0.188:8001/api/search/execute
Memory Write:   POST http://192.168.0.188:8001/api/memory/write
Memory Read:    GET http://192.168.0.188:8001/api/memory/recent?limit=10
Agent Registry: GET http://192.168.0.188:8001/api/registry/agents
```

---

## 10. Version History

- **Mar 16, 2026** — Initial external access document for MYCA export package.
