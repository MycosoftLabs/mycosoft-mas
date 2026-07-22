# CMMC Migration 031 + Patch v2 Deploy — JUL21 2026

**Date:** 2026-07-21  
**Status:** Complete (ops); no soc_ops Met flips  
**Agent:** infrastructure-ops (Cursor)  
**Related:** `CMMC_L2_CONTROLS_HYDRATED_README_INGEST_JUL21_2026.md`, `PERPLEXITY_HANDOFF_PATCH_V2_INGEST_JUL21_2026.md`

---

## Summary

| Item | Result |
|------|--------|
| Migration 031 on MINDEX 189 | **Y** |
| Patch v2 deploy on MAS 188 | **Y** (SCP hotfix; not yet on `origin/main`) |
| `/api/compliance/score` non-zero | **Y** — 22.7% (50 implemented / 220 rows) |
| PS Met flip | **No** (honesty gate; sibling filing to `cmmc_evidence/ps/`) |

---

## 1. Migration 031 (MINDEX VM 189)

**File:** `migrations/031_personnel_screening_evidence_jul21_2026.sql`  
**Method:** `docker exec mindex-postgres psql -U mycosoft -d mindex -v ON_ERROR_STOP=1` (idempotent `IF NOT EXISTS` / `ON CONFLICT DO NOTHING`)  
**Credentials:** `MINDEX_VM_USER=root`, `MINDEX_VM_PASSWORD` from `.credentials.local`  
**Data:** No wipe; merge-only apply.

**Verified after apply:**

| Check | Value |
|-------|-------|
| `soc_ops.ps_subject` | created |
| `soc_ops.ps_screening_event` | created; **2 rows** seeded |
| `soc_ops.ssp_evidence` | created |
| `soc_ops.compliance_audit_log` | created |
| Evidence tables count | **4/4** |

---

## 2. Patch v2 (MAS VM 188)

**Finding:** PR #119 merged BackgroundChecks/MYCA posture to `origin/main`, but Patch v2 router files were **local untracked** (never pushed):

- `mycosoft_mas/compliance/evidence_emitter.py`
- `mycosoft_mas/core/routers/security_evidence_api.py`
- Modified: `myca_main.py`, `compliance_api.py`, `soc/repository.py`

**Deploy method:**

1. `git fetch && git reset --hard origin/main` on 188 (already at `09ed3554` merge #119).
2. SFTP upload of Patch v2 files from dev workstation to `/home/mycosoft/mycosoft/mas/`.
3. Merge-only `.env`: set `BGC_AUTOMATION_ENABLED=false`; preserved `DATABASE_URL` + `MINDEX_DATABASE_URL`.
4. `systemctl restart mas-orchestrator` (systemd + `/etc/mycosoft/mas-compliance.env` drop-in intact).

**Follow-up:** Commit and push Patch v2 files to `main` so future pulls do not regress.

---

## 3. Route status (2026-07-22 ~07:49 UTC)

| Endpoint | HTTP | Notes |
|----------|------|-------|
| `GET /api/security/ps/screening-events` | **401** without key; **200** with `X-API-Key` | Returns **2** screening events |
| `GET /api/compliance/score` | **200** | `implementation_percent`: **22.7** |
| `GET /api/compliance/health` | **200** | `postgres_configured`: true |
| `GET /health` | **200** | Orchestrator up (degraded components unrelated) |

No Met flips performed. PS adjudicate not invoked (PreVeil confirmation deferred per T-109).

---

## 4. Ops scripts (MAS repo, one-shot)

- `scripts/_ops_migration031_patchv2_jul21_2026.py`
- `scripts/_scp_patchv2_mas188_jul21_2026.py`
- `scripts/_restart_mas188_sudo.py`

---

## Related

- Patch v2 ingest: `docs/PERPLEXITY_HANDOFF_PATCH_V2_INGEST_JUL21_2026.md`
- Durability: `docs/CMMC_SOC_OPS_STATE_DURABILITY_JUL21_2026.md`
- T-109 ingest: `docs/CMMC_L2_CONTROLS_HYDRATED_README_INGEST_JUL21_2026.md`
