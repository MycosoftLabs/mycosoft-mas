# DocuSign CMMC + MYCA Integration — JUL15 2026

**Date:** 2026-07-15  
**Status:** Integration scaffold live — JWT blocked until RSA private key path is set  
**Owner:** Cursor (systems) · Claude (DocuSign sign instructions / HTML→PDF workflow)  
**SAO:** Morgan Rockcoons · **CFO:** RJ Ricasata  

**Immutable:** Honesty gate · No false Met · CUI lives in PreVeil · No commercial AI processes CUI · Not “CMMC L2 certified.”

---

## Purpose

DocuSign is the system-wide signing path for:

- CMMC L2 signature-away controls (MA.L2-3.7.1–3.7.6, PS.L2-3.9.2)
- Broader 14-family policy SAO signatures
- MYCA / operator compliance workflows that need durable signed PDFs

Completed (or PreVeil-attested) PDFs land under `CODE/docs/cmmc_evidence/`. **Never** flip `soc_ops.compliance_controls` to `implemented` until signed evidence exists and SAO validates.

---

## Credentials (gitignored only)

| Variable | Where | Notes |
|----------|-------|-------|
| `DOCUSIGN_USER_ID` | MAS `.credentials.local`, website `.env.local` (server) | Impersonated user GUID |
| `DOCUSIGN_API_ACCOUNT_ID` | same | API Account ID |
| `DOCUSIGN_BASE_URL` | same | e.g. `https://na4.docusign.net` |
| `DOCUSIGN_INTEGRATION_KEY` | same | Integration key / client ID |
| `DOCUSIGN_APP_NAME` | same | App label (metadata) |
| `DOCUSIGN_RSA_PRIVATE_KEY_PATH` | same | **Required for JWT** — path to PEM |
| `DOCUSIGN_SECRET_KEY` | same | Optional Auth Code secret |
| `DOCUSIGN_AUTH_SERVER` | same | Default `https://account.docusign.com` |

**Never** put these in git-tracked files, docs, chats, or `NEXT_PUBLIC_*`.  
Placeholders (empty) live in `.credentials.local.example` and `.env.example`.

Optional agent-coordination env (`%USERPROFILE%\.mycosoft\agent-coordination.env.ps1`) holds non-secret defaults only.

---

## Auth: JWT Grant (recommended for MYCA / MAS)

1. In DocuSign **Apps and Keys**, open app `DOCUSIGN_APP_NAME`.
2. Generate / upload an **RSA keypair**. Keep the **private key PEM** only on disk (gitignored path).
3. Set `DOCUSIGN_RSA_PRIVATE_KEY_PATH` to that PEM path in `.credentials.local` and website `.env.local`.
4. Grant consent once (impersonation), e.g. open (replace integration key; do not commit the URL with secrets):

   `https://account.docusign.com/oauth/auth?response_type=code&scope=signature%20impersonation&client_id=<INTEGRATION_KEY>&redirect_uri=https://www.docusign.com`

5. Restart MAS orchestrator so env is loaded.
6. Verify: `GET http://192.168.0.188:8001/api/docusign/health` → `jwt_ready: true` (no secrets in body).

Until step 3–4 succeed, envelope create returns **503** with `"RSA key required"`.

Auth Code + `DOCUSIGN_SECRET_KEY` may be used later for interactive operator login; server automation uses JWT.

---

## What was built

| Piece | Path |
|-------|------|
| Client | `mycosoft_mas/integrations/docusign_client.py` |
| API router | `mycosoft_mas/core/routers/docusign_api.py` |
| Registration | `mycosoft_mas/core/myca_main.py` (`/api/docusign/*`) |
| Website BFF | `WEBSITE/website/app/api/docusign/route.ts` → proxies MAS |
| This doc | `docs/DOCUSIGN_CMMC_MYCA_INTEGRATION_JUL15_2026.md` |

### MAS endpoints

