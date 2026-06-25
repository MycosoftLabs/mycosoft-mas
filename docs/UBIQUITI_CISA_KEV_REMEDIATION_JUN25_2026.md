# Ubiquiti & Lantronix CISA KEV Remediation — Jun 25, 2026

**Date:** June 25, 2026  
**Status:** Complete — UniFi **PATCHED**; MAS deployed; Lantronix **NOT_IN_INVENTORY** (code + LAN port scan)  
**Trigger:** [BleepingComputer — CISA warns of max severity Ubiquiti flaws exploited in attacks](https://www.bleepingcomputer.com/news/security/cisa-warns-of-max-severity-ubiquiti-flaws-exploited-in-attacks/) (Jun 24, 2026)  
**Related:** Ubiquiti [Security Advisory Bulletin 064 (SAB-064)](https://community.ui.com/releases/Security-Advisory-Bulletin-064), [Bishop Fox detection script](https://github.com/BishopFox/CVE-2026-34908-check), [CISA ICS advisory ICSA-26-069-02 (Lantronix)](https://www.cisa.gov/news-events/ics-advisories/icsa-26-069-02)

---

## Executive summary

| CVE | Product | Severity | CISA KEV | Mycosoft exposure | Status |
|-----|---------|----------|----------|---------------------|--------|
| CVE-2026-34908 | UniFi OS | CVSS 10.0 | Actively exploited | **192.168.0.1** (UDM Pro Max) | **PATCHED** (detector: 5.0.8+ behavior) |
| CVE-2026-34909 | UniFi OS | CVSS 10.0 | Actively exploited | Same gateway | **PATCHED** (chained with 34908) |
| CVE-2026-34910 | UniFi OS | CVSS 10.0 | Actively exploited | Same gateway | **PATCHED** (chained with 34908/09) |
| CVE-2025-67038 | Lantronix EDS5000 | Critical | Actively exploited | **None found** in repos or LAN audit | **NOT IN INVENTORY** |

**Live probe (Jun 25, 2026):** Bishop Fox safe detector against `192.168.0.1:443` returned **`PATCHED`** — nginx rejected the auth-bypass path normalization (expected UniFi OS Server **5.0.8+** fix).

---

## CVE details

### UniFi OS chain (CVE-2026-34908 / 34909 / 34910)

| Field | Detail |
|-------|--------|
| **Impact** | Unauthenticated attackers can chain auth bypass + path traversal + command injection → **root RCE** on UniFi OS Server |
| **Affected** | UniFi OS Server **≤ 5.0.6** on UDM, UDM-Pro, UDM-Pro Max, UCG, UNVR, Cloud Key, self-hosted controllers |
| **Fix** | UniFi OS Server **5.0.8+** (Ubiquiti SAB-064, May 2026) |
| **Detection** | Bishop Fox `cve_2026_34908_check.py` — non-destructive probe; port **443** on Mycosoft UDM (not default 11443) |
| **Log indicators** | Requests to `/api/auth/validate-sso/` with `%2f` traversal; `/proxy/users/api/v2/ucs/update/latest_package`; unexpected `ucs-update` child processes |

### Lantronix EDS5000 (CVE-2025-67038)

| Field | Detail |
|-------|--------|
| **Impact** | HTTP RPC logs failed auth by shell-concatenating username → **root command injection** |
| **Affected** | EDS5008, EDS5016, EDS5032 firmware **2.1.0.0R3** |
| **Fix** | Firmware **2.2.0.0R1** ([Lantronix release notes](https://ltrxdev.atlassian.net/wiki/spaces/LTRXTS/pages/2538438657/Latest+Firmware+for+the+EDS5000+series+EDS5008+EDS5016+EDS5032)) |
| **Mycosoft note** | Device fleet uses **MycoBrain ESP32**, **USB/COM serial**, and **Jetson** gateways — **no Lantronix EDS5000** references in any repo |

---

## Mycosoft asset inventory

### Network gateway (affected product class)

| Asset | IP | Role | Hardware | Probe result |
|-------|-----|------|----------|--------------|
| **UniFi Dream Machine Pro Max** | `192.168.0.1` | LAN gateway, DNS, firewall, UniFi controller | `UDMPROMAX` (per `/api/system`) | **PATCHED** @ `:443` |

**Fingerprint markers:** UniFi OS, UDM, Dream Machine (HTTPS `:443`).

**Ports:** `443` open (management UI); `11443` closed/timeout (Bishop Fox default — use `host:443`).

### LAN infrastructure (not directly affected by these CVEs)

| Asset | IP | Notes |
|-------|-----|-------|
| Sandbox VM | 192.168.0.187 | Website Docker, MycoBrain host |
| MAS VM | 192.168.0.188 | Orchestrator :8001, n8n |
| MINDEX VM | 192.168.0.189 | Postgres, Redis, Qdrant, API :8000 |
| MYCA VM | 192.168.0.191 | MYCA workspace |
| Voice Legion | 192.168.0.241 | PersonaPlex / Moshi |
| Earth-2 Legion | 192.168.0.249 | Earth-2 API |
| NAS (UniFi-hosted share) | 192.168.0.105 | `\\192.168.0.105\mycosoft.com` — not UniFi OS appliance firmware |

### Serial / IoT gateways

| Technology | Used by Mycosoft? | Lantronix EDS5000? |
|------------|-------------------|---------------------|
| MycoBrain service (COM/USB) | Yes — local :8003, Sandbox :8003 | **No** |
| ESP32 MDP firmware | Yes | **No** |
| Jetson OpenClaw gateway | Optional (192.168.0.123) | **No** |
| Lantronix EDS5000 | **Not documented** | **No inventory** |

---

## Commands run and results

### Bishop Fox detector (vendored)

```text
python scripts/security/cve_2026_34908_check.py 192.168.0.1:443 --json
→ verdict: PATCHED
→ detail: nginx rejected the normalized-path divergence (HTTP 400) — 5.0.8+ behavior
```

### Mycosoft wrapper

```text
python scripts/security/probe_unifi_kev.py 192.168.0.1 443
→ fingerprint: UniFi OS / UDM / Dream Machine
→ detector.verdict: PATCHED
```

### Connectivity

```text
Test-NetConnection 192.168.0.1 -Port 443  → True
Test-NetConnection 192.168.0.1 -Port 11443 → False (timeout)
GET https://192.168.0.1/api/system → Dream Machine Pro Max (UDMPROMAX)
GET http://192.168.0.188:8001/api/network/health → ok (pre-deploy code path)
```

### Repo search

```text
rg -i "ubiquiti|unifi|lantronix|EDS5000" D:\Users\admin2\Desktop\MYCOSOFT\CODE
→ UniFi: MAS integrations (unifi_client.py), network-monitor agent, zct bootstrap
→ Lantronix: no matches
```

### MAS VM deploy (Jun 25, 2026 11:09 UTC)

```text
git pull origin/main on 192.168.0.188 → 1db70795
sudo systemctl restart mas-orchestrator
GET /health → 200
GET /api/network/kev → 200 (verdict PATCHED)
GET /api/network/diagnostics → 200
GET /api/network/health → 200
```

Systemd drop-in `/etc/systemd/system/mas-orchestrator.service.d/unifi-env.conf` sets `UNIFI_HOST`, `UNIFI_UDM_IP`, `UNIFI_KEV_CHECK_PORT` (no API key in repo).

### NAS 192.168.0.105 (Jun 25, 2026)

```text
Test-NetConnection 192.168.0.105:445 → True (SMB)
From VM 188: TCP 445, 2049 (NFS), 80 → open
showmount -e 192.168.0.105 → showmount not installed on VM (install nfs-common to enumerate exports)
```

### Lantronix LAN scan (Jun 25, 2026)

```text
rg lantronix|EDS5000 across CODE → only KEV remediation docs + MAS network code (no hardware refs)
TCP scan 192.168.0.1–19, .105, .123, .187–189, .241, .249 ports 30718/10001/80 → no Lantronix RPC (30718) open
Verdict: NOT_IN_INVENTORY — physical closet audit still recommended
```

### UniFi API auth (Jun 25, 2026)

```text
WEBSITE .credentials.local: UNIFI_USERNAME, UNIFI_PASSWORD, UNIFI_UDM_IP (no UNIFI_API_KEY in any repo)
POST /api/auth/login → 499 (SSO enabled on UDM; local password login blocked)
scripts/unifi_scan_topology.py → login failed (same SSO blocker)
MAS /api/network/diagnostics → unauthorized.configured=false, reason=UNIFI_API_KEY not set
```

**To enable topology:** UniFi UI → Settings → Control Plane → Integrations → create **API key** → add `UNIFI_API_KEY` to VM systemd drop-in (and website `.credentials.local`).

### UniFi OS version

| Source | Result |
|--------|--------|
| Bishop Fox KEV probe | **PATCHED** (5.0.8+ nginx behavior) |
| `GET /api/system` (unauthenticated) | UDM Pro Max (`UDMPROMAX`), no version field |
| `GET /status` HTML | No reliable OS version string (SSO UI shell) |
| UI Settings → System → About | **Pending Morgan** — confirm **≥ 5.0.8** |

---

## Actions taken (automation & code)

| Change | Path |
|--------|------|
| Bishop Fox detector vendored | `scripts/security/cve_2026_34908_check.py` |
| Mycosoft KEV probe wrapper | `scripts/security/probe_unifi_kev.py` |
| CISA KEV checks in network diagnostics | `mycosoft_mas/services/network_diagnostics.py` → `run_cisa_kev_checks()` |
| New API endpoint | `GET /api/network/kev` in `mycosoft_mas/core/routers/network_api.py` |
| Full diagnostics now includes KEV | `run_full_diagnostics()` vulnerabilities section |
| NetworkMonitorAgent task | `cisa_kev_check` + alerts in `run_cycle()` |
| Agent docs updated | `.cursor/agents/network-monitor.md` |

### Environment variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `UNIFI_HOST` | `192.168.0.1` | Gateway to probe |
| `UNIFI_KEV_CHECK_PORT` | `443` | UDM management port (not 11443) |
| `UNIFI_API_KEY` | (optional) | Topology/clients via Network API |

---

## Manual actions required (remaining)

1. **Confirm UniFi OS version in UI** — Settings → System → About. Should be **≥ 5.0.8**. KEV probe confirms patched behavior; UI string still pending.
2. **Create and deploy `UNIFI_API_KEY`** — SSO blocks password login (`499`). Create API key in UniFi UI → add to VM systemd drop-in + `WEBSITE/website/.credentials.local` to enable topology/unauthorized client checks.
3. **Physical Lantronix audit** — Walk lab/network closet; code + LAN port scan found no EDS5000 RPC. If any EDS5008/5016/5032 exists, upgrade to **2.2.0.0R1**.
4. **Optional: restrict UDM management** — Limit `:443` admin access to management subnet; enable IDS/IPS signatures on UDM Pro Max.
5. **Optional: NFS export inventory** — Install `nfs-common` on VM 188 and run `showmount -e 192.168.0.105` for Proxmox backup path verification.

### Completed automation (Jun 25, 2026)

| Item | Result |
|------|--------|
| Git commit + push | `1db707952` on `origin/main` |
| MAS VM 188 deploy | `git reset --hard origin/main`, orchestrator restarted, git SHA `1db70795` |
| KEV + diagnostics endpoints | HTTP 200 from 188 |
| NAS SMB | `192.168.0.105:445` reachable |
| NAS NFS port | TCP 2049 open (exports not enumerated) |
| Lantronix | NOT_IN_INVENTORY (repo + port scan) |

### Blockers needing Morgan (UI-only)

| Item | Why |
|------|-----|
| UniFi OS exact version string | `/api/system` omits version; UI About required |
| `UNIFI_API_KEY` creation | Not stored in any `.credentials.local`; SSO blocks password API |
| Physical Lantronix hardware | Not discoverable remotely |

---

## Ongoing monitoring

```bash
# After MAS deploy on 188
curl "http://192.168.0.188:8001/api/network/kev"

# From MAS repo (any LAN host)
python scripts/security/probe_unifi_kev.py

# Weekly: include in network_monitor agent cycle or n8n workflow
```

**Alert conditions:** `verdict == VULNERABLE` or `INCONCLUSIVE` on UniFi probe; any new Lantronix device discovered on LAN.

---

## References

- CISA BOD 26-04 — federal agencies must patch KEV within 3 days
- [Bishop Fox — Popping Root on UniFi OS Server](https://bishopfox.com/blog/popping-root-on-unifi-os-server-unauthenticated-rce-chain-detection-analysis)
- MAS: `mycosoft_mas/integrations/unifi_client.py`, `docs/VM_LAYOUT_AND_DEV_REMOTE_SERVICES_FEB06_2026.md`

---

## Verification checklist

- [x] All four CVEs researched
- [x] Mycosoft repos searched for UniFi/Lantronix
- [x] Live UniFi gateway probed — **PATCHED**
- [x] UDM Pro Max identified at 192.168.0.1
- [x] Lantronix — not in codebase
- [x] Detection automation added to MAS
- [x] MAS VM deployed with new endpoints (`1db70795`, Jun 25 2026)
- [x] NAS 192.168.0.105 SMB reachable; NFS port 2049 open
- [x] Lantronix repo + LAN port scan — NOT_IN_INVENTORY
- [ ] UniFi OS version confirmed in UI (pending Morgan — probe shows PATCHED)
- [ ] `UNIFI_API_KEY` created and set on VM 188 (pending Morgan — SSO blocks password login)
- [ ] Physical Lantronix closet audit (pending Morgan)
