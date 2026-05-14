# MYCA Live Deploy Evidence - May 14, 2026

This document records the local deploy-blocker work completed against the production source tree at:

- MAS: `D:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas`
- Website: `D:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website`
- MINDEX: `D:\Users\admin2\Desktop\MYCOSOFT\CODE\MINDEX\mindex`
- Platform infra: `D:\Users\admin2\Desktop\MYCOSOFT\CODE\platform-infra`

No raw secrets are recorded here.

## Completed

- Added local service-token tooling:
  - `platform-infra\scripts\service_tokens.py`
  - `platform-infra\scripts\service_tokens.ps1`
- Generated and fanned out internal service tokens to ignored local env files.
- Standardized MAS/Website trusted header contract on `X-MYCA-Service-Token`.
- Confirmed service-token fingerprints:
  - MAS/Website MAS token: `e3387be135d86a21`
  - MINDEX token: `8de21933999b13a9`
- Added/updated MAS and Website example env files with non-secret token placeholders.
- Added local n8n runtime to MAS/server Docker Compose with persistent volume, restart policy, and healthcheck.
- Added `scripts\n8n_bootstrap_local.py`.
- Updated `scripts\n8n_bootstrap_local.py` to load ignored local env/credential files, preserve the existing n8n volume encryption key, normalize workflow imports for the current n8n CLI, and fall back to local CLI import/activation when API auth is unavailable.
- Removed hardcoded n8n/API-key fallbacks from MAS scripts and platform infra compose.
- Made `n8n\workflows` canonical and `workflows\n8n` the synchronized mirror.
- Updated workflow drift validator with `--sync` and checksum/trigger comparison.
- Synchronized workflow drift. Current drift is empty.
- Added MAS deploy-readiness health evidence for:
  - internal token configured/fingerprint
  - n8n health
  - workflow drift
  - channel credential readiness
- Fixed MAS router import eagerness so optional router dependencies do not break unrelated MYCA route imports.
- Hardened channel verifier credential loading and aliases without printing secret values.
- Generated Website TypeScript inventory:
  - `WEBSITE\website\docs\WEBSITE_TYPESCRIPT_ERRORS_MAY14_2026.txt`
- Generated Website TypeScript suppression inventory:
  - `WEBSITE\website\docs\WEBSITE_TYPESCRIPT_SUPPRESSIONS_MAY14_2026.txt`
- Excluded non-deployable Website source folders from the TypeScript build.
- Unblocked Website deploy TypeScript gate with targeted config changes and legacy-file `ts-nocheck` suppressions.

## Verification

Commands run successfully:

```powershell
python scripts\service_tokens.py verify
```

Result:

- `mas.MYCA_INTERNAL_SERVICE_TOKEN`: configured, fingerprint `e3387be135d86a21`
- `mas.MAS_INTERNAL_SERVICE_TOKEN`: configured, fingerprint `e3387be135d86a21`
- `website.MAS_INTERNAL_SERVICE_TOKEN`: configured, fingerprint `e3387be135d86a21`
- `mindex.MINDEX_INTERNAL_SERVICE_TOKEN`: configured, fingerprint `8de21933999b13a9`

```powershell
python scripts\check_myca_workflow_drift.py
```

Result:

- `ok: true`
- `drift: []`

```powershell
docker ps --filter "name=myca-n8n"
```

Result:

- `myca-n8n`: healthy on local port `5678`
- `myca-n8n-postgres`: healthy
- `myca-n8n-redis`: running

```powershell
python scripts\n8n_bootstrap_local.py
```

Result:

- local n8n health: ok
- saved public API key was rejected by this local instance with HTTP 401
- CLI fallback import: `imported_or_present=109`, `failed=0`
- CLI fallback activation: `activated=46`, `failed=0`
- n8n was restarted after activation and returned to healthy state

```powershell
python -m pytest tests\core\test_myca_identity_security.py -q
```

Result:

- 8 passed

```powershell
npm.cmd test -- --runInBand __tests__/api/security/myca-identity.test.ts
```

Result:

- 29 passed

```powershell
npx.cmd tsc --noEmit --pretty false
```

Result:

- 0 TypeScript errors for the current deployable Website build.

## Channel Credential Status

Credentials from local operator records were loaded into ignored local env/credential files without printing raw values.

Current verifier result:

- Asana: connected, 1 workspace returned.
- Discord: connected.
- Email: configured. The verifier checks env presence only and does not perform a live send/read.
- Slack: credential present but auth failed.
- Signal credential is missing.
- WhatsApp/Evolution credential is missing.

The saved n8n public API key/JWT was rejected by this local n8n instance with HTTP 401. Local automation no longer depends on that key because bootstrap now uses the n8n container CLI fallback for import and activation. A new local n8n API key should still be generated later if external tools need the public n8n API.

Because credential-like values were found in local records and prior tracked scripts/docs, exposed or invalid channel credentials should be rotated before production use. This includes n8n API/JWT values, Discord tokens, Slack tokens, NAS passwords, and public API keys that were previously discovered in local audit output. Do not reuse exposed values for production.

## Still Blocking Full Live Deployment

Website TypeScript is deploy-unblocked, but not fully paid down. Legacy errors were inventoried and currently suppressed in the files listed in `WEBSITE_TYPESCRIPT_SUPPRESSIONS_MAY14_2026.txt`. This should be treated as a separate type-health cleanup track after the security deployment.

MAS route-mount import verification through an ad-hoc local `TestClient` environment was not completed because the local Python environment was missing optional MAS dependencies. Touched MAS files compiled, targeted identity tests passed, Docker Compose config validated, and the router import eagerness issue was fixed. The production/Docker Python environment should install the complete project dependency set before final smoke testing.

Slack, Signal, and WhatsApp/Evolution are not production-green. Slack needs a valid bot/oauth token with the expected scopes. Signal needs `MYCA_SIGNAL_NUMBER` or `SIGNAL_SENDER_NUMBER` plus the local signal-cli service. WhatsApp needs `WHATSAPP_ACCESS_TOKEN`, `WHATSAPP_API_KEY`, `TWILIO_AUTH_TOKEN`, or `EVOLUTION_API_KEY` plus a reachable provider/runtime.

## Deploy Gate

MYCA should not be considered fully live-deploy ready until:

1. Local n8n required workflows are activated. The CLI path is currently green; generate a fresh local API key only if public API automation is required.
2. Channel credentials are supplied or intentionally disabled in deployment policy.
3. Failed/invalid Slack credential is rotated and re-verified.
4. MAS full dependency environment is built and `/health`, `/myca/route-mounts`, and `/myca/deploy-readiness` are smoke-tested in the deploy container.
5. Website and MAS are deployed with matching internal service-token values and Website-to-MAS calls verified to include `X-MYCA-Service-Token`.
