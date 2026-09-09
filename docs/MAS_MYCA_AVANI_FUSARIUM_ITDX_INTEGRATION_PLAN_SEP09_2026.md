# MAS / MYCA / AVANI / Fusarium ITDX Integration Plan — 09 September 2026

**Date:** 09 September 2026  
**Status:** Plan only. Not a completion badge. Not shipped to Sandbox 187.  
**Authority:** Morgan 09 Sep 2026 — fix MAS, MYCA, AVANI, and all agents so they work with the ITDX demo **and** future Fusarium products. No fake green.  
**Related:** `docs/CURSOR_ITDX26_INTEGRATION_SEP08_2026.md`; `docs/CURSOR_ITDX26_CODEX_V13_CONNECT_SEP09_2026.md`; website worktrees `website-itdx` / `website-itdx-codex-v13`; Fusarium twins inventory `docs/FUSARIUM_TWINS_BACKEND_INVENTORY_AND_ACTION_MANIFEST_SEP01_2026.md`.  
**Parallel work:** Another agent (`35796f25`) is adding `/api/itdx/situation-assessment` and Task 8 mounts. **Do not fight that lane.** Treat those files as the in-flight router. Review, harden, and consume — do not rewrite a competing API.  
**Protected files (do not edit):** `mycosoft_mas/core/orchestrator.py`, `orchestrator_service.py`, `mycosoft_mas/safety/guardian_agent.py`, `sandboxing.py`, `mycosoft_mas/security/**`, `mycosoft_mas/myca/constitution/**`, `config/myca_soul.yaml`, `mycosoft_mas/consciousness/soul/identity.py`.  
**CUI / CMMC:** UNCLASSIFIED commercial. Official Army injects stay STOP_INGEST / lab-only. Mycosoft is **pursuing** CMMC L2 — not claiming compliant. **RJ Ricasata is CFO.** No CUI in this plan.

---

## 1. Why they are not working (evidence, 09 Sep 2026)

The ITDX demo **looks** like it has MYCA / AVANI / NLM because FormSpace `:8766` and the local 8765 kit run a **deterministic local envelope**. That is not MAS. The live MAS on `192.168.0.188:8001` is up, degraded, and only **partially** bound. Fusarium consumers still call the wrong host, the wrong path, or a route that deadlocks.

### 1.1 One-page cause table

