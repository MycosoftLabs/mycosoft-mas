# Mycosoft Platform Audit — Inventory, Services, and Gaps (May 2, 2026)

**Date:** May 2, 2026  
**Status:** Audit + inventory (evidence-backed where noted). Not a deployment checklist.  
**Related:** `docs/SYSTEM_GAPS_AND_REMAINING_WORK_FEB10_2026.md`, `docs/NATUREOS_FULL_STACK_ARCHITECTURE_AND_INTEGRATIONS_MAY02_2026.md`, `docs/SYSTEM_REGISTRY_FEB04_2026.md`, `docs/API_CATALOG_FEB04_2026.md`, `.cursor/gap_report_latest.json`

---

## 1. Purpose

Single place to answer:

- What **ran healthy** from the dev workstation on the LAN at audit time.
- What **repos, VMs, and major surfaces** exist.
- Where **Cursor subagents**, **MAS agents**, **website apps**, and **hardware/firmware** fit.
- What **gaps** are known (registry docs, gap scan, and manual triage).

**Fix scope:** This pass prioritized **measurement and documentation**. Many “501” website routes are **intentional** until API keys or upstream services exist; changing them without product approval would be misleading. Broken doc links and ambiguous metrics were corrected in this doc and in `MASTER_DOCUMENT_INDEX.md`.

---

## 2. Live verification (dev PC → LAN)

| Target | URL | Result |
|--------|-----|--------|
| MAS orchestrator | `http://192.168.0.188:8001/health` | **200** (May 2, 2026) |
| MINDEX API | `http://192.168.0.189:8000/health` | **200** (May 2, 2026) |
| MAS n8n | `http://192.168.0.188:5678/healthz` | **200** (May 2, 2026) |
| Prometheus (MAS VM) | `http://192.168.0.188:9090/-/healthy` | **200** from dev PC (May 3, 2026) after `docker compose up -d prometheus` on **188** (`~/mycosoft/mas`) + UFW allow **9090** from LAN; ops: **`scripts/remediate_prometheus_mas188.py`**, **`docs/PROMETHEUS_MAS_VM188_RUNBOOK_MAY03_2026.md`**. |

**Not probed in this pass:** Supabase project health (needs dashboard/API key), Redis/Qdrant/Postgres raw ports on 189 (assumed up when MINDEX `/health` is 200), Voice Legion **241**, Earth-2 Legion **249**, MYCA VM **191**.

---

## 3. Workspace and VMs (canonical)

**Repos (multi-root):** MAS (`mycosoft-mas`), Website (`WEBSITE/website`), MINDEX (`MINDEX/mindex`), MycoBrain, NatureOS, Mycorrhizae, NLM, SDK, platform-infra.

**Production-style VMs:**

| VM | IP | Role |
|----|-----|------|
| Sandbox | 192.168.0.187 | Website Docker, optional edge APIs |
| MAS | 192.168.0.188 | Orchestrator **8001**, n8n **5678**, Ollama **11434**, Prometheus **9090** |
| MINDEX | 192.168.0.189 | Postgres, Redis, Qdrant, API **8000** |
| Voice Legion | 192.168.0.241 | Moshi **8998**, Bridge **8999**, Ollama **11434** |
| Earth-2 Legion | 192.168.0.249 | Earth-2 API **8220** (typical) |
| MYCA workspace | 192.168.0.191 | Separate automation plane (do not confuse with MAS n8n) |

---

## 4. Cursor subagents (MYCA “Andy” operator kit)

Definitions live under merged `.cursor/agents/` (synced from repos to user Cursor). **52** agent markdown files are present in the MAS repo’s `.cursor/agents` tree (includes specialties: `backend-dev`, `website-dev`, `voice-engineer`, `myca-voice`, `n8n-ops`, `n8n-workflow-sync`, `database-engineer`, `memory-engineer`, `crep-agent`, `deploy-pipeline`, `gap-agent`, `route-validator`, `terminal-watcher`, etc.).

**Gap:** Subagents do not auto-run; orchestration rules require the parent agent to **read** the relevant `.md` and apply protocols.

---

## 5. MAS / MYCA runtime agents

Python codebase contains **many** `*Agent` classes under `mycosoft_mas/agents/` (v1, v2, clusters, lab, natureos, integration, memory, voice-adjacent, corporate, device, etc.). Authoritative lists belong in **`docs/SYSTEM_REGISTRY_FEB04_2026.md`** and **`docs/API_CATALOG_FEB04_2026.md`** — refresh when adding agents or routers.

