#!/usr/bin/env python3
"""
Provision Shinobi super API token, register admin if DB empty, read Users.ke + auth,
sync SHINOBI_* to Sandbox 187 .env, recreate website, purge Cloudflare.

See module docstring in previous revision for behavior.
"""
from __future__ import annotations

import json
import os
import re
import secrets
import time
import urllib.error
import urllib.request
from pathlib import Path

MAS = Path(__file__).resolve().parent.parent

SHINOBI_HTTP = os.environ.get("SHINOBI_HTTP", "http://192.168.0.188:8080")
MAS_VM = os.environ.get("MAS_VM_IP", "192.168.0.188")
SANDBOX_VM = os.environ.get("SANDBOX_VM_IP", "192.168.0.187")

ADMIN_MAIL = os.environ.get("SHINOBI_AUTOMATION_MAIL", "crep-api@mycosoft.internal")
ADMIN_PASS = os.environ.get("SHINOBI_AUTOMATION_PASS")


def load_credentials() -> None:
    for base in (MAS, MAS.parent / "WEBSITE" / "website"):
        for fname in (".credentials.local", ".env.local"):
            p = base / fname
            if not p.exists():
                continue
            for line in p.read_text(encoding="utf-8").splitlines():
                if line and not line.startswith("#") and "=" in line:
                    k, _, v = line.partition("=")
                    os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def quote_env_value(val: str) -> str:
    if not val:
        return '""'
    if re.fullmatch(r"[A-Za-z0-9_.:/+-]+", val):
        return val
    esc = val.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{esc}"'


def merge_env_keys(
    content: str, updates: dict[str, str], keys: tuple[str, ...]
) -> str:
    drop = set(updates.keys())
    lines_out: list[str] = []
    for line in content.splitlines():
        s = line.strip()
        if s and not s.startswith("#") and "=" in s:
            key = s.split("=", 1)[0].strip()
            if key in drop:
                continue
        lines_out.append(line)
    for k in keys:
        if k in updates and updates[k]:
            lines_out.append(f"{k}={quote_env_value(updates[k])}")
    body = "\n".join(lines_out)
    if body and not body.endswith("\n"):
        body += "\n"
    return body


def ssh_connect(host: str):
    import paramiko

    pw = os.environ.get("VM_PASSWORD") or os.environ.get("VM_SSH_PASSWORD")
    if not pw:
        raise SystemExit("VM_PASSWORD not set")
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(host, username="mycosoft", password=pw, timeout=45)
    return c


def host_exec(c, cmd: str, timeout: int = 180) -> tuple[int, str]:
    _, stdout, stderr = c.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    code = stdout.channel.recv_exit_status()
    return code, out + err


def docker_exec(c, inner: str, timeout: int = 120) -> tuple[int, str]:
    cmd = f"docker exec shinobi sh -c {json.dumps(inner)}"
    return host_exec(c, cmd, timeout=timeout)


def get_super_json(c) -> list:
    code, out = docker_exec(c, "cat /home/Shinobi/super.json")
    if code != 0:
        raise RuntimeError(f"cat super.json failed: {out[:500]}")
    return json.loads(out.strip())


def put_super_json_sftp(c, data: list) -> None:
    import paramiko

    payload = json.dumps(data, indent=2).encode("utf-8")
    sftp = c.open_sftp()
    try:
        remote_tmp = "/tmp/shinobi_super.json"
        with sftp.file(remote_tmp, "w") as wf:
            wf.write(payload)
    finally:
        sftp.close()
    code, out = host_exec(
        c, f"docker cp {remote_tmp} shinobi:/home/Shinobi/super.json && rm -f {remote_tmp}"
    )
    if code != 0:
        raise RuntimeError(f"docker cp super.json failed: {out[:800]}")


def mysql_query(c, sql: str) -> str:
    inner = f"mysql -u root ccio -N -e {json.dumps(sql)}"
    code, out = docker_exec(c, inner)
    if code != 0:
        raise RuntimeError(f"mysql failed: {out[:500]}")
    return out.strip()


