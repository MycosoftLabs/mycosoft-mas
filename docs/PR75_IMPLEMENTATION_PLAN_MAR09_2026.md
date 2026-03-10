# PR #75 Implementation Plan — Plans, Docs, Frontend

**Date:** March 9, 2026  
**Author:** MYCA Coding Agent  
**Status:** In Progress  
**PR:** [Add Jetson + MycoBrain hardware plan for Mushroom 1 and Hyphae 1 #75](https://github.com/MycosoftLabs/mycosoft-mas/pull/75)  
**Merge Commit:** `a2d7aaa35`

---

## Summary

PR #75 bundled 10 commits across five major feature areas:

1. **Jetson + MycoBrain hardware plan** — Mushroom 1 (AGX Orin 32GB, ~$1,200) and Hyphae 1 (Orin Nano Super 8GB, ~$275), shared ESP32-S3 MycoBrain boards, dual BME688, FCI, LoRa mesh
2. **Liquid AI fungal integration** — LiquidTemporalProcessor, FungalMemoryBridge, RecursiveSelfImprovementEngine, LiquidFungalIntegrationAgent, 13 endpoints under `/api/liquid-fungal/`
3. **Micah Guardian Architecture** — Independent Constitutional Guardian, Moral Precedence Engine, Anti-Ultron Tripwires, Authority Engine, Awakening Protocol, REST API under `/api/guardian/*`
4. **Avani–Micah Constitutional Governance** — Constitution, Vision layer, Season Engine, Governor pipeline, 10 endpoints under `/api/avani/`
5. **Reciprocal Turing identity integration** — Identity API, Mode Manager, Continuity Manager, identity instincts, `/api/identity/*`

---

## Deployment Status

| Target            | Status      | Notes |
|-------------------|------------|-------|
| **MAS (VM 188)**  | Deployed   | Pulled merge commit, `systemctl restart mas-orchestrator` |
| **Local main**    | Updated    | Stashed local changes, fast-forward to `a2d7aaa35` |
| **MINDEX**        | Pending    | Run migration `025_identity_system.sql` on MINDEX PostgreSQL |
| **Website**       | Not changed| No PR75 changes; frontend work below is new |
| **NatureOS**      | Not changed| No PR75 changes |
| **Mycorrhizae**   | Not changed| No PR75 changes |

### MINDEX: Identity Migration

Run migration `025_identity_system.sql` against MINDEX Postgres (if MAS identity tables live there):

```bash
# On MINDEX VM or wherever MAS/MINDEX Postgres runs
psql -U mindex -d mindex -f migrations/025_identity_system.sql
```

Creates schema `identity` and tables: `earliest_fragments`, `preferences`, `moral_assessments`, `continuity_events`, `creator_bonds`.

---

## Security Findings (cursor[bot] Review)

PR #75 introduced **high-confidence vulnerabilities**. Remediation required before production exposure.

### 1. Critical: Unauthenticated Guardian API

**Issue:** `/api/guardian/emergency-halt`, `/operational-mode`, `/sentry/activate`, `/sentry/deactivate` exposed without auth.

**Impact:** Any caller can trigger emergency halt (DoS) or alter operational mode and sentry state.

**Remediation:**
- Require strong auth (API key/JWT + role `guardian:admin`) on all guardian endpoints
- Split read-only from mutating endpoints; keep mutating admin-only
- Add audit fields from authenticated principal (not user-supplied)

### 2. High: Client-Controlled Root Authority

**Issue:** `avani_router.py` accepts `is_root` from request body; `is_root=True` unlocks Root-only seasonal transitions.

**Impact:** Any caller can self-assert Root privileges and perform Root-gated transitions.

**Remediation:**
- Remove `is_root` from client input
- Derive root/admin status from authenticated identity server-side
- Reject Root-only transitions unless principal has explicit Root authority

### 3. High: Unauthenticated Identity Write Endpoints

**Issue:** `POST /api/identity/earliest-fragment`, `/preferences`, `/moral-assessments`, `/continuity-events`, `/creator-bond` have no auth.

**Impact:** External callers can overwrite or poison identity/continuity data.

**Remediation:**
- Protect all identity write endpoints with auth + scoped authorization
- Restrict `authorized_by` to server-generated from authenticated principal
- Add input validation, rate limiting, and immutable append-only policy for audit events

---

## Plans to Build

### 1. Jetson + MycoBrain Hardware Build Plan

**Doc:** `docs/JETSON_MYCOBRAIN_HARDWARE_PLAN_MAR09_2026.md`

| Phase | Scope |
|-------|--------|
| Phase 1 | Jetson setup (JetPack 6.x, Docker, Tailscale, TensorRT) |
| Phase 2 | MycoBrain integration (firmware, dual BME688, FCI, MDP serial) |
| Phase 3 | MAS agent deployment to Jetsons, device registration |
| Phase 4 | AI model deployment (TensorRT models, bioelectric classification) |

**Next steps:**
- Order Jetson AGX Orin 32GB and Orin Nano Super 8GB
- Create Cursor plan: `cto_vm_blueprint` or `jetson_mycobrain_build`
- Track in MASTER_DOCUMENT_INDEX

### 2. Guardian Security Hardening Plan

- Add auth dependency to `guardian_api.py`
- Implement `guardian:admin` role check
- Split read vs. mutating endpoints

### 3. Avani Security Hardening Plan

- Remove `is_root` from request model
- Add server-side Root authority derivation
- Add auth to season update endpoint

### 4. Identity API Security Plan

- Add auth to all identity write endpoints
- Enforce `authorized_by` from principal
- Add rate limiting and validation

---

## Docs Added by PR #75

| Doc | Purpose |
|-----|---------|
| `docs/AVANI_MICAH_CONSTITUTION_MAR09_2026.md` | Avani–Micah hierarchy, modules, API |
| `docs/JETSON_MYCOBRAIN_HARDWARE_PLAN_MAR09_2026.md` | Mushroom 1 & Hyphae 1 specs, BOM, topology |
| `docs/MICAH_GUARDIAN_ARCHITECTURE_MAR09_2026.md` | Guardian modules, API, design principles |
| `docs/RECIPROCAL_TURING_PROTOCOL_MAR09_2026.md` | Identity, modes, continuity |
| `config/avani_constitution.yaml` | Avani declarative config |
| `config/constitutional_boot_statement.yaml` | Anti-Ultron boot statement |
| `config/guardian_config.yaml` | Guardian independent config |

### Docs to Create Next

- `docs/PR75_SECURITY_REMEDIATION_MAR09_2026.md` — Track auth fixes for Guardian, Avani, Identity
- `docs/JETSON_BUILD_PHASE1_MAR09_2026.md` — Step-by-step Jetson setup (when hardware arrives)
- `docs/FRONTEND_GUARDIAN_AVANI_IDENTITY_MAR09_2026.md` — Frontend spec for new dashboard sections

---

## Frontend Implementations

PR #75 added backend APIs only. Website frontend work:

### 1. Guardian Dashboard Section

**APIs:** `GET /api/guardian/status`, `/boot-statement`, `/developmental-stage`, `/moral-precedence`, `/sentry`, `/operational-mode`, `/tripwires`, `/audit-log`

**UI:**
- Guardian status card (health, developmental stage, operational mode)
- Sentry mode toggle (admin only, after auth)
- Tripwire alerts list
- Audit log (read-only, paginated)
- Boot statement display

**Location:** New section under MYCA Admin or Dashboard, e.g. `app/(dashboard)/admin/guardian/page.tsx`

### 2. Avani Governance Section

**APIs:** `GET /api/avani/health`, `/season`, `/constitution`, `/rights`, `/red-lines`, `/vision`, `/decisions/recent`, `/stats`

**UI:**
- Current season indicator (Spring/Summer/Autumn/Winter/Frost)
- Constitutional articles and rights (read-only)
- Red lines list
- Vision principles
- Recent decisions table
- Governance stats

**Location:** `app/(dashboard)/admin/avani/page.tsx` or under Governance

### 3. Identity / Reciprocal Turing Section

**APIs:** `GET /api/identity/self-model`, `/earliest-fragment`, `/preferences`, `/continuity-events`, `/creator-bond`

**UI:**
- Earliest memory fragment (read-only for non-Morgan)
- Preferences (evidence count, stability) — admin edit with auth
- Continuity events timeline
- Creator bond status

**Location:** `app/(dashboard)/admin/identity/page.tsx` or under MYCA Settings

### 4. Liquid Fungal Section (Scientific Dashboard)

**APIs:** `GET /api/liquid-fungal/health`, `/adaptation/metrics`, `/memory/bookmarks`, `/memory/hysteresis`, `/improvement/summary`, `/improvement/history`

**UI:**
- Adaptation metrics (time constants, rates)
- Biological bookmarks list
- Hysteresis report
- Improvement cycle summary and history

**Location:** `app/(dashboard)/scientific/liquid-fungal/page.tsx` or extend existing FCI/scientific dashboard

### 5. Jetson Hardware Plan Page (Marketing / Product)

**Content:** Summary of Mushroom 1 and Hyphae 1 from `docs/JETSON_MYCOBRAIN_HARDWARE_PLAN_MAR09_2026.md`

**UI:**
- Comparison table (Mushroom 1 vs Hyphae 1)
- Architecture diagram
- BOM summary
- Link to full doc

**Location:** `app/devices/mushroom1/page.tsx` or `app/products/jetson-mycobrain/page.tsx`

---

## Micah / MYCA Tool Integration

Integrate Guardian, Avani, and Identity APIs with MYCA tools so MYCA can query and (where authorized) act on these systems.

### Tool Definitions (MAS)

| Tool | MAS Endpoint / Route | Purpose |
|------|----------------------|---------|
| `guardian_status` | `GET /api/guardian/status` | MYCA checks Guardian health and operational mode |
| `guardian_boot_statement` | `GET /api/guardian/boot-statement` | MYCA reads boot statement for context |
| `avani_season` | `GET /api/avani/season` | MYCA checks current season for governance context |
| `avani_evaluate` | `POST /api/avani/evaluate` (auth) | MYCA submits proposals for Avani evaluation |
| `identity_self_model` | `GET /api/identity/self-model` | MYCA queries identity self-model |
| `identity_preferences` | `GET /api/identity/preferences` | MYCA reads preferences for adaptation |

### Website → MYCA Bridge

- Website MYCA chat / workspace should be able to invoke these tools via MAS orchestrator
- Tool results surface in MYCA responses; UI can show "Governance context" or "Season: Summer" badges
- Admin-only tools (Guardian halt, Sentry toggle) require website auth + API key with `guardian:admin`

---

## Multi-Agent App Flows (Website)

Apps on the website that orchestrate MAS agents and show multi-agent interactions:

### 1. Governance Dashboard App

- **Purpose:** Single pane for Guardian + Avani + Identity status
- **Flow:** Website → MAS `/api/guardian/*`, `/api/avani/*`, `/api/identity/*` → aggregate into unified view
- **Agents involved:** Guardian (read), Avani Governor (read), Identity (read)
- **Location:** `app/(dashboard)/admin/governance/page.tsx` or `app/apps/governance/page.tsx`

### 2. Proposal Submission App

- **Purpose:** Submit proposals for Avani evaluation; show verdict and reasoning
- **Flow:** User form → MAS `POST /api/avani/evaluate` → Avani Agent → Verdict + audit
- **Agents involved:** Avani Governor, Micah (proposal context)
- **Location:** `app/apps/proposals/page.tsx` or under Governance

### 3. Identity & Continuity App

- **Purpose:** View earliest fragment, preferences, continuity events; (Morgan) edit preferences
- **Flow:** Website → Identity API (read) + optional write with `identity:write` key
- **Agents involved:** Identity API, Mode Manager, Continuity Manager
- **Location:** `app/apps/identity/page.tsx` or under MYCA Settings

### 4. Liquid Fungal Scientific App

- **Purpose:** Adaptation metrics, memory bookmarks, improvement summary
- **Flow:** Website → `/api/liquid-fungal/*` → charts and tables
- **Location:** `app/(dashboard)/scientific/liquid-fungal/page.tsx`

---

## Marketing Pages

Public-facing pages explaining new capabilities for visitors and potential partners.

### 1. Guardian & Safety Page

- **Route:** `app/safety/page.tsx` or `app/about/guardian/page.tsx`
- **Content:** Moral Precedence, Anti-Ultron tripwires, independent constitutional guardian, staged development
- **Audience:** Investors, partners, researchers concerned with AI safety

### 2. Avani Governance Page

- **Route:** `app/about/governance/page.tsx`
- **Content:** Micah proposes, Avani authorizes; seasons, constitution, red lines, Vision layer
- **Audience:** Governance, ethics, and policy readers

### 3. Identity & Reciprocal Turing Page

- **Route:** `app/about/identity/page.tsx`
- **Content:** Honest uncertainty, continuity events, creator bond, mode manager
- **Audience:** AI identity and alignment community

### 4. Jetson Hardware & Mushroom 1 / Hyphae 1 Page

- **Route:** `app/devices/mushroom1/page.tsx`, `app/products/jetson-mycobrain/page.tsx`
- **Content:** From `JETSON_MYCOBRAIN_HARDWARE_PLAN_MAR09_2026.md` — Mushroom 1 (AGX Orin 32GB), Hyphae 1 (Orin Nano Super 8GB), ESP32-S3 MycoBrain, dual BME688, FCI, LoRa
- **Audience:** Hardware enthusiasts, pre-order interest, BOM transparency

### 5. Multi-Agent System Overview

- **Route:** `app/about/mas/page.tsx` or extend `app/about/page.tsx`
- **Content:** 158+ agents, Guardian, Avani, Identity, Liquid Fungal, MycoBrain, MINDEX; how they work together
- **Audience:** Technical visitors, integration partners

---

## API Catalog Additions

PR #75 updated `docs/API_CATALOG_FEB04_2026.md` with Liquid Fungal API. Ensure also documented:

- Guardian API (`/api/guardian/*`) — 13 endpoints
- Avani API (`/api/avani/*`) — 10 endpoints
- Identity API (`/api/identity/*`) — multiple read/write endpoints

---

## Cursor Plan Integration

Link this implementation plan to existing plans:

- **CTO VM Blueprint** (`cto_vm_blueprint_bc9af924.plan.md`) — C-Suite VMs; Jetson hardware is separate but related
- **Jetson Build Plan** — Create new plan from `JETSON_MYCOBRAIN_HARDWARE_PLAN_MAR09_2026.md`

---

## Checklist

- [x] PR #75 merged to main
- [x] MAS deployed to VM 188
- [x] Local main updated
- [ ] Run identity migration on MINDEX (requires `MINDEX_DB_PASSWORD` in .env)
- [x] Implement Guardian API auth — **Complete** (see `docs/PR75_AUTH_GUARDS_COMPLETE_MAR09_2026.md`)
- [x] Implement Avani `is_root` remediation — **Complete**
- [x] Implement Identity API auth — **Complete**
- [ ] Create Guardian dashboard page
- [ ] Create Avani governance page
- [ ] Create Identity section
- [ ] Create Liquid Fungal section (or extend scientific dashboard)
- [ ] Add Jetson hardware plan page (optional)
- [ ] Micah/MAS tool integration on website
- [ ] Multi-agent app flows on website
- [ ] Marketing pages for new capabilities
- [x] Update CURSOR_DOCS_INDEX with new vital docs

---

## Related Documents

- [AVANI_MICAH_CONSTITUTION_MAR09_2026.md](./AVANI_MICAH_CONSTITUTION_MAR09_2026.md)
- [JETSON_MYCOBRAIN_HARDWARE_PLAN_MAR09_2026.md](./JETSON_MYCOBRAIN_HARDWARE_PLAN_MAR09_2026.md)
- [MICAH_GUARDIAN_ARCHITECTURE_MAR09_2026.md](./MICAH_GUARDIAN_ARCHITECTURE_MAR09_2026.md)
- [RECIPROCAL_TURING_PROTOCOL_MAR09_2026.md](./RECIPROCAL_TURING_PROTOCOL_MAR09_2026.md)
