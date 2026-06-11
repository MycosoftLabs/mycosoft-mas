# Security Hardening Deployed + SINE Backend Verification (June 11, 2026)

**Date:** June 11, 2026
**Status:** Security fixes — Complete & deployed. SINE backend — schema provisioned; model artifact still required (honest `model_unavailable`).
**Audit source:** `docs/SECURITY_AUDIT_ALL_SYSTEMS_JUN09_2026.md`
**SINE handoff:** `WEBSITE/website/docs/codex-handoffs/SINE_CURSOR_BACKEND_FULL_FUNCTIONAL_HANDOFF_JUN08_2026.md`

---

## Part 1 — Security hardening (from JUN09 audit) — DEPLOYED

### What was fixed and shipped

| Finding | Fix | Repo / commit |
|---|---|---|
| M-1/M-4/M-5/M-6/M-9 — unauthenticated MAS infra routes | New `mycosoft_mas/core/internal_auth.py` `require_internal_token` (env `MAS_INTERNAL_TOKEN`, header `X-MAS-Internal-Token`, **fail-closed in production**). Applied to `deploy_api` (router-level), `firmware_flash_api` (flash), all 13 `autonomous_api` POSTs, `coding_api` (request/approve/cancel/halt/scan), `agent_runner_api` (start/stop/wisdom/notify). | mycosoft-mas `0936fc40c` |
| M-2 — unauthenticated firmware flash | `POST /{device_id}/firmware/flash` now gated. | mycosoft-mas `0936fc40c` |
| M-3 — revoked password default | `scripts/recreate_mas_container.py` env-only, raises if unset. | mycosoft-mas `0936fc40c` |
| M-7 — MycoBrain 8003 fail-open auth | `verify_api_key` now requires `MYCOBRAIN_API_KEY` when set; no silent no-op. | mycosoft-mas `0936fc40c` |
| M-8 — tracked MQTT creds | `_jetson_mqtt.env` untracked + gitignored. **Rotate the MQTT cred (Morgan).** | mycosoft-mas `0936fc40c` |
| X-1/X-3 — MINDEX fail-open auth | `require_api_key` fail-closed in production; also now accepts `X-Internal-Token` so internal callers keep working. | mindex `918b9d1`, `a1183a3` |
| X-2 — revoked DB password in 5 scripts | Replaced literals with `{MINDEX_DB_PASSWORD}` placeholders. | mindex `918b9d1` |
| P-1 — 0.0.0.0 infra binds | Postgres/Redis/Qdrant bound to `127.0.0.1` in platform-infra compose. | CODE root `d66a0d3` (local) |

### Deploy + verification (live)

- **MAS 188:** `MAS_INTERNAL_TOKEN` generated, written to VM `.env` and `.credentials.local`; `mas-orchestrator` restarted on `feature/com4-hyphae-ota-local-may29-2026`.
  - `POST /api/deploy/trigger` **without** token → **HTTP 401** (was 200). ✅
  - `GET /api/deploy/status/none` **with** token → **HTTP 404** (auth passed). ✅
- **MINDEX 189:** `MINDEX_ENV=production` set, `mindex-api` rebuilt/restarted (`a1183a3`).
  - `POST /api/mindex/nlm/classify/acoustic` **without** token → **HTTP 401** (was open). ✅
  - same **with** `X-Internal-Token` → **HTTP 200**. ✅
  - `GET /api/mindex/health` → `db: ok`. ✅
- Deploy script (idempotent, re-runnable): `MAS/mycosoft-mas/scripts/deploy_security_hardening_jun11_2026.py`.

### Still requires Morgan
- Rotate the MQTT credential that was in `_jetson_mqtt.env`.
- Decide on git-history scrub for the revoked-password literals (same procedure as March 2026).
- Set `MAS_INTERNAL_TOKEN` in website BFF env + n8n callers that hit 188 mutating routes (server-side only, never `NEXT_PUBLIC_*`).

