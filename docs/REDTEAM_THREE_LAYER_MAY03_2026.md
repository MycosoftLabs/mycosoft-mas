# Red team three-layer SOC (May 03, 2026)

**Date:** May 3, 2026  
**Status:** Complete  

## Layers

| Layer | Where | Module | Behavior |
|-------|-------|--------|----------|
| **L1** | MAS (prod-safe) | Red team L1 scheduler in MAS | Continuous SAFE checks (TLS, ports, secrets/CVE helpers per implementation). |
| **L2** | Scoped sandbox | `mycosoft_mas/redteam/layer2_scoped.py` | `nmap -sn` against `SOC_REDTEAM_L2_TARGET` (default `192.168.0.187`) when `nmap` exists on Linux; otherwise informational “skipped” finding (no fake scan). |
| **L3** | Sandbox AI | `mycosoft_mas/redteam/layer3_ai.py` | Claude defensive plan for `SOC_REDTEAM_L3_SCOPE`; no exploit execution; interval `SOC_REDTEAM_L3_INTERVAL_SEC` (default 6h). |

## Persistence

- Tables: `soc_ops.redteam_runs`, `soc_ops.redteam_findings`.  
- **MAS API:** `GET /api/redteam/soc-runs`, `GET /api/redteam/soc-findings?run_id=&limit=`.  
- **Website:** `GET /api/security/redteam?action=soc-runs|soc-findings` (admin-only); **SOC (L1–L3)** tab on `/security/redteam`.

## Control / kill switches

- `SOC_REDTEAM_L2=0` — disable L2 background loop.  
- `SOC_REDTEAM_L3=0` — disable L3 background loop.  
- Guardian: `mycosoft_mas/security/redteam_guardian_gate.py` for higher-risk **simulation** types on credential/phishing/pivot endpoints.

## Follow-up

- Pre-bake **`mycosoft/redteam-tools`** image on sandbox with nuclei, trivy, gitleaks, ZAP baseline for richer L2 evidence.
