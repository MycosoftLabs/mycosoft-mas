#!/usr/bin/env python3
"""
MYCA2 rollout on VMs: apply MINDEX 0023 on 189, redeploy MINDEX API, MAS 188, optional website 187.
Requires: .credentials.local with VM_PASSWORD; git pushed to origin/main for each repo.

Usage:
  python scripts/myca2_vm_rollout.py --migrate-only
  python scripts/myca2_vm_rollout.py --mindex
  python scripts/myca2_vm_rollout.py --mas
  python scripts/myca2_vm_rollout.py --all
  python scripts/myca2_vm_rollout.py --test
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CREDS = os.path.join(REPO_ROOT, ".credentials.local")
MINDEX_SQL = os.path.normpath(
    os.path.join(REPO_ROOT, "..", "..", "MINDEX", "mindex", "migrations", "0023_myca2_psilo_registry.sql")
)


def load_creds():
    if os.path.isfile(CREDS):
        for line in open(CREDS).read().splitlines():
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ[k.strip()] = v.strip()
    pw = os.environ.get("VM_SSH_PASSWORD") or os.environ.get("VM_PASSWORD")
    if not pw:
        print("ERROR: VM_PASSWORD in .credentials.local")
        sys.exit(1)
    return pw


def ssh_run(client, cmd: str) -> tuple[int, str, str]:
    stdin, stdout, stderr = client.exec_command(cmd, get_pty=True)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    return stdout.channel.recv_exit_status(), out, err


def sudo_run(client, password: str, remote_bash: str) -> tuple[int, str, str]:
    """Run bash on remote as root (VM sudo password same as SSH)."""
    cmd = f"sudo -S bash -c {repr(remote_bash)}"
    stdin, stdout, stderr = client.exec_command(cmd, get_pty=True)
    stdin.write(password + "\n")
    try:
        stdin.flush()
    except Exception:
        pass
    try:
        stdin.channel.shutdown_write()
    except Exception:
        pass
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    return stdout.channel.recv_exit_status(), out, err


def free_mas_port_188(client, password: str) -> None:
    """Stop host mas-orchestrator so Docker can bind 8001:8000."""
    c, o, e = sudo_run(client, password, "systemctl stop mas-orchestrator 2>/dev/null; exit 0")
    if o.strip():
        print(o.strip())
    if e.strip() and "password" not in e.lower() and "sorry" not in e.lower():
        print(e.strip())
    time.sleep(3)


def migrate_189(password: str) -> bool:
    import paramiko

    if not os.path.isfile(MINDEX_SQL):
        print(f"ERROR: migration file not found: {MINDEX_SQL}")
        return False

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect("192.168.0.189", username="mycosoft", password=password, timeout=45)

    c, o, e = ssh_run(
        client,
        "cd /home/mycosoft/mindex && git fetch origin && git reset --hard origin/main",
    )
    print(o or e)

    remote_sql = "/tmp/myca2_0023_psilo.sql"
    sftp = client.open_sftp()
    sftp.put(MINDEX_SQL, remote_sql)
    sftp.close()

    c, o, e = ssh_run(
        client,
        f"cat {remote_sql} | docker exec -i mindex-postgres psql -U mindex -d mindex -v ON_ERROR_STOP=1",
    )
    print("=== psql 0023 ===")
    print(o or e)
    client.close()
    return c == 0


def deploy_mindex():
    r = subprocess.run(
        [sys.executable, os.path.join(REPO_ROOT, "_deploy_mindex_vm.py")],
        cwd=REPO_ROOT,
    )
    return r.returncode == 0


def deploy_mas(password: str) -> bool:
    import paramiko

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect("192.168.0.188", username="mycosoft", password=password, timeout=120)

    mas_dir = "/home/mycosoft/mycosoft/mas"
    c, o, e = ssh_run(
        client,
        "test -d /opt/mycosoft/mas && echo /opt/mycosoft/mas || echo /home/mycosoft/mycosoft/mas",
    )
    if c == 0 and (o or "").strip():
        mas_dir = (o or "").strip().splitlines()[-1].strip()

    c, o, e = ssh_run(
        client,
        f"cd {mas_dir} && git fetch origin && git reset --hard origin/main && git log -1 --oneline",
    )
    print(o or e)
    if c != 0:
        client.close()
        return False

    free_mas_port_188(client, password)

    c, o, e = ssh_run(client, f"cd {mas_dir} && docker build -t mycosoft/mas-agent:latest .")
    print((o or e)[-8000:] if len(o or e) > 8000 else (o or e))
    if c != 0:
        client.close()
        return False

    ssh_run(client, "docker rm -f myca-orchestrator-new 2>/dev/null || true")

    env_file_opt = ""
    c2, o2, _ = ssh_run(client, f"test -f {mas_dir}/.env && echo yes || echo no")
    if "yes" in (o2 or ""):
        env_file_opt = f"--env-file {mas_dir}/.env "

    run_cmd = (
        "docker run -d --name myca-orchestrator-new --restart unless-stopped "
        f"{env_file_opt}"
        "-e MINDEX_API_URL=http://192.168.0.189:8000 "
        "-p 8001:8000 mycosoft/mas-agent:latest"
    )
    c, o, e = ssh_run(client, run_cmd)
    print(o or e)
    if c != 0:
        print(f"docker run exit {c}: {e}")
        client.close()
        return False
    client.close()
    time.sleep(45)
    return True


def _mas_base() -> str:
    """MAS base URL: MAS_API_URL env, or probe 188:8001/8000."""
    env = (os.environ.get("MAS_API_URL") or "").rstrip("/")
    if env:
        return env
    import urllib.request

    for port in (8001, 8000):
        u = f"http://192.168.0.188:{port}/health"
        try:
            urllib.request.urlopen(u, timeout=8)
            return f"http://192.168.0.188:{port}"
        except Exception:
            continue
    return "http://192.168.0.188:8001"


def _mindex_health_url() -> str:
    base = (os.environ.get("MINDEX_API_URL") or "http://192.168.0.189:8000").rstrip("/")
    return f"{base}/api/mindex/health"


def smoke_test() -> bool:
    """Validate MAS + MINDEX DB + PSILO session round-trip."""
    import json
    import urllib.error
    import urllib.request

    mas = _mas_base()
    mindex_health = _mindex_health_url()
    ok = True

    try:
        r = urllib.request.urlopen(f"{mas}/health", timeout=15)
        h = json.loads(r.read().decode())
        if h.get("status") not in ("healthy", "ok", None) and "status" in h:
            if str(h.get("status", "")).lower() not in ("healthy", "ok"):
                print(f"WARN MAS health shape: {h}")
        print(f"OK MAS health: {h}")
    except Exception as ex:
        print(f"FAIL MAS health: {ex}")
        ok = False

    try:
        r = urllib.request.urlopen(mindex_health, timeout=15)
        mj = json.loads(r.read().decode())
        if mj.get("db") != "ok":
            print(f"FAIL MINDEX db not ok: {mj}")
            ok = False
        else:
            print(f"OK MINDEX health: db=ok service={mj.get('service')}")
    except Exception as ex:
        print(f"FAIL MINDEX health: {ex}")
        ok = False

    session_id = None
    try:
        req = urllib.request.Request(
            f"{mas}/api/plasticity/psilo/session/start",
            data=b'{"dose_profile":{},"phase_profile":{}}',
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        r = urllib.request.urlopen(req, timeout=45)
        body = json.loads(r.read().decode())
        session_id = body.get("session_id")
        if not session_id:
            print(f"FAIL PSILO start missing session_id: {body}")
            ok = False
        else:
            print(f"OK PSILO start: session_id={session_id}")
    except urllib.error.HTTPError as ex:
        print(f"FAIL PSILO start HTTP {ex.code}: {ex.read().decode()[:500]}")
        ok = False
    except Exception as ex:
        print(f"FAIL PSILO start: {ex}")
        ok = False

    if session_id:
        try:
            r = urllib.request.urlopen(
                f"{mas}/api/plasticity/psilo/session/{session_id}", timeout=15
            )
            st = json.loads(r.read().decode())
            print(f"OK PSILO GET session: keys={list(st.keys())[:8]}")
        except Exception as ex:
            print(f"FAIL PSILO GET session: {ex}")
            ok = False

    return ok


def main():
    load_creds()
    pw = os.environ.get("VM_SSH_PASSWORD") or os.environ.get("VM_PASSWORD")
    ap = argparse.ArgumentParser()
    ap.add_argument("--migrate-only", action="store_true")
    ap.add_argument("--mindex", action="store_true")
    ap.add_argument("--mas", action="store_true")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--test", action="store_true")
    args = ap.parse_args()

    if args.test:
        sys.exit(0 if smoke_test() else 1)

    if args.migrate_only:
        sys.exit(0 if migrate_189(pw) else 1)

    if args.all or args.mindex:
        if not migrate_189(pw):
            print("Migration failed; continue deploy? (mindex may error on new routes)")
        if not deploy_mindex():
            sys.exit(1)

    if args.all or args.mas:
        if not deploy_mas(pw):
            sys.exit(1)

    if args.all:
        print("Website: run WEBSITE _rebuild_sandbox.py + Cloudflare purge if plasticity proxy routes changed.")
        if not smoke_test():
            sys.exit(1)

    print("Done.")


if __name__ == "__main__":
    main()
