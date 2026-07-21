# BackgroundChecks.com + PreVeil MYCA Integration

**Date:** July 20, 2026  
**Status:** Deployed to MAS VM 192.168.0.188 (Jul 20, 2026) — live on orchestrator systemd service  
**Scope:** MAS-only compliance automation for Morgan Rockcoons and RJ Ricasata

## Security boundaries

- BackgroundChecks credentials exist only in gitignored local configuration. The provider token must never be committed, logged, placed in `NEXT_PUBLIC_*`, or included in requests to MYCA model providers.
- The read-only MYCA posture response is operational metadata, not CMMC evidence and not a claim that any control is implemented. Patch v1 (Jul 20) adds honest PreVeil onboarding blocks (CSM Adam Fernandez, order Jul 16, enclave not live, PE.3.10.6 not Met), Nick Faso confirmation pending, and optional `cmmc` summary from soc_ops when Postgres is configured.
- BackgroundChecks report details, PDFs, SSNs, dates of birth, addresses, and adverse-action functions are deliberately excluded. MAS returns only limited status metadata for explicitly allowlisted staff.
- A provider token was shared in chat during setup. Rotate it after integration if chat logs persist.

## Environment configuration

Set these in MAS `.credentials.local` only:

| Variable | Required | Purpose |
|---|---:|---|
| `BACKGROUNDCHECKS_API_TOKEN` | Yes | BackgroundChecks.com provider credential |
| `BACKGROUNDCHECKS_API_BASE_URL` | No | Provider base URL; defaults to `https://app.backgroundchecks.com/api` |
| `BACKGROUNDCHECKS_ALLOWED_EMPLOYEE_EMAILS` | Yes for status/order | Comma-separated real Morgan/RJ employee email allowlist |
| `BACKGROUNDCHECKS_ALLOWED_EMPLOYEE_IDS` | No | Optional stable internal IDs for operations configuration |
| `BACKGROUNDCHECKS_PROD_ORDERS_ALLOWED` | No | Defaults to `false`; must be explicitly `true` to create an allowed order |
| `MYCA_POSTURE_API_KEY` | Yes | Internal key required in the `X-API-Key` header |
| `PREVEIL_DRIVE_PATH` | No | PreVeil Drive mount path; only its configured/not-configured state is exposed |
| `BACKGROUNDCHECKS_LIVE_SMOKE` | No | Opt-in gate for the non-destructive account smoke test |

## MAS endpoints

All endpoints require `X-API-Key: <MYCA_POSTURE_API_KEY>`.

| Method | Path | Behavior |
|---|---|---|
| GET | `/api/compliance/background-checks` | Polls provider report metadata and returns only Morgan/RJ allowlisted subjects |
| POST | `/api/compliance/background-checks/order` | Creates an invitation only for an allowlisted subject and only when production ordering is explicitly enabled |
| GET | `/api/myca/posture` | Read-only operational posture for BackgroundChecks and the PreVeil Drive design |

The order request requires an allowed applicant email, a documented provider SKU (`HIRE1`, `HIRE2`, or `HIRE3`), and an explicit provider terms agreement. The default production-order state is disabled.

## Provider behavior

The integration uses the documented v1 API query authentication pattern and these endpoints:

- `GET /accounts` for an opt-in, non-destructive connectivity smoke check.
- `GET /reports/all` and `GET /reports/{report_key}/status` for polling.
- `POST /orders/new` for explicit, allowlisted production invitation/order creation.

The provider documentation reviewed July 20, 2026 does not expose an outbound webhook-registration API. Status updates therefore use polling; no webhook endpoint was invented.

## PreVeil Drive-filesystem design

MYCA consumes a metadata-only posture block:

```json
{
  "preveil": {
    "status": "configured | pending_onboarding",
    "design": "drive_fs",
    "read_only": true,
    "drive_path_configured": false,
    "pending_onboarding": true
  }
}
```

`PREVEIL_DRIVE_PATH` is never returned. The future Drive integration remains read-only and must not ingest or expose PreVeil CUI to MYCA or any commercial AI endpoint.

## Verification

**MAS VM deploy (Jul 20, 2026):** Integration files applied on `192.168.0.188` from commit `70298dc98` (branch `chore/license-notice-readme-sweep-jun25-2026`); orchestrator env synced to `/home/mycosoft/mycosoft/mas/.env`; `BACKGROUNDCHECKS_PROD_ORDERS_ALLOWED=true` on VM. Post-restart smoke: `/health` 200; `/api/compliance/background-checks` 401 without key / 200 with key; `/api/myca/posture` 401 without key / 200 with key.

Run focused mocked tests:

```powershell
poetry run pytest tests/test_backgroundchecks_client.py tests/test_backgroundchecks_compliance_api.py -q
```

The optional live smoke must only call the provider account endpoint and must never create an order:

```powershell
$env:BACKGROUNDCHECKS_LIVE_SMOKE = "1"
```