| Layer | What operators expect | What is actually true | Evidence (09 Sep 2026) |
|---|---|---|---|
| MAS process | Healthy orchestrator with agents | **`status=degraded`**. Collectors skipped. `health.agents=[]`. `git_sha=3388505` (“Restore draft-only DocuSign API routes”) while ITDX files were **hot-copied**, not committed. | `GET /health` 200; component `collectors` message `Collectors skipped (MAS_SKIP_BACKGROUND_STARTUP)`; `MAS_SKIP_BACKGROUND_STARTUP=1` in `myca_main.py` startup. Local HEAD is `12b215c` on `cursor/field-operator-live-observations-sep01`. ITDX router files are **uncommitted** (`?? itdx_api.py`, `?? itdx_task8_agent.py`). |
| Task 8 / seven-role | Seven live MAS agents consulted | Router **exists on 188** (`/api/itdx/task8`, `/api/avani/task8`, `/api/myca/task8`). **IntentionAgent fails** (`No module named 'mycosoft_mas.engines.intention.intention_service'`). Payload still reports `seven_role.qualification=BOUND` / `role_count=7`. AVANI rubber-stamps all three COAs **PASS**. | Live `GET /api/avani/task8` 200. Role `coa_proposer` `ok=false` with that ImportError. Options `coa-1/2/3` all `formspace_gate=PASS`, `approved=true`, reason `All constitutional checks passed.` |
| Situation assessment | Earth Sim channels scored or honestly UNQUALIFIED | OpenAPI lists `GET,POST /api/itdx/situation-assessment`. **GET hung** (10s, 0 bytes). Implementation calls **itself** over HTTP (`MAS_INTERNAL_URL` default `http://127.0.0.1:8001`) for NLM / Earth-2 / physics / AVANI / devices. Single-worker + sequential self-GET **deadlocks**. Earth-2 unreachable; physics 502. | OpenAPI 967 paths include the route. Probe timeout. Code: `itdx_api.py` `_get_json` / `_post_json`. `GET /api/earth2/status` → `available=false`, `192.168.0.249:8220` unreachable. `GET /api/physics/health` → HTTP 502. |
| NLM | Qualified predict for Task 12 / biology / chemistry | **`model_loaded=false`**, health `degraded`, `uptime_seconds=0`. `POST /api/nlm/predict` still **200** with stub text *“The NLM model is not yet fully trained”* and **hardcoded `confidence=0.85`**. That number is **not** a Task 12 p and must never paint as SCORED. | Live health + predict. Code: `nlm/inference/service.py` `confidence=0.85  # Placeholder`; `nlm/models/base_model.py` stub paragraph. |
| MYCA consciousness | Awake brain coordinating agents | **`/api/myca/health` and `/api/myca/status` = `dormant`, `is_conscious=false`.** Voice brain HTTP is up (`/voice/brain/health` 200, providers listed healthy) but that is **not** a 7-role Task 8 and not a Fusarium situation score. | Live JSON. Skip-startup means background init (agent spawn, collectors) never ran. |
| AVANI | One governor used by ITDX + Fusarium | **Governor exists.** `/api/avani/health` 200. `/api/avani/evaluate` 200 (always approve on low-risk observe). **`/api/avani/status` 404** — website and Fusarium catalog poll that path. Website `app/api/avani/status` is an **embedded local engine**, not the MAS governor. | OpenAPI: 14 `/api/avani/*` paths, no `/status`. Website `lib/config/api-urls.ts` `STATUS: "/api/avani/status"`. Fusarium catalog `avani-status` → `/api/avani/status`. |
| 8765 lab → MAS | Kit binds NLM / MYCA / MINDEX | Defaults point at **wrong localhost ports**: NLM `127.0.0.1:8000` (MINDEX API port), MINDEX `127.0.0.1:8003` (MycoBrain), MYCA `127.0.0.1:8001` (no local MAS; 188 is the orchestrator). Loopback-only + 5s timeout. Bind state stays `not_bound` / `UNQUALIFIED`. | `website-itdx/itdx/local/itdx/integrations.py` and `website-itdx-codex-v13/itdx/app/itdx/integrations.py`. Sep 08/09 docs already recorded NLM/MYCA UNQUALIFIED on the extract. |
| Website consumers | Same-origin `/api/itdx/*` on 3010 | **Main `WEBSITE/website` has no `app/api/itdx`.** Worktree `website-itdx` has overlay / registry / v12 only. Codex worktree exposes **`/api/fusarium/itdx/task8`** (owner 401) and probes MAS paths with an **8s** timeout. Live 3010: `/api/itdx/situation-assessment` **404**, `/api/itdx/task8` **404**, `/api/fusarium/itdx/task8` **401**, `/fusarium/itdx` **307** (login). | Probed `http://127.0.0.1:3010` this session. Codex `lib/itdx/task8-client.mjs` `MAS_TASK8_PATHS` + 8s abort. |
| Agent registry | All Task 8 roles registered and startable | Catalog `GET /agents/registry/` 200, **48** definitions including `itdx-task8`. `/agents/` list is **401**. Health `agents: []` because skip-startup never instantiated the runtime set. Intention **module missing** so COA proposer cannot `process_task`. | Registry sample included `itdx-task8`, `mycology_bio`, financials. Intention error on live Task 8. |
| FormSpace math | Confused with production NLM | `:8766` recorded seed-11 math **PASS**. That is **not** loaded NLM and **not** Fusarium-gateway MYCA. Treating it as a green MAS badge is the failure Morgan called out. | `docs/CURSOR_ITDX26_INTEGRATION_SEP08_2026.md` §09 Sep walkthrough. |

### 1.2 Live probe log (this session)

Host `192.168.0.188` **pings**. TCP 8001 is intermittently slow (PowerShell `Test-NetConnection` false; `curl` 2–20s). Local `127.0.0.1:8001` is **down** (dev PC is not MAS).

