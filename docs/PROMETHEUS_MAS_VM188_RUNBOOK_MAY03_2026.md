# Prometheus on MAS VM 188 — Runbook (May 3, 2026)

**Date:** May 3, 2026  
**Status:** Operational reference  
**VM:** MAS `192.168.0.188`  
**Expected port:** **9090** (host publish in repo compose: `9090:9090`)

---

## Symptoms

- From LAN/dev PC: `http://192.168.0.188:9090/-/healthy` **times out** (seen May 2–3, 2026).
- MAS orchestrator (**8001**), n8n (**5678**) on same host can still be healthy.

---

## Diagnose (on VM after SSH)

Use `$env:VM_PASSWORD` / `.credentials.local` per project rules; do not paste passwords into docs.

```bash
ssh mycosoft@192.168.0.188
docker ps -a --format '{{.Names}}\t{{.Status}}\t{{.Ports}}' | grep -i prom
curl -sS -o /dev/null -w '%{http_code}\n' http://127.0.0.1:9090/-/healthy
ss -tlnp | grep 9090 || true
```

**Local repo helper** — password resolution order: `VM_PASSWORD` / `VM_SSH_PASSWORD` env → `MYCO_SOFT_CREDENTIALS_FILE` path → `mycosoft-mas/.credentials.local`.

```powershell
cd C:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas
# External PowerShell (recommended): gitignored file visible here.
python scripts/diagnose_prometheus_mas188.py
```

**Cursor integrated terminal / MCP SSH:** If `.credentials.local` is hidden from the sandbox, set `VM_PASSWORD` on the MCP server process or `MYCO_SOFT_CREDENTIALS_FILE` to an absolute path the process can read. The Mycosoft SSH MCP (`mycosoft_mas.mcp.ssh_server`) tries SSH keys first, then falls back to that password (restart MCP after updating code).

**Full remediation (compose + UFW):** `python scripts/remediate_prometheus_mas188.py` — starts stopped Prometheus containers, runs `docker compose up -d prometheus` under `~/mycosoft/mas` if localhost **9090** is still down, then opens UFW for **192.168.0.0/24** when localhost health is **200**.

---

## Remediation branches

| Observation | Action |
|---------------|--------|
| No Prometheus container | Start stack from canonical compose on 188 (often under `~/mycosoft/` or Docker project used for MAS). Align image/labels with repo root `docker-compose.yml` Prometheus service. |
| Container exits / unhealthy | `docker logs <prometheus-container>`; fix `prometheus.yml` mount path or disk. |
| **200** on VM localhost, **timeout** from LAN | Open host firewall: allow TCP **9090** from `192.168.0.0/24` (UFW `allow from 192.168.0.0/24 to any port 9090 proto tcp` or equivalent). Confirm Docker publishes `0.0.0.0:9090`, not `127.0.0.1:9090`. |
| Intentionally localhost-only | Document in audit doc; use SSH tunnel or VPN for metrics. |

---

## Verify after change

From dev PC:

```powershell
(Invoke-WebRequest -Uri "http://192.168.0.188:9090/-/healthy" -UseBasicParsing -TimeoutSec 10).StatusCode
```

Expect **200**.

---

## References

- [MYCOSOFT_PLATFORM_AUDIT_INVENTORY_AND_GAPS_MAY02_2026.md](./MYCOSOFT_PLATFORM_AUDIT_INVENTORY_AND_GAPS_MAY02_2026.md) — platform audit  
- `scripts/diagnose_prometheus_mas188.py` — automated SSH checks  
