# Evidence Register API (MAS) — Jul 22, 2026

**Status:** Implemented  
**Endpoint:** `GET /api/security/evidence-register`  
**Host:** MAS orchestrator `http://192.168.0.188:8001`  
**Auth:** `X-API-Key: $MYCA_POSTURE_API_KEY` (same as Patch v2 security/posture routes)

## Purpose

Expose **metadata only** from `CODE/docs/cmmc_evidence/REGISTER.md` (or `REGISTER.json` sidecar) for the Security tab evidence table. Never returns PDF bodies, PreVeil file contents, or other artifact bytes.

## Response shape

```json
{
  "source": "REGISTER.md",
  "register_path": "/path/to/REGISTER.md",
  "count": 25,
  "entries": [
    {
      "id": "EV-PS-001",
      "controls": ["PS.L2-3.9.2", "3.9.2"],
      "artifact_path": "docs/cmmc_evidence/ps/PS_L2-3.9.2_RJ_Access_Agreement_SIGNED_JUL2026.pdf",
      "artifact_name": "PS_L2-3.9.2_RJ_Access_Agreement_SIGNED_JUL2026.pdf",
      "sha256": "b2a49cec9d291eade0737baa5ba96d6fc9777cb3406b99174884290eab0dc435",
      "signer": "Raljoseph Ricasata (RJ Ricasata, CFO)",
      "storage_tier": "internal_repo",
      "classification": "UNCLASSIFIED",
      "docusign_envelope": "AC00FC6C-EDA2-84FE-82C7-391A5236C1D9"
    }
  ]
}
```

### `storage_tier` enum

| Value | Meaning |
|-------|---------|
| `preveil` | PreVeil enclave / `/CUI/` path |
| `internal_repo` | Internal CODE tree (`docs/cmmc_evidence/…`) |
| `google_drive` | Google Drive file id / path |
| `public_repo` | Public git repo (never CUI) |

## Configuration (MAS VM)

Set on MAS `.env` (merge-only — do not truncate):

```env
CMMC_EVIDENCE_REGISTER_PATH=/opt/mycosoft/CODE/docs/cmmc_evidence/REGISTER.md
# optional override for JSON sidecar (preferred when present):
# CMMC_EVIDENCE_REGISTER_JSON=/opt/mycosoft/CODE/docs/cmmc_evidence/REGISTER.json
```

If `REGISTER.json` exists beside the markdown register, the API prefers the JSON sidecar.

## Frontend wiring (Claude)

1. Website Security tab: proxy `GET /api/security/evidence-register` via existing MAS proxy pattern with `X-API-Key` from server env.
2. Render table columns: id, controls, artifact_name, sha256 (truncated), signer, storage_tier, classification, docusign_envelope.
3. Do **not** fetch artifact paths as downloadable URLs from this endpoint — metadata pointers only.

## Verification

```bash
# 401 without key
curl -s -o /dev/null -w "%{http_code}" http://192.168.0.188:8001/api/security/evidence-register

# 200 with key
curl -s -H "X-API-Key: $MYCA_POSTURE_API_KEY" http://192.168.0.188:8001/api/security/evidence-register | jq '.count,.entries[0].id'
```

## Related

- Patch v2 emitter: `mycosoft_mas/core/routers/security_evidence_api.py`
- Register source: `CODE/docs/cmmc_evidence/REGISTER.md`
- PS.L2-3.9.2 flip: `doc:access-agreement#EV-PS-001` via `scripts/_cmmc_ps_392_flip_jul22_2026.py`