def ensure_super_token(c) -> str:
    data = get_super_json(c)
    if not data:
        raise RuntimeError("super.json empty")
    row = data[0]
    tokens = row.get("tokens") or []
    if isinstance(tokens, str):
        tokens = [tokens]
    if tokens:
        return tokens[0]
    token = secrets.token_hex(16)
    row["tokens"] = [token]
    put_super_json_sftp(c, data)
    code, out = host_exec(c, "docker restart shinobi")
    if code != 0:
        raise RuntimeError(f"docker restart shinobi failed: {out[:500]}")
    time.sleep(18)
    return token


def register_admin_http(super_token: str) -> str | None:
    """Returns plaintext password if registration request was sent (caller saves)."""
    passwd = ADMIN_PASS or secrets.token_urlsafe(24)
    group_ke = secrets.token_hex(4)
    details = {
        "factorAuth": "0",
        "size": "10000",
        "days": "5",
        "event_days": "10",
        "log_days": "10",
        "max_camera": "",
        "permissions": "all",
        "edit_size": "1",
        "edit_days": "1",
        "edit_event_days": "1",
        "edit_log_days": "1",
        "use_admin": "1",
        "use_aws_s3": "1",
        "use_webdav": "1",
        "use_discordbot": "1",
        "use_ldap": "1",
    }
    body = {
        "data": {
            "mail": ADMIN_MAIL,
            "ke": group_ke,
            "pass": passwd,
            "password_again": passwd,
            "details": details,
        }
    }
    url = f"{SHINOBI_HTTP.rstrip('/')}/super/{super_token}/accounts/registerAdmin"
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            raw = r.read().decode("utf-8", errors="replace")
        try:
            j = json.loads(raw)
        except json.JSONDecodeError:
            print("registerAdmin non-JSON response length:", len(raw))
            return None
        print(
            "registerAdmin ok:",
            j.get("ok"),
            "mail:",
            (j.get("user") or {}).get("mail"),
        )
        if j.get("ok") is True:
            return passwd
        print("registerAdmin did not succeed:", (raw or "")[:400])
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")[:500]
        print("registerAdmin HTTPError:", e.code, err_body)
    except urllib.error.URLError as e:
        print("registerAdmin URL failed:", e)
    return None


def register_admin_if_needed(c, super_token: str) -> str | None:
    """Returns new automation password if registerAdmin ran."""
    cnt = mysql_query(c, "SELECT COUNT(*) FROM Users;")
    try:
        n = int(cnt.split()[0])
    except (ValueError, IndexError):
        n = 0
    if n > 0:
        print("Shinobi Users table non-empty; skip registerAdmin.")
        return None
    pw = register_admin_http(super_token)
    time.sleep(3)
    return pw


def fetch_user_keys(c) -> tuple[str, str]:
    out = mysql_query(
        c, f"SELECT ke, auth FROM Users WHERE mail={repr(ADMIN_MAIL)} LIMIT 1;"
    )
    if not out:
        out = mysql_query(c, "SELECT ke, auth FROM Users LIMIT 1;")
    lines = [ln for ln in out.splitlines() if ln.strip()]
    if not lines:
        raise RuntimeError("No Users row with ke/auth")
    parts = lines[0].split("\t")
    if len(parts) < 2:
        parts = lines[0].split()
    ke = parts[0].strip()
    auth = parts[1].strip() if len(parts) > 1 else ""
    if not ke:
        raise RuntimeError("ke empty in DB")
    # MySQL prints NULL; single-account admin uses group key = account ke
    if not auth or auth.upper() == "NULL":
        auth = ke
    return ke, auth