**Gap:** Not every agent class is guaranteed registered or exercised at runtime; registry vs code drift is possible.

---

## 6. Website — major product surfaces

**Public / marketing:** Home, devices, defense narratives, legal pages — see sitemap and `app/` tree.

**NatureOS dashboard (authenticated tiers):** Sidebar/nav is driven from `WEBSITE/website/components/dashboard/nav.tsx`. Representative **Apps** entries:

- Nature Statistics, Fungi Compute, Earth Simulator, Virtual Petri Dish, Biology Simulator (company), Compound Analyser, Aerosol (company), Ancestry Database, Growth Analytics (company), Tools hub  
- **AI:** AI Studio (company), NLM Training, Workflows (company)  
- **Development:** API Gateway, Functions, SDK, Cloud Shell  
- **Infrastructure:** Device Network, MycoBrain Console, Sporebase Monitor, Ground Station, Monitoring, Storage, plus defense-adjacent entries in other sections  

**Canonical integration docs:** `docs/NATUREOS_FULL_STACK_ARCHITECTURE_AND_INTEGRATIONS_MAY02_2026.md`, per-app docs under `docs/NATUREOS_APP_*_MAY01_2026.md`, May 3 MVP completion docs listed in `docs/MASTER_DOCUMENT_INDEX.md`.

**MYCA / search:** Fluid Search, `/myca`, test-voice — see voice and MYCA Alive docs in `CURSOR_DOCS_INDEX.md`.

---

## 7. Website BFF — explicit HTTP 501 (configuration gaps, not necessarily bugs)

Many Next.js BFF routes return **501** when API keys are unset or when the HTTP contract marks a path as not implemented (honest failure vs mock data). **Canonical file-by-file list:** **Appendix A**.

**Gap:** Aggregated “501 route” counts from automated scans often **include false positives** (e.g. scripts that mention `501` in regex). Use Appendix A + `route-validator`, not raw scanner totals.

---

## 8. MINDEX, NatureOS .NET, Mycorrhizae, MycoBrain

| System | Role | Doc pointers |
|--------|------|--------------|
| **MINDEX** | Postgres + Redis + Qdrant + FastAPI **8000** | MINDEX `docs/`, `ALL_LIFE_ETL_MAY02_2026.md` |
| **NatureOS core-api** | C# SignalR, controllers | `docs/NATUREOS_DOTNET_CORE_API_RUNBOOK_MAY02_2026.md` |
| **Mycorrhizae** | Protocol API **8002** | `Mycorrhizae/mycorrhizae-protocol` |
| **MycoBrain** | ESP32 firmware variants + local/sandbox service **8003** | `mycobrain/docs/`, MAS `services/mycobrain/` |

---

## 9. n8n, Redis, Supabase, Prometheus

| Service | Expected | Audit note |
|---------|----------|------------|
| **n8n (MAS)** | 188:5678 | **200** `/healthz` from dev PC |
| **Redis** | 189:6379 | Use MINDEX stack health / ops runbooks |
| **Supabase** | Cloud project | Required for auth, storage, CREP waypoints (see `CREP_WAYPOINTS_SUPABASE_COMPLETE_MAY03_2026.md`); validate keys in `.env.local` / VM secrets |
| **Prometheus** | 188:9090 | **Unreachable** from dev LAN in latest probe — runbook: `docs/PROMETHEUS_MAS_VM188_RUNBOOK_MAY03_2026.md` |

---

## 10. Automated gap scan snapshot (May 2–3, 2026)

Source: `python scripts/gap_scan_cursor_background.py` → `.cursor/gap_report_latest.json` (`local_workspace_scan`, **102** indexed files with gaps).

**Summary fields (noisy — triage required):**

| Metric | Count |
|--------|-------|
| TODO/FIXME-style hits (workspace) | 695 |
| Stub-pattern hits | 281 |
| “501 / NotImplemented” pattern hits | 143 |
| Bridge-gap mentions | 100 |
| Index-referenced files with gaps | 102 |
| Index line-level gaps | 534 |

**By-repo excerpt (`by_repo` in JSON):**

| Repo | routes_501_count (scanner) | Notes |
|------|---------------------------|--------|
| mas | 97 | Includes scripts/tests — **not** all HTTP routes |
| website | 40 | Mix of real BFF 501 + string matches |
| mindex | 5 | Review FastAPI routers |
| natureos | 1 | Review .NET controllers |

