# MINDEX VM 189 – AVX/Bun Crash Assessment (Feb 9, 2026)

## Summary

- **VM 189 (MINDEX)** is different from 187 and 188: its CPU (or the VM’s exposed CPU features) **does not support AVX**.  
- The **“bun has crashed” / segmentation fault** on 189 comes from **Claude Code** (or another Bun-based app), **not** from MINDEX.  
- **MINDEX does not use Bun.** The MINDEX stack (Postgres, Redis, Qdrant, MINDEX API) is Python/FastAPI only and does not require AVX.  
- **Recommendation:** Do **not** install or run Claude Code on VM 189. Use 189 only for MINDEX services; keep Claude Code on 187 (and optionally 188).

---

## Why VM 189 Looks Different

| Aspect | 187 (Sandbox) | 188 (MAS) | 189 (MINDEX) |
|--------|----------------|-----------|----------------|
| **Role** | Website, Claude Code (coding agent target) | MAS orchestrator, agents, optional Claude | **Database + vector store + MINDEX API only** |
| **Stack** | Docker, Next.js, Claude Code (Bun/Electron) | Docker, Python, optional Claude Code | **Docker, Python, Postgres, Redis, Qdrant** |
| **Claude Code needed?** | **Yes** – coding agent SSHs here to run `claude -p` | Optional (convenience) | **No** – not part of MYCA coding flow |
| **Typical setup** | App server + dev tooling | App server + agents | **Data server: minimal OS + containers** |
| **CPU/VM** | Often newer or AVX exposed | Often newer or AVX exposed | **Older CPU or VM without AVX** → Bun segfault |

So 189 is “different” by design: it’s the **data host** (Postgres, Redis, Qdrant, MINDEX API), not an app/dev host. The “different console” and the Bun crash are from running a **desktop/dev tool (Claude Code)** on a machine that doesn’t support the tool’s requirements (AVX).

---

## What the Error Means

- **“bun has crashed” / “segmentation fault at address 0x…”**  
  Bun (the JavaScript runtime) is hitting an illegal instruction or bad memory access. On x86_64, this often happens when the binary was built to use **AVX** and the CPU (or what the VM exposes) doesn’t support it.

- **“CPU lacks AVX support” / “suggests newer CPU”**  
  - **AVX (Advanced Vector Extensions)** = extra CPU instructions (Intel/AMD) used by many modern binaries.  
  - If the **physical CPU** is old (pre‑2011 Intel, or similar), it may not have AVX.  
  - If 189 is a **VM**, the hypervisor (e.g. Proxmox) might give this VM an older CPU model or hide AVX for compatibility, so the guest sees “no AVX.”  
  - Bun (and some Node/Electron builds) assume AVX is present → they crash on 189.

So: **189’s “CPU” (real or virtual) does not advertise AVX**, and anything that requires AVX (like Bun / Claude Code) will segfault there. That’s expected for this VM if it’s older or configured without AVX.

---

## Why MINDEX on 189 Is Unaffected

- **MINDEX stack on 189:**
  - **PostgreSQL** (postgres:15-alpine) – C, no AVX requirement for normal use.
  - **Redis** (redis:7-alpine) – C, no AVX requirement for normal use.
  - **Qdrant** (qdrant/qdrant) – Rust; typically supports non-AVX or has fallbacks.
  - **MINDEX API** – **Python 3.11 + FastAPI + uvicorn** (see `MINDEX/mindex/Dockerfile` and `pyproject.toml`). No Bun, no Node, no AVX requirement from our stack.

So the **Bun crash is not from MINDEX**. It comes from **Claude Code** (or another Bun-based app) you installed on 189. MINDEX itself can run perfectly on a non-AVX host.

---

## What to Do

### 1. Do not run Claude Code on VM 189

- **Claude Code is only required on 187 (Sandbox).** The MYCA coding agent SSHs to 187 and runs `claude -p` there.  
- Installing Claude Code on 189 is optional and, on this VM, causes the Bun crash.  
- **Recommendation:** Uninstall or do not use Claude Code on 189. Use 189 only for MINDEX services.

### 2. Keep 189 as the data-only host

- **189’s job:** Postgres 5432, Redis 6379, Qdrant 6333/6334, and (if deployed) MINDEX API 8000.  
- No need for Claude Code, Bun, or Node on 189 for the Mycosoft pipeline.  
- “Different console” and “different setup” are expected: 189 is a **data server**, not an app/dev box like 187/188.

### 3. If you need a “unified” console for 189

- Use **SSH + terminal** (e.g. `ssh mycosoft@192.168.0.189`) and run only:
  - `docker ps` / `docker compose logs`
  - `curl http://localhost:8000/api/mindex/health` (if MINDEX API is on 189)
  - Postgres/Redis/Qdrant admin commands as in `docs/MINDEX_VM_DEPLOYMENT_STATUS_FEB04_2026.md`  
- Do **not** install Claude Code (or other Bun/Electron apps) on 189.

### 4. If 189’s hardware or Proxmox config can be changed

- **If 189 is a VM:** In Proxmox, check the VM’s CPU type. If it’s set to something like “kvm64” or an older model, the guest may not see AVX. Changing to “host” (or a newer model that exposes AVX) can fix Bun/Claude Code on 189 – but again, **Claude Code is not required on 189**.  
- **If 189 is physical:** The CPU may simply not support AVX. No software change can add AVX; the only fix for running Bun there would be different hardware.

---

## Quick Health Check (189)

From your workstation (or 187/188), verify MINDEX services on 189:

```bash
# Containers
ssh mycosoft@192.168.0.189 "sudo docker ps"

# MINDEX API (if deployed on 189)
curl -s http://192.168.0.189:8000/api/mindex/health

# Postgres (from host with psql)
psql -h 192.168.0.189 -U mycosoft -d mindex -c "SELECT 1"

# Redis
redis-cli -h 192.168.0.189 PING

# Qdrant
curl -s http://192.168.0.189:6333/
```

If these succeed, **MINDEX on 189 is working**. The Bun crash is unrelated to MINDEX and can be ignored by not running Claude Code (or other Bun-based apps) on 189.

**Verified Feb 9, 2026:** On 189, `mindex-postgres`, `mindex-redis`, and `mindex-qdrant` are Up (ports 5432, 6379, 6333). MINDEX API (port 8000) may be deployed on 187 or at a different path on 189; the data stack on 189 is healthy.

---

## Reference

| Doc | Purpose |
|-----|--------|
| `docs/MINDEX_VM_DEPLOYMENT_STATUS_FEB04_2026.md` | 189 services, paths, SSH, management |
| `docs/VM_LAYOUT_AND_DEV_REMOTE_SERVICES_FEB06_2026.md` | VM roles and URLs |
| `docs/MYCA_CODING_SYSTEM_FEB09_2026.md` | Claude Code on **187** only for coding agent |

---

**Bottom line:** VM 189 is the MINDEX data host and does not need Claude Code. The Bun crash is from Claude Code (or similar) expecting AVX on a machine that doesn’t have it. Keep 189 for Postgres, Redis, Qdrant, and MINDEX API only; leave Claude Code off 189 so MINDEX can run perfectly there.
