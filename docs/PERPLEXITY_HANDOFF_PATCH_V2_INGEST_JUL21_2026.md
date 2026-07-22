# Perplexity Handoff Patch v2 Ingest — JUL21 2026

**Date:** 2026-07-21  
**Status:** Complete (ingest + MAS evidence spine scaffold; no PS.L2-3.9.1 Met flip until adjudicate run post-migration)  
**Agent:** Cursor  
**Source PDF:** `C:\Users\Owner1\Downloads\handoff_patch_v2_jul21_2026.pdf`  
**Canonical copy:** `MAS/mycosoft-mas/docs/PERPLEXITY_HANDOFF_PATCH_V2_INGEST_JUL21_2026.md`  
**CODE mirror:** `CODE/docs/PERPLEXITY_HANDOFF_PATCH_V2_INGEST_JUL21_2026.md`

---

## 1. Executive summary (5 bullets)

- **HR/screening human lane closed:** Morgan + RJ completed HireRight six-check packages Jul 21; peer adjudication memos signed (`MYC-ADJ-ROCKCOONS-2026-07-21`, `MYC-ADJ-RICASATA-2026-07-21`); Drive mirror live under folder `1JzHq6t3ceMp4s3OKA93BS7DtQMJCJau2`.
- **Cursor primary lane pivots:** Digitize paper trail into `soc_ops` (`ps_subject`, `ps_screening_event`, `ssp_evidence`) and route **all** control Met flips through `POST /api/security/evidence/emit` — no manual `soc_ops` edits.
- **PS.L2-3.9.1 flip rule unchanged in spirit:** Met only via `POST /api/security/ps/adjudicate` after PreVeil paths + Drive mirror refs validate; **not** flipped in this ingest session (migration must run on 189 first).
- **BC.com automation demoted:** `BGC_AUTOMATION_ENABLED=false` default; Nick Faso path bypassed; production BC.com orders blocked unless both automation flag and explicit prod-order env are true.
- **Largest remaining SPRS events:** PreVeil enclave activation bundle (36 controls) after both users provisioned; Batch E Wazuh (SI.L2-3.14.6); Batch A endpoint evidence — all blocked on Morgan/onboarding or ops capture.

---

## 2. Overrides vs Patch v1 (Jul 20)

| Topic | v1 (Jul 20) | v2 (Jul 21) |
|-------|-------------|-------------|
| Nick Faso / BC.com URL | Awaiting reply; prod orders gated on written confirmation | **Bypassed** — HireRight manual path used |
| Morgan/RJ BGC | Not ordered | **Complete** — reports + adjudication memos on file |
| PS.L2-3.9.1 | Not-Met; waiting on screening | Paper trail **done**; Cursor digitizes + emitter flip |
| BC.com API automation | Critical-path Day-1 | **Feature-flagged off** (`BGC_AUTOMATION_ENABLED=false`) |
| PreVeil | Ordered Jul 16, onboarding pending | Order **executed** ($4,780 Y1); onboarding in progress with Adam Fernandez |
| Primary Cursor queue | BGC polling + Nick gate | Evidence emitter + 48-hr punchlist (Batch A/E + enclave bundle) |
| UI | Security tab BGC subsection (Claude) | Same owner — now **Personnel Screening table** from `ps_screening_event` (provider-agnostic) |

**Unchanged from v1:** CUI stays in PreVeil only; no third-party AI on CUI; honesty gate at API layer; MYCA `/api/myca/posture` remains operational metadata not evidence; 100% self-perform (no Zeetachec).

---

## 3. Cross-read alignment (Jul 20–21 docs)