**Gap:** Scanner totals **must not** be quoted as “broken API count” without human filtering.

---

## 11. Consolidated gap list (prioritized themes)

| Priority | Gap | Evidence / action |
|----------|-----|-------------------|
| Critical | Base64 instead of AES-GCM in legacy security paths | `SYSTEM_GAPS_AND_REMAINING_WORK_FEB10_2026.md` — security-auditor |
| High | Prometheus **9090** not reachable from dev LAN | Runbook + `scripts/diagnose_prometheus_mas188.py`; start container or open **9090** on 188 |
| High | Voice stack completeness (~40%) | Registry + voice docs |
| High | WebSocket platform gap | Multiple dashboards expect realtime |
| High | Doc drift: **`docs/MASTER_INVENTORY_MAY02_2026.md`** missing | Was linked from MASTER_DOCUMENT_INDEX — **replaced** by this doc until `build_master_inventory.py` produces the file |
| Medium | Financial / research / WiFiSense stubs | Stub-implementer + registry |
| Medium | Missing or redirect-needed marketing pages | route-validator + `SYSTEM_GAPS_*` |
| Medium | Supabase RLS / broker patterns unchecked | `gap_report_latest.json` index_gaps → MYCODAO plan |
| Low | 80+ TODOs across Python | code-auditor triage |
| Ops | Gap scan false positives in `todos_fixmes` (e.g. word “BUG” in prose) | Tighten scanner or filter by path |

---

## 12. How to refresh this audit

1. Health: curl/Invoke-WebRequest MAS, MINDEX, n8n, Prometheus from **trusted** network paths.  
2. Run `python scripts/gap_scan_cursor_background.py` from MAS repo.  
3. Run website `route-validator` / smoke tests per `docs/NATUREOS_STAGING_MATRIX_MAY02_2026.md`.  
4. Update **`docs/SYSTEM_REGISTRY_FEB04_2026.md`** and **`docs/API_CATALOG_FEB04_2026.md`** when agents or APIs change.

---

## Appendix A — Website BFF canonical `501` responses (`status: 501` in `route.ts`)

Source: grep `status:\s*501` under `WEBSITE/website/app/api/**/route.ts` (May 3, 2026). These are **configuration or contract** responses, not scanner false positives. Changing **501 → 503** (or other codes) is a **product** decision — requires explicit approval for website behavior.

| Route file | Condition / env var |
|------------|---------------------|
| `app/api/transit/marta/route.ts` | `MARTA_API_KEY` unset |
| `app/api/transit/cta-bus/route.ts` | `CTA_BUS_TRACKER_API_KEY` unset |
| `app/api/transit/wmata/route.ts` | `WMATA_API_KEY` unset |
| `app/api/transit/metrolink/route.ts` | `METROLINK_API_KEY` unset |
| `app/api/transit/dart/route.ts` | `DART_API_KEY` unset |
| `app/api/transit/trimet/route.ts` | `TRIMET_API_KEY` unset |
| `app/api/transit/cta-train/route.ts` | `CTA_TRAIN_TRACKER_API_KEY` unset |
| `app/api/transit/511-bay/route.ts` | `TRANSIT_511_API_KEY` unset |
| `app/api/crep/airnow/bbox/route.ts` | `AIRNOW_API_KEY` unset |
| `app/api/crep/airnow/current/route.ts` | `AIRNOW_API_KEY` unset |
| `app/api/shodan/count/route.ts` | `SHODAN_API_KEY` unset |
| `app/api/shodan/host/[ip]/route.ts` | `SHODAN_API_KEY` unset |
| `app/api/shodan/search/route.ts` | `SHODAN_API_KEY` unset (also referer gating for NatureOS — see file) |
| `app/api/mindex/ingest/[type]/route.ts` | **GET** handler returns **501** (“query not implemented”; route is write-oriented) |

---

## 13. References

- `docs/MASTER_DOCUMENT_INDEX.md` — full TOC  
- `.cursor/CURSOR_DOCS_INDEX.md` — vital docs for agents  
- `docs/SYSTEM_GAPS_AND_REMAINING_WORK_FEB10_2026.md` — thematic backlog  
- `docs/PROMETHEUS_MAS_VM188_RUNBOOK_MAY03_2026.md` — Prometheus on 188  
- `scripts/gap_scan_cursor_background.py` — workspace scanner  
- `scripts/diagnose_prometheus_mas188.py` — SSH Prometheus diagnostics  
