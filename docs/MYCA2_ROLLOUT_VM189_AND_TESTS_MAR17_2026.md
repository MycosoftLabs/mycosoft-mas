# MYCA2 rollout VM189 + MAS + tests — Mar 17, 2026

**Status:** MINDEX `docker-compose.yml` fix is on `main` (earth-sync YAML: heredoc so `while True:` does not break parsing). **Redeploy from a machine on `192.168.0.0/24`** — Cursor/agent runs that SSH to 189 often time out (WinError 10060) when not on LAN.

## 1. VM 189 — Postgres + MINDEX API

On **your dev PC** (VPN/LAN to Proxmox):

```powershell
cd C:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas
# load .credentials.local into process env, then:
python scripts/myca2_vm_rollout.py --mindex
```

Or manually on **189**:

```bash
cd ~/mindex && git fetch origin && git reset --hard origin/main
docker compose config --quiet   # must pass
docker compose build --no-cache mindex-api
docker compose up -d mindex-api mindex-postgres
```

Migration **0023** (MYCA2/PSILO tables) is applied by `myca2_vm_rollout.py --mindex` / `--migrate-only` if not already applied.

## 2. VM 188 — MAS

```powershell
python scripts/myca2_vm_rollout.py --mas
```

## 3. VM 187 — Website (only if MYCA2/plasticity API routes changed)

Follow usual sandbox rebuild + NAS mount + Cloudflare purge (`deploy-website-sandbox` skill / `_rebuild_sandbox.py`).

## 4. MYCA2 smoke tests (exercise live stack)

Requires MAS **8001** + MINDEX **8000** reachable:

```powershell
$env:MYCA2_VM_SMOKE = "1"
# optional: $env:MAS_API_URL / $env:MINDEX_API_URL
poetry run pytest tests/test_myca2_vm_smoke.py -v
```

Or:

```powershell
python scripts/myca2_vm_rollout.py --test
```

**Full chain:** `python scripts/myca2_vm_rollout.py --all` (after `main` is pushed for mindex + mas + website as needed).

## References

- `scripts/myca2_vm_rollout.py`
- `tests/test_myca2_vm_smoke.py`
- `MINDEX/mindex/migrations/0023_myca2_psilo_registry.sql`
