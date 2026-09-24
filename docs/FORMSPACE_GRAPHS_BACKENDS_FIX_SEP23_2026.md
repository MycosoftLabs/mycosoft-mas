# FormSpace Graphs + Tool Backends Fix — September 23, 2026

**Date:** September 23, 2026  
**Status:** Complete (graphs + tool backends wired)  
**Related:** `FORMSPACE_NLM_FULL_BUILD_PLAN_SEP23_2026.md`, `FORMSPACE_FULL_APP_COMPLETE_SEP23_2026.md`  
**Constraint:** No nginx cutover on 187

---

## Root cause (graphs)

1. Website BFF `POST /api/formspace/graph` **proxied only** to MAS `192.168.0.188:8001/api/formspace/graph`.
2. That route **does not exist on MAS yet** (404 / timeout).
3. BFF returned **404** to the client → Graphs tab failed.
4. Atlas/demo worked only because of catalog fallback; graph/experiment had none.

---

## Existing code found (reused)

| Asset | Location | Use |
|-------|----------|-----|
| **Native tied-A SSM** | `MAS/.../nlm/formspace/native_ssm.py` | Ported to `lib/formspace/native-ssm.ts` for BFF graphs/experiments |
| **FormSpace Stage B engine** | `MAS/.../nlm/formspace/{atlas,dynamics,graphing,engine}.py` | Already built; also mounted under live `/api/nlm/formspace/*` |
| **Mamba / Selective SSM** | `MAS/NLM/nlm/model/ssm_blocks.py` | Architecture reference (scientific NLM trunk, not chat) |
| **Forecast ledger + observations** | `formspace/forecast_ledger.py`, `observation_pipeline.py`, `/api/nlm/observations` | Evidence / causal contracts |
| **MINDEX evidence** | `mindex/.../sine_acoustic/evidence_builder.py`, `persisted_evidence.py`, mica GPU bridge | Acoustic/Merkle evidence patterns |
| **MAS 6-layer memory** | `/api/memory/remember`, `/api/memory/recall` | Wired into FormSpace Memory BFF |
| **Catalog chart IDs** | `lib/nlm/canonical-seeds.ts` `formspace_chart_ids` | Aligned demo fixtures |

GitHub `gh search` under MycosoftLabs returned no extra public hits this session; local repos were the source of truth.

---

## What was wired

### Website (works now on localhost:3010)

| Tool | Backend |
|------|---------|
| **Graphs** | Local FormSpace engine (`nativeScan`) + catalog fixtures; optional MAS when `FORMSPACE_PREFER_MAS=1` |
| **Experiments** | Same native SSM recovery trial |
| **Evidence** | Local evidence log after graph/experiment (+ MAS when present) |
| **Memory** | Local store + MAS `/api/memory/remember|recall` (6-layer) when reachable |
| **Atlas/Demo** | Canonical catalog (unchanged) |

Files: `lib/formspace/{native-ssm,engine,server}.ts`, `app/api/formspace/{graph,experiment,evidence,memory,health}/route.ts`

### MAS (code ready; VM redeploy still open)

- Dedicated `/api/formspace/*` router (prior pass)
- **Also** mounted on **live** NLM router: `/api/nlm/formspace/{health,demo,graph,experiment,evidence}` so a normal NLM/orchestrator redeploy exposes FormSpace without a new router name

---

## Graph verify steps

1. Open `http://localhost:3010/ai/formspace`
2. Atlas → select **FCI bioelectric atlas** (`fs-fci-demo-v1`)
3. Click **Replay fixture graph** or Graphs → **Compute graph**
4. Expect sparkline + `origin=CATALOG_FIXTURE` · `ssm=native_tied_A_rank1` · `local engine`
5. API check:
   ```powershell
   Invoke-RestMethod -Method POST -Uri http://localhost:3010/api/formspace/graph `
     -ContentType application/json `
     -Body '{"chart_id":"fs-fci-demo-v1","use_demo_fixture":true}'
   ```
   Expect `ok: true`, `points.length >= 8`, `p: null`, `engine: website-formspace-local`
6. Experiments → **Run recovery trial** → baseline + perturbed sparklines
7. Evidence tab should list graph/experiment rows after runs

---

## Still open

- Redeploy MAS 188 so `/api/nlm/formspace/*` (or `/api/formspace/*`) is live (SSH key auth blocked this session)
- Live measured series from devices (empty until real observations)
- MINDEX Merkle roots on every FormSpace artifact (P2 chain)
- No Sandbox/nginx cutover (per freeze)