| Method | Path | Behavior |
|--------|------|----------|
| GET | `/api/docusign/health` | Configured? JWT ready? (no secrets) |
| GET | `/api/docusign/packs` | CMMC pack metadata |
| POST | `/api/docusign/envelopes` | Create envelope (optional `pack_id`) |
| POST | `/api/docusign/envelopes/cmmc` | Pack-scoped create (default `status=created`) |
| GET | `/api/docusign/envelopes/{id}` | Status |
| POST | `/api/docusign/webhooks/connect` | Connect → evidence path hint (**no soc_ops flip**) |

Website: `GET /api/docusign?action=health|packs|envelope&envelopeId=…`  
`POST /api/docusign` or `?action=cmmc` with same JSON body as MAS.

---

## CMMC packs

Source drafts (unsigned): `C:\Users\Owner1\Downloads\cmmc_l2_policies\`

| `pack_id` | Source | Signers | Evidence hint |
|-----------|--------|---------|---------------|
| `ma_maintenance` | `POLICY_MA_Maintenance.html` | Morgan + RJ | `docs/cmmc_evidence/ma/3.7.1-3.7.6_maintenance_policy_signed.pdf` |
| `ps_rj_access` | `RJ_Access_Agreement.html` | RJ | `docs/cmmc_evidence/ps/3.9.2_rj_access_agreement_signed.pdf` |
| `policy_family_batch` | `POLICY_*.html` (14 families) | Morgan (SAO) | `docs/cmmc_evidence/<family>/` |

**CUI note:** Draft HTML may show a CUI banner. Do not paste bodies into Cursor/Claude. Convert/sign via DocuSign; keep CUI-bearing signed copies in PreVeil.

Related flip prep: `CODE/docs/CMMC_L2_SIGNATURE_FLIP_READY_JUL15_2026.md`.

---

## How Claude should instruct DocuSign signing

1. Confirm RSA path + consent done (`/api/docusign/health` → `jwt_ready`).
2. Produce PDFs from the Downloads HTML **outside** commercial AI context if CUI-marked (operator export / print-to-PDF).
3. Base64 the PDF; call MAS `POST /api/docusign/envelopes/cmmc` with:
   - `pack_id`: `ma_maintenance` or `ps_rj_access`
   - `documents`: `[{ document_base64, name, file_extension: "pdf", document_id: "1" }]`
   - `signers`: correct emails/names for Morgan / RJ
   - `status`: `created` first (draft), then `sent` after SAO review
4. Track with `GET /api/docusign/envelopes/{id}`.
5. On `completed`: download signed PDF → evidence path (or PreVeil) → **stop**. Cursor runs soc_ops SQL only after SAO validation.
6. For the remaining 14 family policies, use `policy_family_batch` or one envelope per family; same evidence discipline.

---

## MYCA usage

MYCA agents may:

- Check `GET /api/docusign/health` before offering “send for signature”
- List packs via `/api/docusign/packs`
- Create draft envelopes for operator review
- Surface webhook evidence hints

MYCA must **not**:

- Auto-Met flip controls
- Put DocuSign secrets in prompts / Notion / public GitHub
- Process CUI document bodies through commercial LLM APIs

---

## Blocked on Morgan

1. Generate RSA keypair in DocuSign app; save private PEM to a secure local path.
2. Set `DOCUSIGN_RSA_PRIVATE_KEY_PATH` in `.credentials.local` (+ website `.env.local` if BFF creates envelopes).
3. Complete one-time JWT consent (impersonation) in browser.
4. Optionally configure DocuSign Connect → `https://<MAS>/api/docusign/webhooks/connect` (JSON).
5. Provide signer emails for Morgan / RJ if not already in DocuSign address book.

---

## Guardrails

- No hardcoded secrets in code or docs
- CUI RoB always applies
- Website marketing `/compliance` page unchanged (BFF only)
- Deploy freeze: prefer small focused commits; rebuild website only if BFF must ship to sandbox

---

## Related

- `CODE/docs/CMMC_L2_SIGNATURE_FLIP_READY_JUL15_2026.md`
- `CODE/docs/AI_AGENT_CUI_RULES_OF_BEHAVIOR_JUL15_2026.md`
- `docs/API_CATALOG_FEB04_2026.md` · `docs/SYSTEM_REGISTRY_FEB04_2026.md`
- Evidence roots: `CODE/docs/cmmc_evidence/ma/`, `…/ps/`
