# MYCA2 VM rollout and smoke — Mar 17, 2026

**Status:** Operational runbook  
**Related:** `scripts/myca2_vm_rollout.py`, migration `migrations/0023_myca2_psilo_registry.sql`, plan `myca2_psilo_stack`

## Scope

- **Postgres on VM 189** — PSILO/MYCA2 tables via MINDEX migration applied to `mindex-postgres`.
- **MINDEX API (189)** — `docker compose` pull/build/up `mindex-api` after migration.
- **MAS (188)** — `git pull`, **stop `mas-orchestrator`** (frees host :8001), Docker run `myca-orchestrator-new` with `MINDEX_API_URL=http://192.168.0.189:8000`.
- **Website (187)** — Only if plasticity/MYCA2 API routes changed; rebuild container, NAS mount, Cloudflare purge (script prints reminder).

## One-shot rollout (from dev PC with `.credentials.local`)

```powershell
cd C:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas
Get-Content .\.credentials.local | ForEach-Object {
  if ($_ -match "^([^#=]+)=(.*)$") {
    [Environment]::SetEnvironmentVariable($matches[1].Trim(), $matches[2].Trim(), "Process")
  }
}
python scripts/myca2_vm_rollout.py --all --test
```

Steps: migrate 189 → MINDEX API → MAS Docker → smoke (MAS health, MINDEX `db==ok`, PSILO start + get).

## Smoke only (no deploy)

```powershell
python scripts/myca2_vm_rollout.py --test
```

## Pytest (same checks)

```powershell
$env:MYCA2_VM_SMOKE = "1"
poetry run pytest tests/test_myca2_vm_smoke.py -v
```

Optional: `MAS_API_URL`, `MINDEX_API_URL`.

## Rollback MAS to systemd

If you need host `mas-orchestrator` again:

```bash
ssh mycosoft@192.168.0.188
docker stop myca-orchestrator-new 2>/dev/null; docker rm myca-orchestrator-new 2>/dev/null
sudo systemctl start mas-orchestrator
```

## Verify

- `http://192.168.0.189:8000/api/mindex/health` → `"db": "ok"`
- `http://192.168.0.188:8001/health` (or probed port)
- `POST /api/plasticity/psilo/session/start` → `session_id`; `GET .../session/{id}` → 200