| Doc | Alignment with v2 |
|-----|-------------------|
| `PERPLEXITY_HANDOFF_PATCH_V1_INGEST_JUL20_2026.md` | Superseded for screening state; posture Nick-gate text replaced in MAS |
| `BACKGROUNDCHECKS_PREVEIL_MYCA_INTEGRATION_JUL20_2026.md` | MAS client still valid for future automation; prod orders now double-gated |
| `CURSOR_TO_CLAUDE_BGC_POSTURE_FRONTEND_HANDOFF_JUL21_2026.md` | Updated §8 with v2 endpoints + UI table spec |
| `MYCA_BACKGROUNDCHECKS_AUTOMATION_GUIDE_JUL21_2026.md` | Polling flows optional; automation demoted until flag on |
| `CMMC_COMPLIANCE_DATA_RESTORE_JUL21_2026.md` | soc_ops intact on 189; env restore unrelated to v2 schema |
| `CMMC_SOC_OPS_STATE_DURABILITY_JUL21_2026.md` | Durability guards compatible with emitter append-only tables |
| `CURSOR_BACKGROUNDCHECKS_PREVEIL_COMPLIANCE_HANDOFF_JUL17_2026.md` | PS.3.9.1 flip still requires favorable + SAO + filed — v2 adds emitter path |

**Contradiction resolved:** v1 said keep prod orders false until Nick; v2 says manual HireRight complete — MAS posture now reports `nick_faso_confirmation.status=bypassed` and defaults prod orders off via automation flag.

---

## 4. Ownership matrix

| Work item | Cursor | Claude | Morgan | Perplexity |
|-----------|--------|--------|--------|------------|
| Migration `031_personnel_screening_evidence_jul21_2026.sql` on MINDEX 189 | **Execute** | — | Approve apply on 189 | — |
| Evidence emitter + PS adjudicate APIs | **Done (code)** | — | Run adjudicate after migration | — |
| Security tab Personnel Screening table | — | **UI + BFF** | — | — |
| PreVeil enclave 36-control bundle | Capture after live | UI reflects | Onboarding call | SSP re-cut after |
| Batch A endpoint evidence | **Report + capture** | — | — | — |
| Batch E Wazuh SIEM | **Stand up / report** | — | — | — |
| IR tabletop | Endpoint **Done** | — | **Run exercise** | — |
| AT training records | Endpoint **Done** | — | RJ complete CDSE | — |
| Hydrated 110-control JSON (P0) | Drop into repo when delivered | — | — | **Deliver** |
| MYCA `/api/myca/posture` runtime | Design-time | — | — | — |

---

## 5. MAS engineering delivered this session

| Artifact | Path |
|----------|------|
| SQL migration + seed | `migrations/031_personnel_screening_evidence_jul21_2026.sql` |
| Evidence emitter core | `mycosoft_mas/compliance/evidence_emitter.py` |
| Security API router | `mycosoft_mas/core/routers/security_evidence_api.py` |
| Repository extensions | `mycosoft_mas/soc/repository.py` |
| Posture v2 block | `mycosoft_mas/core/routers/compliance_api.py` |
| Router registration | `mycosoft_mas/core/myca_main.py` |
| Unit tests | `tests/test_evidence_emitter.py` |

