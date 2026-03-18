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
    c, o, e = ssh_run(
        client,
        "cd /home/mycosoft/mycosoft/mas && git fetch origin && git reset --hard origin/main && git log -1 --oneline",
    )
    print(o or e)
    if c != 0:
        client.close()
        return False
    c, o, e = ssh_run(
        client,
        "cd /home/mycosoft/mycosoft/mas && docker build -t mycosoft/mas-agent:latest .",
    )
    print((o or e)[-8000:] if len(o or e) > 8000 else (o or e))
    if c != 0:
        client.close()
        return False
    ssh_run(client, "docker rm -f myca-orchestrator-new 2>/dev/null || true")
    c, o, e = ssh_run(
        client,
        "docker run -d --name myca-orchestrator-new --restart unless-stopped "
        "--network host mycosoft/mas-agent:latest",
    )
    print(o or e)
    client.close()
    time.sleep(20)
    return c == 0


def smoke_test():
    import urllib.request

    ok = True
    for url, name in [
        ("http://192.168.0.188:8001/health", "MAS health"),
        ("http://192.168.0.189:8000/api/mindex/health", "MINDEX health"),
        (
            "http://192.168.0.188:8001/api/plasticity/psilo/session/start",
            "PSILO start (POST)",
        ),
    ]:
        try:
            if "POST" in name:
                req = urllib.request.Request(
                    url,
                    data=b'{"dose_profile":{},"phase_profile":{}}',
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                r = urllib.request.urlopen(req, timeout=30)
                body = r.read().decode()[:500]
            else:
                r = urllib.request.urlopen(url, timeout=10)
                body = r.read().decode()[:200]
            print(f"OK {name}: {body}")
        except Exception as ex:
            print(f"FAIL {name}: {ex}")
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
        print("Website: run WEBSITE _rebuild_sandbox.py + Cloudflare purge separately.")
        smoke_test()

    print("Done.")


if __name__ == "__main__":
    main()
