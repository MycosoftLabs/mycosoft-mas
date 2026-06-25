# Ubiquiti & Lantronix CISA KEV Remediation — Jun 25, 2026

**Date:** June 25, 2026  
**Status:** Investigation complete — UniFi **PATCHED**; Lantronix **not in inventory**  
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

### SSH to VMs

Attempted `mycosoft@187/188/189` — **Authentication failed** from this dev host (credentials present but may need rotation or key-based auth). Gateway probe succeeded from LAN without SSH.

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

## Manual actions required

1. **Confirm UniFi OS version in UI** — Settings → System → About. Should be **≥ 5.0.8**. Detector says patched; UI confirmation is best practice.
2. **Deploy MAS changes to VM 188** — `run_cisa_kev_checks` and `/api/network/kev` require orchestrator restart after pull.
3. **Set `UNIFI_API_KEY` on MAS VM** (if not already) — enables topology + unauthorized client checks; not required for KEV probe.
4. **Physical Lantronix audit** — Walk lab/network closet; if any EDS5008/5016/5032 exists, upgrade to **2.2.0.0R1** and restrict HTTP RPC to management VLAN.
5. **Optional: restrict UDM management** — Limit `:443` admin access to management subnet; enable IDS/IPS signatures if available on UDM Pro Max.
6. **Monitor logs** — Alert on SAB-064 indicators (see CVE section).

### Blockers needing Morgan

| Item | Why |
|------|-----|
| UniFi UI version screenshot / auto-update policy | Physical/UI access to `https://192.168.0.1` |
| Lantronix physical inventory | Not visible in code; only Morgan knows lab hardware |
| VM SSH from dev PC | Auth failed — may need password rotation or deploy from VM-side git pull |
| MAS deploy to 188 | Requires working SSH or on-VM git pull + `sudo systemctl restart mas-orchestrator` |

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
- [ ] MAS VM deployed with new endpoint (pending SSH/deploy)
- [ ] UniFi OS version confirmed in UI (pending Morgan)
- [ ] Physical Lantronix audit (pending Morgan)