def sync_sandbox_env(api_key: str, group_key: str) -> None:
    import paramiko

    keys = ("SHINOBI_API_KEY", "SHINOBI_GROUP_KEY", "SHINOBI_URL")
    updates = {
        "SHINOBI_API_KEY": api_key,
        "SHINOBI_GROUP_KEY": group_key,
        "SHINOBI_URL": SHINOBI_HTTP,
    }
    pw = os.environ.get("VM_PASSWORD") or os.environ.get("VM_SSH_PASSWORD")
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(SANDBOX_VM, username="mycosoft", password=pw, timeout=45)
    try:
        sftp = client.open_sftp()
        for remote in ("/opt/mycosoft/website/.env", "/opt/mycosoft/.env"):
            try:
                with sftp.file(remote, "r") as rf:
                    raw = rf.read().decode("utf-8", errors="replace")
            except FileNotFoundError:
                print(f"Skip missing {remote}")
                continue
            new_body = merge_env_keys(raw, updates, keys)
            with sftp.file(remote, "w") as wf:
                wf.write(new_body.encode("utf-8"))
            print(f"Updated {remote} ({len(new_body)} bytes)")
        sftp.close()
        cmds = [
            "cd /opt/mycosoft/website && docker compose -f docker-compose.production.yml -f docker-compose.production.blue-green.yml up -d --force-recreate website-blue website-green 2>&1",
            "cd /opt/mycosoft/website && docker compose -p mycosoft-production up -d --force-recreate mycosoft-website 2>&1",
        ]
        for cmd in cmds:
            _, stdout, _ = client.exec_command(cmd, timeout=300)
            out = stdout.read().decode("utf-8", errors="replace")
            code = stdout.channel.recv_exit_status()
            if out.strip():
                print(out.strip()[:1500])
            if code == 0:
                print("Compose recreate succeeded.")
                break
    finally:
        client.close()


def purge_cf() -> None:
    token = os.environ.get("CLOUDFLARE_API_TOKEN")
    zone = os.environ.get("CLOUDFLARE_ZONE_ID")
    if not token or not zone:
        print("Skip Cloudflare purge (token/zone missing).")
        return
    req = urllib.request.Request(
        f"https://api.cloudflare.com/client/v4/zones/{zone}/purge_cache",
        data=json.dumps({"purge_everything": True}).encode(),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            data = json.loads(r.read().decode())
        print("Cloudflare:", "ok" if data.get("success") else data)
    except urllib.error.URLError as e:
        print("Cloudflare purge failed:", e)


def append_local_credentials(
    api_key: str, group_key: str, automation_pass: str | None = None
) -> None:
    """Merge SHINOBI_* into MAS .credentials.local (gitignored), replacing prior values."""
    p = MAS / ".credentials.local"
    if not p.exists():
        return
    keys_api = {"SHINOBI_URL", "SHINOBI_API_KEY", "SHINOBI_GROUP_KEY"}
    lines_out: list[str] = []
    for line in p.read_text(encoding="utf-8").splitlines():
        if line and not line.startswith("#") and "=" in line:
            k = line.split("=", 1)[0].strip()
            if k in keys_api:
                continue
            if k == "SHINOBI_AUTOMATION_MAIL":
                continue
            if k == "SHINOBI_AUTOMATION_PASS" and automation_pass is not None:
                continue
        lines_out.append(line)
    lines_out.append("")
    lines_out.append(
        "# Shinobi (MAS 188) — synced by provision_shinobi_keys_and_sync_sandbox.py"
    )
    lines_out.append(f"SHINOBI_URL={SHINOBI_HTTP}")
    lines_out.append(f"SHINOBI_API_KEY={api_key}")
    lines_out.append(f"SHINOBI_GROUP_KEY={group_key}")
    lines_out.append(f"SHINOBI_AUTOMATION_MAIL={ADMIN_MAIL}")
    if automation_pass is not None:
        lines_out.append(f"SHINOBI_AUTOMATION_PASS={automation_pass}")
    p.write_text("\n".join(lines_out).rstrip() + "\n", encoding="utf-8")
    print("Updated SHINOBI_* in .credentials.local")


def main() -> int:
    load_credentials()
    c = ssh_connect(MAS_VM)
    auto_pass: str | None = None
    try:
        st = ensure_super_token(c)
        print("Super API token length:", len(st))
        auto_pass = register_admin_if_needed(c, st)
        api_key, group_key = fetch_user_keys(c)
        print("Fetched DB key lengths:", len(api_key), len(group_key))
    finally:
        c.close()

    append_local_credentials(api_key, group_key, automation_pass=auto_pass)
    sync_sandbox_env(api_key, group_key)
    purge_cf()
    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
