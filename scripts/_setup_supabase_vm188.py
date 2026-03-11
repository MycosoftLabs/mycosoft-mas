#!/usr/bin/env python3
"""
Automated Supabase backbone setup on VM 188.

Creates .env on VM, configures systemd EnvironmentFile, copies Google creds if present,
restarts mas-orchestrator, and syncs n8n workflow.

Credentials: Read from .env (MAS repo root) or os.environ.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Load .env from MAS repo root and common credential locations
_root = Path(__file__).resolve().parent.parent
_env = _root / ".env"
for env_file in [
    _env,
    _root.parent.parent / "WEBSITE" / "website" / ".env.local",
    _root.parent.parent / "website" / "website" / ".env.local",
    Path.home() / ".mycosoft-credentials",
]:
    if env_file and env_file.exists():
        for line in env_file.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                v = v.strip().strip('"').strip("'")
                if k.strip() and v:
                    os.environ.setdefault(k.strip(), v)

# Load VM password
creds = Path(__file__).resolve().parent.parent / ".credentials.local"
pw = ""
if creds.exists():
    for line in creds.read_text().splitlines():
        if "=" in line and not line.strip().startswith("#"):
            k, v = line.split("=", 1)
            if k.strip() in ("VM_PASSWORD", "VM_SSH_PASSWORD"):
                pw = v.strip()
                break
pw = pw or os.environ.get("VM_PASSWORD") or os.environ.get("VM_SSH_PASSWORD", "")
if not pw:
    print("Set VM_PASSWORD or VM_SSH_PASSWORD")
    sys.exit(1)

# Supabase credentials from env
supabase_url = os.environ.get("NEXT_PUBLIC_SUPABASE_URL", "").strip()
supabase_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "").strip()
supabase_pub = os.environ.get("NEXT_PUBLIC_SUPABASE_PUBLISHABLE_DEFAULT_KEY", "").strip()

if not supabase_url or not supabase_key:
    print("Set NEXT_PUBLIC_SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY")
    sys.exit(1)

# Google Sheets credentials: GOOGLE_SHEETS_CREDENTIALS_JSON (inline/base64) or file path
import base64
import json as _json

sheets_json_inline = os.environ.get("GOOGLE_SHEETS_CREDENTIALS_JSON", "").strip()
sheets_json_bytes = None
if sheets_json_inline:
    try:
        if sheets_json_inline.startswith("eyJ"):  # base64 of '{"'
            sheets_json_bytes = base64.b64decode(sheets_json_inline).decode("utf-8")
        else:
            sheets_json_bytes = sheets_json_inline
        _j = _json.loads(sheets_json_bytes)
        if _j.get("type") == "service_account":
            sheets_json_bytes = _json.dumps(_j)  # minified for writing
        else:
            sheets_json_bytes = None
    except Exception:
        sheets_json_bytes = None

sheets_creds_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS") or os.environ.get("GOOGLE_SERVICE_ACCOUNT_PATH")
local_sheets = Path(sheets_creds_path) if sheets_creds_path else None
if not sheets_json_bytes and (not local_sheets or not local_sheets.exists()):
    # Auto-discover service account JSON in common paths
    for p in [
        Path.home() / "Desktop" / "MYCOSOFT" / "cred",
        Path.home() / "MYCOSOFT" / "cred",
        _root / "cred",
        _root.parent / "cred",
    ]:
        if p.exists():
            for f in sorted(p.glob("*.json")):
                try:
                    content = f.read_text(encoding="utf-8")
                    j = _json.loads(content)
                    if j.get("type") == "service_account":
                        local_sheets = f
                        sheets_json_bytes = content
                        break
                except Exception:
                    pass
            if local_sheets or sheets_json_bytes:
                break

import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect("192.168.0.188", username="mycosoft", password=pw, timeout=15)
sftp = client.open_sftp()


def run(cmd: str, use_sudo: bool = False) -> tuple[str, str]:
    if use_sudo:
        sin, sout, serr = client.exec_command(f"echo {repr(pw)} | sudo -S bash -c {repr(cmd)}")
    else:
        sin, sout, serr = client.exec_command(cmd)
    out = sout.read().decode()
    err = serr.read().decode()
    return out, err


# 1. Create cred dir and write service account JSON if we have it
run("mkdir -p /home/mycosoft/mycosoft/cred")
remote_sheets = "/home/mycosoft/mycosoft/cred/myca-sheets.json"
if sheets_json_bytes:
    try:
        with sftp.open(remote_sheets, "wb") as f:
            f.write(sheets_json_bytes.encode("utf-8"))
        print(f"Wrote service account JSON to {remote_sheets}")
    except Exception as e:
        remote_sheets = ""
        print(f"Could not write Sheets creds: {e}")
elif local_sheets and local_sheets.exists():
    try:
        content = local_sheets.read_bytes()
        j = _json.loads(content)
        if j.get("type") == "service_account":
            with sftp.open(remote_sheets, "wb") as f:
                f.write(content)
            print(f"Copied service account JSON to {remote_sheets}")
        else:
            remote_sheets = ""
            print("Local JSON is not a service_account; skip Sheets creds")
    except Exception as e:
        remote_sheets = ""
        print(f"Could not copy Sheets creds: {e}")
else:
    remote_sheets = ""
    print("No Google Sheets credentials. Set GOOGLE_SHEETS_CREDENTIALS_JSON (inline JSON or base64) or GOOGLE_APPLICATION_CREDENTIALS path.")

# 2. N8N_API_KEY for workflow sync
# n8n API keys live in DB, not env. Always inject fresh key into n8n so MAS can sync workflows.
o, _ = run("docker ps -q -f name=n8n 2>/dev/null | head -1")
n8n_container = (o or "").strip()
n8n_key = ""
n8n_key_for_env = ""

if n8n_container:
    o2, _ = run(
        "python3 -c 'import secrets; print(secrets.token_urlsafe(32))' 2>/dev/null || openssl rand -hex 24 2>/dev/null"
    )
    n8n_key = (o2 or "").strip()
    if n8n_key:
        run("docker stop %s 2>/dev/null" % n8n_container)
        db_path = ""
        for cand in ["/home/node/.n8n/database.sqlite", "/root/.n8n/database.sqlite"]:
            run("docker cp %s:%s /tmp/n8n_db.sqlite 2>/dev/null" % (n8n_container, cand))
            o, _ = run("test -f /tmp/n8n_db.sqlite && wc -c /tmp/n8n_db.sqlite | awk '{print $1}'")
            if o and o.strip().isdigit() and int(o.strip()) > 0:
                db_path = cand
                break
        if db_path:
            # n8n 1.62+ uses user_api_keys (id, userId, label, apiKey, createdAt, updatedAt); older uses user.apiKey.
            key_val = "n8n_api_" + n8n_key if not n8n_key.startswith("n8n_api_") else n8n_key
            inject_script = (
                "import sqlite3, uuid\n"
                "c = sqlite3.connect('/tmp/n8n_db.sqlite')\n"
                "cur = c.cursor()\n"
                # Resolve table name (n8n may use prefix like "user_api_keys" or "n8n_user_api_keys")
                "cur.execute(\"SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%%user_api_keys'\")\n"
                "tbl = cur.fetchone()\n"
                "tbl = tbl[0] if tbl else None\n"
                "if tbl:\n"
                "  cur.execute('SELECT id FROM \"user\" LIMIT 1')\n"
                "  row = cur.fetchone()\n"
                "  uid = row[0] if row else None\n"
                "  if uid:\n"
                "    cur.execute('DELETE FROM \"' + tbl + '\" WHERE \"label\"=?', ('mas-sync',))\n"
                "    rid = str(uuid.uuid4())\n"
                "    cur.execute('INSERT INTO \"' + tbl + '\" (\"id\", \"userId\", \"label\", \"apiKey\", \"createdAt\", \"updatedAt\") VALUES (?,?,?,?,datetime(\"now\"),datetime(\"now\"))',\n"
                "      (rid, uid, 'mas-sync', %r))\n"
                "else:\n"
                "  cur.execute(\"SELECT name FROM sqlite_master WHERE type='table' AND name='user'\")\n"
                "  if cur.fetchone():\n"
                '    cur.execute(\'PRAGMA table_info("user")\')\n'
                "    cols = [r[1] for r in cur.fetchall()]\n"
                "    col = 'apiKey' if 'apiKey' in cols else 'api_key'\n"
                "    cur.execute('UPDATE \"user\" SET \"' + col + '\" = ?', (%r,))\n"
                "c.commit()\n"
                "c.close()\n"
            ) % (key_val, key_val)
            with sftp.open("/tmp/inject_n8n_key.py", "wb") as f:
                f.write(inject_script.encode())
            run("python3 /tmp/inject_n8n_key.py 2>/dev/null")
            run("docker cp /tmp/n8n_db.sqlite %s:%s 2>/dev/null" % (n8n_container, db_path))
            print("Injected N8N_API_KEY into n8n database")
        else:
            print("Could not find n8n SQLite DB (Postgres or custom path?)")
        run("docker start %s 2>/dev/null" % n8n_container)
        import time as _t
        _t.sleep(8)
# Use full key (n8n_api_xxx) for API auth when we injected into user_api_keys
n8n_key_for_env = ("n8n_api_" + n8n_key) if n8n_key and not n8n_key.startswith("n8n_api_") else (n8n_key or "")
if n8n_key_for_env:
    print("N8N_API_KEY set for n8n workflow sync")
else:
    print("N8N_API_KEY not set; workflow sync may fail with 401")

# 3. Build .env content
env_lines = [
    "# Supabase backbone - auto-generated",
    f"NEXT_PUBLIC_SUPABASE_URL={supabase_url}",
    f"SUPABASE_SERVICE_ROLE_KEY={supabase_key}",
    f"NEXT_PUBLIC_SUPABASE_PUBLISHABLE_DEFAULT_KEY={supabase_pub}",
]
if remote_sheets:
    env_lines.append(f"GOOGLE_APPLICATION_CREDENTIALS={remote_sheets}")
if n8n_key_for_env:
    env_lines.append(f"N8N_API_KEY={n8n_key_for_env}")
# When MAS runs on 188, local and cloud both hit n8n on 188
env_lines.append("N8N_LOCAL_URL=http://localhost:5678")
env_lines.append("N8N_URL=http://localhost:5678")
env_content = "\n".join(env_lines)

# 4. Write .env on VM via sftp
env_path = "/home/mycosoft/mycosoft/mas/.env"
run("mkdir -p /home/mycosoft/mycosoft/mas")
with sftp.open(env_path, "wb") as f:
    f.write(env_content.encode())
print(f"Created {env_path}")

# 5. Systemd override: add EnvironmentFile + explicit N8N_API_KEY (ensures MAS has key)
override_dir = "/etc/systemd/system/mas-orchestrator.service.d"
# Escape '%' for systemd; no other special chars expected in key
_key_escaped = (n8n_key_for_env or "").replace("%", "%%")
override_conf = f"""[Service]
EnvironmentFile={env_path}
Environment=N8N_API_KEY={_key_escaped}
"""
tmp_conf = "/tmp/mas-env-override.conf"
with sftp.open(tmp_conf, "wb") as f:
    f.write(override_conf.encode())
run(f"sudo mkdir -p {override_dir} && sudo mv {tmp_conf} {override_dir}/env.conf", use_sudo=True)
print("Added systemd EnvironmentFile override")

# 6. Daemon reload and restart
o, e = run("sudo systemctl daemon-reload && sudo systemctl restart mas-orchestrator", use_sudo=True)
print("Restarted mas-orchestrator:", "ok" if not e else e[:200])

# 7. Verify n8n accepts the API key (diagnostic)
if n8n_key_for_env:
    o, _ = run(f"KEY=$(grep '^N8N_API_KEY=' {env_path} 2>/dev/null | cut -d= -f2-); curl -s -o /dev/null -w '%{{http_code}}' -H 'X-N8N-API-KEY: $KEY' http://localhost:5678/api/v1/workflows 2>/dev/null || echo '000'")
    code = (o or "000").strip()
    if code == "200":
        print("n8n API key verified (200 OK)")
    else:
        print(f"n8n API key test returned {code} (expected 200)")

# 8. Wait for MAS to come up, then sync n8n workflow
import time
for attempt in range(6):
    time.sleep(10)
    o, e = run(
        "curl -s -m 120 -X POST 'http://127.0.0.1:8001/api/workflows/sync-both' "
        "-H 'Content-Type: application/json' -d '{}' 2>&1"
    )
    out = (o or "").strip()
    if out and ("synced" in out or "status" in out or "workflow" in out.lower()):
        print("n8n workflow sync:", out[:500])
        break
    if attempt < 5:
        print(f"MAS not ready (attempt {attempt+1}/6), retrying...")
else:
    print("n8n sync skipped (MAS may need more time to start)")

sftp.close()
client.close()
print("Setup complete.")