### New endpoints (MAS 188:8001, `X-API-Key: MYCA_POSTURE_API_KEY`)

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/security/ps/screening-events` | Personnel Screening table data (metadata only) |
| POST | `/api/security/evidence/emit` | Canonical control flip + `ssp_evidence` insert |
| POST | `/api/security/ps/adjudicate` | PS.L2-3.9.1 + 3.9.1 via screening row |
| POST | `/api/security/at/training-record` | AT.L2-3.2.x training evidence |
| POST | `/api/security/ir/tabletop-record` | IR.L2-3.6.3 tabletop evidence |

### Env (merge only — do not truncate `.env`)

| Variable | Default | Notes |
|----------|---------|-------|
| `BGC_AUTOMATION_ENABLED` | `false` | Patch v2 demotes BC.com automation |
| `BACKGROUNDCHECKS_PROD_ORDERS_ALLOWED` | ignored unless automation true | Existing VM `true` no longer opens orders alone |

---

## 6. Open actions (ordered)

### Cursor (next)

1. Apply migration **031** on MINDEX VM 189 (`soc_ops` schema).
2. Deploy MAS 188 with new router; smoke `GET /api/security/ps/screening-events`.
3. After Morgan confirms PreVeil file copy matches seeded paths, run `POST /api/security/ps/adjudicate` for both event UUIDs — **only then** PS.L2-3.9.1 goes Met.
4. Report Batch A + Batch E status from Jul-15 punchlist (evidence files on laptops / Wazuh on 188).

### Morgan

1. Complete PreVeil onboarding (2 users live, encrypted email + Drive drop test).
2. Copy BGC PDFs + adjudication memos into PreVeil paths seeded in migration (or update paths in DB).
3. Ping Cursor to run §2.3 enclave-activation bundle **after** live tenant screenshot.
4. RJ: complete CDSE Cyber Awareness + Insider Threat (Morgan certs already filed Jul 20).
5. Schedule 90-min IR tabletop with RJ.

### Claude

1. Wire Security tab Personnel Screening subsection per updated handoff §8.
2. BFF proxies for new `/api/security/*` routes (server-side key only).

### Perplexity

1. P0 hydrated 110-control JSON (~462 KB, MD5 abca7ab1…).
2. Re-cut SSP narrative after PreVeil enclave bundle fires.

---

## 7. Blockers

| Blocker | Owner |
|---------|-------|
| Migration 031 not yet applied on 189 | Cursor ops |
| PreVeil files not confirmed at `/CUI/Personnel-Screening/...` paths | Morgan + Adam Fernandez |
| PS.L2-3.9.1 Met flip intentionally deferred until adjudicate POST succeeds | Honesty gate |
| Enclave 36-control bundle blocked until 2 live PreVeil users | Morgan onboarding |
| Wazuh / Batch A evidence unknown | Cursor Day-1 report |

---

## 8. Drive mirror reference (metadata only — not CUI in git)

| Artifact | Drive file ID |
|----------|---------------|
| HR folder 2026 | `1JzHq6t3ceMp4s3OKA93BS7DtQMJCJau2` |
| Rockcoons BGC PDF | `1DQqQ_9oem2tirjZoi5g9PBl7Q4_tQSPz` |
| Ricasata BGC PDF | `1FrI9D4pdXvdtChEugCMCn7709Dee74Hn` |
| Rockcoons adjudication memo | `1C4qrjB-YVeHw5DrDmdwtGqFaTSa8-np5` |
| Ricasata adjudication memo | `1t6VaX6Oj011Mf5ovO65sv7sWXzYGtXOr` |

Seeded event UUIDs: `22222222-2222-4222-8222-222222222201` (Morgan), `22222222-2222-4222-8222-222222222202` (RJ).

---

## 9. Verification

```powershell
# After migration + MAS deploy (key from .credentials.local — never commit)
$h = @{ "X-API-Key" = $env:MYCA_POSTURE_API_KEY }
Invoke-RestMethod -Uri "http://192.168.0.188:8001/api/security/ps/screening-events" -Headers $h
Invoke-RestMethod -Uri "http://192.168.0.188:8001/api/myca/posture" -Headers $h
poetry run pytest tests/test_evidence_emitter.py tests/test_backgroundchecks_compliance_api.py -q
```

**Do not** run adjudicate until Morgan confirms PreVeil mirror paths are authoritative.

---

## Related

- Patch v1: `docs/PERPLEXITY_HANDOFF_PATCH_V1_INGEST_JUL20_2026.md`
- Claude handoff: `docs/CURSOR_TO_CLAUDE_BGC_POSTURE_FRONTEND_HANDOFF_JUL21_2026.md` (§8 v2 addendum)
- Jul-15 punchlist: `uploaded_attachments/.../CURSOR_CMMC_48HR_TECHNICAL_PUNCHLIST_JUL15_2026.md`