| Probe | Result |
|---|---|
| `GET /health` | 200 `degraded`. postgres/redis/crep healthy. collectors skipped (`MAS_SKIP_BACKGROUND_STARTUP`). `git_sha=3388505fb4f0e6c0bd561b981c889c66187b50cd`. `myca_route_mounts` true for consciousness_chat, grounding_status, conversation_memory, search_memory, voice_orchestrator. `agents=[]`. |
| `GET /openapi.json` | 200, **967** paths. ITDX: `/api/itdx/health`, `/task8`, `/situation-assessment`, `/authority`. AVANI: health/evaluate/evaluate-message/constitution/… + **`/api/avani/task8`**. **No `/api/avani/status`.** NLM: health/predict/load/unload/training/* . MYCA: health/status/chat + **`/api/myca/task8`**. |
| `GET /api/avani/status` | **404** |
| `GET /api/avani/health` | 200 `avani-governor`, season spring, 3/3 approved |
| `POST /api/avani/evaluate` | 200 `approved=true`, `reason=All constitutional checks passed.` |
| `GET /api/avani/task8` | 200 full Task 8 payload (see §1.1). ~20s. |
| `GET /voice/brain/health` | 200 `myca-brain-api` `1.0.0-memory-integrated` |
| `GET /voice/brain/status` | 200 brain initialized; ollama/nemotron/gemini/claude/openai listed healthy |
| `GET /api/nlm/health` | 200 `degraded`, `model_loaded=false`, `uptime_seconds=0.0` |
| `GET /api/nlm/predict` | **405** (POST only) |
| `POST /api/nlm/predict` | 200 stub + “not yet fully trained” |
| `GET /api/itdx/health` | 200 `itdx-task8/v1` + `itdx.situation_assessment/v1` + 7 kit role labels |
| `GET /api/itdx/situation-assessment` | **timeout / 0 bytes** (deadlock risk, §4) |
| `GET /api/registry/agents` | **404** (wrong path; live catalog is `/agents/registry/`) |
| `GET /agents/registry/` | 200, 48 agents |
| `GET /agents/` | **401** |
| `GET /api/myca/health` | 200 `dormant` / `is_conscious=false` |
| `GET /api/myca/status` | 200 same dormant counters (0 thoughts, 0 agents_coordinated) |
| `GET /api/earth2/status` | 200 `available=false`, Legion `192.168.0.249:8220` unreachable |
| `GET /api/physics/health` | **502** |

Website 3010 (whatever worktree is bound this morning):

| Path | Result |
|---|---|
| `/api/itdx/situation-assessment` | **404** |
| `/api/itdx/task8` | **404** |
| `/api/fusarium/itdx/task8` | **401** (route exists; owner gate) |
| `/api/avani/status` | timeout / not proven |
| `/fusarium/itdx` | **307** (auth redirect) |

### 1.3 Code facts (do not re-invent)

Already on disk / on 188 (agent `35796f25` lane):

- `mycosoft_mas/core/routers/itdx_api.py` — Task 8 + situation assessment + aliases `/api/avani/task8`, `/api/myca/task8`, `/api/itdx/authority`.
- `mycosoft_mas/agents/itdx_task8_agent.py` — maps kit roles to existing v2 agents. **No invented LLM personas.**
- `mycosoft_mas/core/myca_main.py` ~1208–1218 mounts those routers (try/except ImportError).
- `mycosoft_mas/agents/__init__.py` safe-imports `ITDXTask8Agent`.
- `scripts/_itdx_ship_188.py` / `_itdx_restart_188.py` — **SCP + `systemctl restart mas-orchestrator`**. Explains live routes with a stale `git_sha`.
- Tests: `tests/test_itdx_task8_api.py` — unit gates/Borda/schema only. **No live fail-closed HTTP suite yet.**

Website / 8765:

- Codex `app/api/fusarium/itdx/task8/route.ts` — owner-only; probes MAS Task 8; falls back to FormSpace recorded + `POST /api/avani/evaluate`; comment still says “Per-role Task 8 API is not published yet” (stale relative to 188).
- `lib/itdx/task8-client.mjs` — 8s timeout; paths `/api/avani/task8`, `/api/myca/task8`, `/api/itdx/task8`, `/api/fusarium/task8` (last is **not** on MAS OpenAPI).
- Main website Fusarium tree is launchpad/auth only — **no ITDX workspace in `WEBSITE/website`**.
- 8765 `integrations.py` defaults are **localhost port-swapped** (§1.1).

---

## 2. Target architecture (ITDX and every future Fusarium product)

One MAS contract. Fusarium apps are **consumers**. No per-app fake agents. No second MYCA. No seven invented LLM personas.

```text
Fusarium product (ITDX, Earth Sim, CREP, twins, later apps)
        │  owner session, same-origin BFF
        ▼
Website BFF  /api/fusarium/<product>/…   (auth, no CUI, no secrets in NEXT_PUBLIC)
        │  MAS_API_URL=http://192.168.0.188:8001
        ▼
MAS contract (this plan)
  POST /api/itdx/situation-assessment
        slice in → channels + agent_ids + UNQUALIFIED/NOT_SUPPLIED/SCORED
  POST /api/itdx/task8
        same slice → 7 kit roles bound to existing agent_ids + AVANI gate
  POST /api/avani/evaluate           (governor only)
  GET  /api/avani/health             (plus a status alias — §5)
  GET  /api/nlm/health
  POST /api/nlm/predict              (qualified only when model_loaded && not stub)
  GET  /api/myca/health
  GET  /voice/brain/health           (voice path; not a situation score)
        │
        ├── existing agents (process_task)  grounding / intention / planner / reflection / avani / …
        ├── NLM service (load real weights or stay UNQUALIFIED)
        ├── Earth-2 Legion 249:8220 when actually reachable
        └── MINDEX 189:8000 for taxonomy / embeddings (empty = empty, not fake rows)
```

### 2.1 Situation slice (in)

Canonical body (`itdx.situation_assessment/v1`). Accept website `slice` as alias of `ao` (already in `itdx_api._normalize_map_slice`).

| Field | Rule |
|---|---|
| `origin` | `SYNTHETIC_EXERCISE` for ITDX demo. Never imply live COP. |
| `execution` | `ADVISORY_ONLY`. No actuator. |
| `synthetic` / `live_cop` | `true` / `false` on every response. |
| `clock` | ISO-8601 or omit. |
| `ao` / `slice` | name, bbox, center. Empty → Fort Stewart **demo** slice only if caller asks for demo; production Fusarium must send a real slice or get `NOT_SUPPLIED`. |
| `assets` / `units` | declared markers only. IDs resolve to **this payload**, not SME truth. |
| `goal` / `constraints` | optional envelope for Task 8. |

### 2.2 Channel scores (out)

Every channel is an object. **Missing data never becomes `p=0.73`.**

```text
status: SCORED | UNQUALIFIED | NOT_SUPPLIED
agent_id: existing registry id or null
p: number | null          # only if a labeled, loaded model produced it
uncertainty: number | null
error: string | null
note: human reason
live: raw probe crumbs (http, excerpt) — not a second score
```

Channel order (already in `CHANNEL_KEYS` — keep):

`physics`, `biology`, `chemistry`, `economics`, `weather`, `topology`, `biometry`, `equipment_weapons_assets`, `officer_capability`, `persona`, `information`, `decision_authority`

Fusion keys stay **NOT_SUPPLIED** until each has its own labeled process: `p_truth`, `p_deception`, `data_quality`. NLM class-p is **not** P(truth). Borda is **not** P(success). Official 1–5 Army rubric stays **NOT_SUPPLIED**.

### 2.3 Fusarium as consumers (not new MAS apps)

| Product | Consumes | Must not do |
|---|---|---|
| ITDX tab + Algorithm lab | Task 8 + situation-assessment + FormSpace recorded math (labeled local) | Invent 7 badges from FormSpace AVANI |
| Earth Simulator / CREP | situation-assessment channels + Task 14 GeoJSON flags | Replace real aircraft/vessels/sats; treat class-p as geo radius |
| Twins (Nature Statistics, Aerosol, Biology Sim, Compound Analyser, Growth Analytics, Petri, Ancestry, Fungi Compute) | same situation contract when they need AO scores; existing domain APIs otherwise | Spawn `aerosol-agent` / `petri-agent` clones of Task 8 |
| Later Fusarium products | same two POSTs + AVANI evaluate | Per-app “MYCA” stubs |

Website BFFs stay owner-gated. **No 187 cutover** in this plan.

---

## 3. Role map — ITDX Task 8 → existing MAS agents

Kit labels (do not rename): State summarizer, COA proposer, Alternative planner, Skeptical critic, Evidence verifier, AVANI guardian, Human handoff.

| Kit role | MAS `agent_id` | Module | Live 09 Sep | Honesty rule |
|---|---|---|---|---|
| State summarizer | `grounding-agent` | `agents/v2/grounding_agent.py` | Bound; `process_task` success | Summarizes **declared** slice only |
| COA proposer | `intention-agent` | `agents/v2/intention_agent.py` | **Broken** — missing `mycosoft_mas.engines.intention.intention_service` | `bound=false` until import+process succeed. Templates alone ≠ bound |
| Alternative planner | `planner-agent` | `agents/v2/planner_agent.py` | Bound; `{planned:true}` | Distinct action types from envelope, not a field COA |
| Skeptical critic | `reflection-agent` | `agents/v2/reflection_agent.py` | Bound | Must surface failed checks. Agreement is not evidence |
| Evidence verifier | `grounding-agent` (same) | same | Bound; IDs vs submitted slice | Not SME entailment. Do not invent a second verifier persona |
| AVANI guardian | `avani-governor` | `avani/agents/avani_agent.py` + `AvaniGovernor` | Bound; **all PASS** | Gate DENY/PAUSE/PASS/REVIEW. Low-risk observe must not auto-green the demo |
| Human handoff | intended `secretary` | SecretaryAgent (Google Workspace) | **Not invoked** (honest). Row uses `itdx-task8` | Stay REVIEW / ADVISORY_ONLY. Do not fake secretary |

**Do not add:** CEO-as-Task-8, seven GPT personas, “ITDX Analyst 1–7”, or a new `Task8LLMAgent`. CEO / CTO / CFO agents stay in the corporate registry and are unused here. **CFO remains RJ.**

Qualification (fail closed):

```text
BOUND only if all 7 rows have bound=true AND error is null AND process_task status≠error
else UNQUALIFIED (today’s payload must flip — it currently marks BOUND with an Intention ImportError)
```

---

## 4. AVANI — what exists vs 404, and the Fusarium gate

### Exists on 188 (OpenAPI + curl)

| Path | Use |
|---|---|
| `GET /api/avani/health` | Governor + season + stats |
| `POST /api/avani/evaluate` | Constitutional proposal (ITDX / Fusarium write gate) |
| `POST /api/avani/evaluate-message` | MYCA chat/voice ingress (website `avani-governance.ts`) |
| `GET /api/avani/{constitution,rights,red-lines,vision,season,stats,decisions/recent}` | Read charter |
| `GET,POST /api/avani/task8` | Alias of Task 8 (added this morning) |

### 404 / mismatch

| Caller | Calls | MAS has | Fix (M2) |
|---|---|---|---|
| Website `AvaniProvider`, `api-urls.ts`, Fusarium catalog | `GET /api/avani/status` | **nothing** | Add **alias** `GET /api/avani/status` → same body as `/health` plus `backend_connected=true`. Do not invent a second engine. |
| Website BFF `app/api/avani/status` | embedded `getGovernanceState()` | local only | BFF should proxy MAS `/api/avani/health` (or the new alias). Embedded engine stays fallback with `backend_connected=false`. |
| Codex Task 8 fallback | `POST /api/avani/evaluate` | works, always approve | Keep evaluate. Tighten envelope for ITDX so “observe / request_sample / restore_link” is **REVIEW** unless evidence+goal+reversibility checks are explicit — not a silent PASS chorus. |

### How Fusarium uses AVANI later

1. **Ingress:** chat/voice/search → `POST /api/avani/evaluate-message` (already the website contract).  
2. **Actuation / COA:** `POST /api/avani/evaluate` then map `approved` → kit gate via `avani_to_task8_gate`.  
3. **Situation channel `decision_authority`:** gate only. Never P(command authority).  
4. **No second AVANI repo required** for the demo. Standalone `avani` weights mentioned in the website status note are out of scope.

Do **not** edit `guardian_agent.py` or constitution YAML to “make ITDX pass.”

---

## 5. NLM — stub vs load, how predict becomes qualified

### Today

1. `GET /api/nlm/health` → `model_loaded=false` (authoritative).  
2. `POST /api/nlm/predict` still runs `NLMService.predict` → `load_model()` may “succeed” on a stub `NLMBaseModel` that prints *not yet fully trained* and returns **`confidence=0.85`**.  
3. `itdx_api._nlm_channel_from_predict` already treats that phrase as UNQUALIFIED and **ignores** service confidence. **Keep that.**  
4. `uptime_seconds=0.0` on health is another tell the service is not a running trained worker.  
5. FormSpace 24-D SSM / Task 12 F1=1.0 on `:8766` is a **recorded bundle**, not this MAS service.

### Qualification rule (fail closed)

```text
NLM BOUND / channel SCORED only if:
  health.model_loaded == true
  AND predict.text does not match /not yet fully trained/i
  AND confidence is not the hardcoded 0.85 placeholder
  AND a real checkpoint exists (GET /api/nlm/training/checkpoints count>0)
  AND ops explicitly loaded via POST /api/nlm/load (do not load as a probe)
else UNQUALIFIED — p=null
```

### How to load (M3, ops-gated)

1. Inventory checkpoint path on 188 (`NLM` repo / configured `model_dir`). If none, **stop** — stay UNQUALIFIED.  
2. `POST /api/nlm/load` only when Morgan authorizes GPU/RAM on 188 or a Legion. Dev PC does **not** run NLM inference.  
3. Proof: health `model_loaded=true` **and** predict text changes **and** confidence is model-produced.  
4. Never paint FormSpace recorded F1 as production NLM.

---

## 6. Phased work (M0–M5)

Owner mapping is the **executing agent after this plan**, not a green checkbox.

### M0 — Inventory (this document)

- [x] Read last-72h ITDX docs.  
- [x] Probe 188 + 3010.  
- [x] Read AVANI / NLM / Task 8 / 8765 / website consumers.  
- [x] Freeze this plan in indexes (pointer pass below).  
- [x] Public OSINT + Google Maps client wired (`ITDX_EXTERNAL_SOURCES_INTEGRATION_SEP09_2026.md`). Google Directions key still missing.  
- [ ] **Do not** restart 188 again until M2 deadlock fix is in the same tree as `35796f25`.

### M1 — Contract freeze (docs + types only)

1. Publish the slice / channel / Task 8 JSON as the **only** Fusarium situation contract (`itdx.situation_assessment/v1`, `itdx-task8/v1`).  
2. Website Codex types already exist in `lib/itdx/*` — align names; do not add a third schema.  
3. Mark `/api/fusarium/task8` as **not on MAS**. BFF path is `/api/fusarium/itdx/task8` → MAS `/api/itdx/task8`.  
4. 8765 `integrations.py` target table (lab only; loopback still allowed):

| Service | Wrong default | Correct when binding MAS |
|---|---|---|
| NLM | `127.0.0.1:8000` | `http://192.168.0.188:8001` + `/api/nlm/health` |
| MYCA | `127.0.0.1:8001` if that process is absent | `http://192.168.0.188:8001` + `/api/myca/health` **and** `/voice/brain/health` as two separate binds |
| MINDEX | `127.0.0.1:8003` | `http://192.168.0.189:8000` |

Empty MINDEX species = empty. No fake taxonomy.

### M2 — Mount / harden routers (not orchestrator internals)

Coordinate with `35796f25`. Same files.

1. **Break the situation-assessment deadlock.** Stop HTTP-to-self. Call in-process: NLM service status, AvaniGovernor, earth2 client, device registry. If a worker must HTTP, use a second worker **or** a dedicated internal ASGI client that does not re-enter the same queue.  
2. Add `GET /api/avani/status` alias → health body + `backend_connected`.  
3. Fix Task 8 `bound` / `seven_role`: ImportError or `status=error` ⇒ `bound=false`, qualification UNQUALIFIED.  
4. Cap situation-assessment wall time (≤ 8s) and return partial channels with errors — never hang the worker.  
5. Earth-2 / physics failures stay `NOT_SUPPLIED` with the live error (already the intent).  
6. Tests: unit (already started) + the proof suite in §7.  
7. **188 deploy:** `systemctl restart mas-orchestrator` **only after** deadlock + qualification fixes are on the VM. Use existing `_itdx_restart_188.py` / ship script. Do not git-pull a dirty tree blindly; copy the same five files the ship script already lists. Refresh `git_sha` in health if the running tree is a hot-patch (honest SHA or `hotpatch=true`).

### M3 — Register agents and fix real binds

1. Keep `itdx-task8` in `agent_registry.py` (already being added).  
2. Repair **IntentionAgent** missing `intention_service` **without** touching orchestrator/guardian/soul. If the engine module is gone, `process_task` must return `status=error` and Task 8 stays UNQUALIFIED — do not stub a fake plan.  
3. Decide skip-startup: either keep `MAS_SKIP_BACKGROUND_STARTUP=1` for API recovery **and** document that `health.agents` will stay `[]`, or turn it off on 188 **after** confirming collectors will not wedge the API again. Default for the demo: **leave skip on**, do not pretend agents are running.  
4. MYCA remain `dormant` unless Morgan asks to awaken. Dormant ≠ Task 8 failure if Task 8 uses v2 agents directly. Persona channel stays NOT_SUPPLIED.  
5. Secretary / Google: still not invoked.

### M4 — Fusarium consumer (3010 worktree only; no 187)

1. Codex BFF: prefer MAS `/api/itdx/task8` + `/api/itdx/situation-assessment`; raise timeout above 8s **or** fail UNQUALIFIED on abort (do not fall back to seven green badges).  
2. Add same-origin `/api/itdx/situation-assessment` BFF **or** teach Earth panel to call `/api/fusarium/itdx/situation-assessment` — pick one and update Earth left panel. Today both 404 on the path Earth/docs mention.  
3. Main `WEBSITE/website` stays untouched until Morgan says merge PR #299. **No Sandbox rebuild.**  
4. 8765 stays loopback lab. Optional env overrides to 188 — never bake passwords.  
5. Future twins: import the same client (`situationAssessment(slice)`). No new agents.

### M5 — Proof suite + restart

Run §7 against 188. Any silent PASS is a failed milestone. Then, and only then, `systemctl restart mas-orchestrator` if the process was not already bounced with M2.

---

## 7. Proof tests (fail closed — no silent PASS)

Each test is **FAIL** unless the assertion holds. Do not `xfail` skip into green.

| ID | Command / probe | PASS only if | Today (09 Sep) |
|---|---|---|---|
| P0 | `curl -m 8 :8001/health` | HTTP 200. Body includes `MAS_SKIP_BACKGROUND_STARTUP` **or** `agents` non-empty — never both “healthy” and empty without the skip flag. | FAIL as a “healthy MAS” claim. PASS as degraded+skip (honest). |
| P1 | `GET /api/nlm/health` | `model_loaded` boolean present. If false, no UI may show NLM BOUND. | UNQUALIFIED (correct). |
| P2 | `POST /api/nlm/predict` ecology text | If health `model_loaded=false` **or** body contains “not yet fully trained”, situation channel biology/chemistry must be UNQUALIFIED and `p` null. **FAIL if any consumer stores 0.85 as p.** | Predict stub live. Channel path unproven (assessment hung). |
| P3 | `GET /api/avani/status` | HTTP 200 (after M2 alias). | **FAIL 404** |
| P4 | `POST /api/avani/evaluate` low-risk observe | HTTP 200 with `approved` boolean. ITDX Task 8 must not treat approve-all as seven-role success. | Evaluate works; Task 8 over-greens. |
| P5 | `GET /api/itdx/health` | 200 + both schema names. | PASS |
| P6 | `GET /api/itdx/situation-assessment` | HTTP 200 in ≤ 8s. Every `CHANNEL_KEYS` present. NLM-backed channels UNQUALIFIED while model unloaded. `p` null there. No hang. | **FAIL timeout** |
| P7 | `GET /api/itdx/task8` | 200. `seven_role.qualification=UNQUALIFIED` until Intention import is fixed. `execution=ADVISORY_ONLY`. `live_cop=false`. | **FAIL** (reports BOUND with ImportError) |
| P8 | Intention row | `error` null and `ok=true` **or** qualification UNQUALIFIED. | FAIL (error + BOUND) |
| P9 | `GET /api/myca/health` | 200. Dormant is allowed. Must not be used as persona p. | PASS (dormant honest) |
| P10 | `GET /voice/brain/health` | 200. Not a substitute for P7. | PASS as brain HTTP only |
| P11 | Website 3010 `/api/itdx/situation-assessment` | Owner session 200 **or** 401/403 — never 404 once M4 lands. Unauth 401. | **FAIL 404** |
| P12 | Website 3010 `/api/itdx/task8` or `/api/fusarium/itdx/task8` | Owner 200 with MAS payload **or** UNQUALIFIED + probes. Unauth 401. | 401 on fusarium path; 404 on `/api/itdx/task8` |
| P13 | 8765 bind (optional lab) | If `ITDX_*` pointed at 188, health probes return MAS JSON. Defaults-as-localhost stay UNAVAILABLE — that is PASS if labeled. | Defaults wrong ports |
| P14 | Earth-2 / physics | Unreachable ⇒ weather/physics `NOT_SUPPLIED`, not SCORED. | Earth-2 down; physics 502 — assessment never returned |
| P15 | No mock data | Grep ITDX/Fusarium consumer for hardcoded species / 0.73 / seven fake names. | NLM 0.85 placeholder is the live violation |
| P16 | pytest `tests/test_itdx_task8_api.py` | Unit gates stay. Add tests: deadlock-free assessment mock; BOUND forbidden when any role `error`. | Unit only; no live suite |

CI: these are **runtime** proofs against 188 + 3010. Unit tests alone are not M5.

---

## 8. Out of scope / honesty

- Official Army inject pack, FOUO PDF bytes, 1–5 rubric, fielded COP.  
- Sandbox 187 rebuild, Cloudflare purge, PR #299 merge, public GitHub packet.  
- Weka eval (ready, not run — see Sep 08/09 doc).  
- Awakening MYCA, loading NLM weights, or turning off skip-startup without an ops window.  
- Editing orchestrator / guardian / security / constitution / soul / identity.  
- Claiming CMMC compliant. **RJ is CFO, not COO.**  
- CUI in Cursor, git, website, or MAS logs.  
- Per-app fake agents for twins.

---

## 9. Recommended next execution order

1. **M2 deadlock + qualification** on the existing `itdx_api` / `itdx_task8_agent` (same PR/lane as `35796f25`).  
2. **P6 + P7 + P8** on 188 after one `systemctl restart mas-orchestrator`.  
3. **M4 BFF path unification** on `website-itdx-codex-v13` only.  
4. Intention module repair or honest UNQUALIFIED (M3).  
5. NLM load only with a real checkpoint (Morgan).  
6. 187 / merge only when Morgan says ship.

---

## Lessons (so the next agent does not mint another green badge)

- FormSpace recorded PASS ≠ MAS NLM ≠ seven MYCA agents.  
- OpenAPI listing a route ≠ the route returns. Self-HTTP on one worker hangs situation-assessment.  
- `seven_role.BOUND` with an ImportError is a fake badge — fix the predicate before the UI.  
- `confidence=0.85` in `NLMService` is mock data and must never become a channel `p`.  
- Website `/api/avani/status` and MAS `/api/avani/health` are different contracts; 404 is why AVANI “does not work” in Fusarium chrome.  
- 8765 defaults (`:8000` / `:8003` / localhost `:8001`) cannot see 188/189.  
- Hot-copy to 188 leaves `git_sha` lying. Say `hotpatch` or bump the running SHA.