---

## Part 2 — SINE backend verification (vs JUN08 handoff)

### Honest current state on VM 189

| Check | Result |
|---|---|
| MINDEX health | **200**, `db: ok` |
| Acoustic blobs (NAS) | ESC-50 WAVs present under `/mnt/nas/mindex/Library/acoustic/esc50/` |
| SINE service files | All present (`mindex_api/services/sine_acoustic/*`) and deployed |
| **SINE evidence/registry schema** | **NOW PROVISIONED (this session).** Applied `20260606_sine_model_registry` + `20260606_sine_analysis_evidence`. 6 `sine.*` tables exist: `model_artifact, prototype, model_output, prototype_match, fusion_evidence, sound_transcript`. |
| ESC-50 metadata CSV | **Reconstructed this session** at `/mnt/nas/mindex/Library/acoustic/esc50/meta/esc50.csv` (2000 rows, labels parsed from filenames `fold-clip-take-TARGET.wav`). |
| `GET /sine/models` | `model_registry_empty` (honest — table present, no rows) |
| `GET /sine/prototypes` | `prototype_catalog_empty` (honest — table present, no rows) |
| **Honesty contract** | **INTACT** — endpoints correctly report `model_unavailable`; no fake labels. |

### What remains for "fully functional" (the JUN08 completion gate)

These are the real blockers, unchanged by the schema work, and they are a **dedicated ML task**:

1. **`torch` / `onnxruntime` not installed in `mindex-api` container** (`soundfile` is). A runtime pip install will not survive a container rebuild — this needs a **Dockerfile/requirements change** in the MINDEX repo, then rebuild.
2. **No trained model artifact** — must run `scripts/train_sine_esc50_p0.py` on the ESC-50 NAS audio (CPU-only on the VM; will be slow), produce the package under `/mnt/nas/mindex/models/acoustic/sine-esc50-cnn-p0-v1/`.
3. **Register + smoke + mark-loaded + prototypes** via the existing strict verifier scripts (`verify_sine_model_artifact_package.py`, `smoke_sine_model_artifact_inference.py`, `build_sine_prototype_catalog.py`).
4. **E2E gate** `verify_sine_real_ai_e2e.py` must return `status: ready`.

### Recommendation

The schema + metadata gap is closed. The model-training step is heavy (torch in-container + CPU training + strict package gates) and should be a **scoped, confirmed run** — not started silently — because:
- it needs a MINDEX Dockerfile change (torch CPU wheels) to persist, and
- a CPU training run on the MINDEX VM could be long and resource-heavy on a production DB host.

**Decision needed from Morgan:** train the P0 ESC-50 model (a) on the MINDEX VM CPU, (b) on a GPU Legion then ship the artifact to NAS, or (c) defer. The frontend is correctly honest in the meantime (`frontend_ready_backend_pending`).

---

## Files changed this session

**mycosoft-mas:** `mycosoft_mas/core/internal_auth.py` (new), `core/routers/{deploy_api,firmware_flash_api,autonomous_api,coding_api,agent_runner_api}.py`, `services/mycobrain/mycobrain_service_standalone.py`, `scripts/recreate_mas_container.py`, `scripts/deploy_security_hardening_jun11_2026.py` (new), `.gitignore`, removed `_jetson_mqtt.env`, `docs/SECURITY_AUDIT_ALL_SYSTEMS_JUN09_2026.md`, `docs/codex-handoffs/SECURITY_AUDIT_BACKEND_CODEX_HANDOFF_JUN09_2026.md`.

**mindex:** `mindex_api/dependencies.py`, `scripts/_{deploy_mindex_v2,fix_mindex,full_fix,kill_and_restart,restart_mindex_fixed}.py`. VM-side: 2 SINE migrations applied + ESC-50 meta csv built (no repo change).

**CODE root:** `platform-infra/docker-compose.yml` (local commit `d66a0d3`).
