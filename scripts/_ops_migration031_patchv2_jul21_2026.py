#!/usr/bin/env python3
"""Apply migration 031 on MINDEX 189 and deploy Patch v2 MAS on 188 (merge-only env)."""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import paramiko

ROOT = Path(__file__).resolve().parents[1]
CREDS = ROOT / ".credentials.local"
MIGRATION = ROOT / "migrations" / "031_personnel_screening_evidence_jul21_2026.sql"

MINDEX_HOST = "192.168.0.189"
MAS_HOST = "192.168.0.188"
MAS_CODE = "/home/mycosoft/mycosoft/mas"


def load_creds() -> None:
    if CREDS.exists():
        for line in CREDS.read_text(encoding="utf-8").splitlines():
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


def ssh_connect(host: str) -> paramiko.SSHClient:
    if host == MINDEX_HOST:
        user = os.environ.get("MINDEX_VM_USER", "root")
        password = os.environ.get("MINDEX_VM_PASSWORD") or os.environ.get("VM_PASSWORD")
    else:
        user = os.environ.get("MAS_VM_USER") or os.environ.get("VM_SSH_USER", "mycosoft")
        if user == "root" and host == MAS_HOST:
            user = "mycosoft"
        password = (
            os.environ.get("VM_PASSWORD")
            or os.environ.get("VM_SSH_PASSWORD")
            or os.environ.get("MAS_VM_PASSWORD")
        )
    if not password:
        raise SystemExit("Missing VM password in .credentials.local")
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(host, username=user, password=password, timeout=20)
    return client


def run(ssh: paramiko.SSHClient, cmd: str, timeout: int = 120) -> tuple[int, str, str]:
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode(errors="replace")
    err = stderr.read().decode(errors="replace")
    code = stdout.channel.recv_exit_status()
    return code, out, err


def apply_migration_031() -> bool:
    print("\n=== MINDEX 189: migration 031 ===")
    if not MIGRATION.exists():
        print(f"ERROR: migration file missing: {MIGRATION}")
        return False

    sql = MIGRATION.read_text(encoding="utf-8")
    ssh = ssh_connect(MINDEX_HOST)
    try:
        code, out, err = run(
            ssh,
            "docker ps --format '{{.Names}}' | grep -E 'postgres|mindex-postgres' | head -1",
        )
        container = out.strip().splitlines()[0] if out.strip() else ""
        if not container:
            code, out, err = run(ssh, "docker ps --format '{{.Names}}'")
            print("docker ps:\n", out)
            print("ERROR: postgres container not found")
            return False
        print(f"Postgres container: {container}")

        remote_path = "/tmp/031_personnel_screening_evidence_jul21_2026.sql"
        sftp = ssh.open_sftp()
        with sftp.file(remote_path, "w") as f:
            f.write(sql)
        sftp.close()

        # Idempotent apply via psql inside container
        psql_cmd = (
            f"docker exec -i {container} psql -U mycosoft -d mindex -v ON_ERROR_STOP=1 "
            f"-f {remote_path} 2>&1 || "
            f"cat {remote_path} | docker exec -i {container} psql -U mycosoft -d mindex -v ON_ERROR_STOP=1 2>&1"
        )
        # Copy file into container then run
        run(ssh, f"docker cp {remote_path} {container}:{remote_path}")
        code, out, err = run(
            ssh,
            f"docker exec {container} psql -U mycosoft -d mindex -v ON_ERROR_STOP=1 -f {remote_path}",
            timeout=180,
        )
        print(out)
        if err:
            print("stderr:", err)
        if code != 0:
            print(f"ERROR: psql exit {code}")
            return False

        verify_cmd = (
            f"docker exec {container} psql -U mycosoft -d mindex -tAc "
            "\"SELECT COUNT(*) FROM information_schema.tables "
            "WHERE table_schema='soc_ops' AND table_name IN "
            "('ps_subject','ps_screening_event','ssp_evidence','compliance_audit_log');\""
        )
        code, out, err = run(ssh, verify_cmd)
        table_count = out.strip()
        print(f"soc_ops evidence tables present: {table_count}/4")

        code, out, err = run(
            ssh,
            f"docker exec {container} psql -U mycosoft -d mindex -tAc "
            "'SELECT COUNT(*) FROM soc_ops.ps_screening_event;'",
        )
        print(f"ps_screening_event rows: {out.strip()}")
        return table_count == "4"
    finally:
        ssh.close()


def deploy_mas_patch_v2() -> bool:
    print("\n=== MAS 188: Patch v2 deploy (merge-only env) ===")
    ssh = ssh_connect(MAS_HOST)
    try:
        code, out, err = run(
            ssh,
            f"cd {MAS_CODE} && git fetch origin && git reset --hard origin/main && git log -1 --oneline",
            timeout=120,
        )
        print(out or err)
        if code != 0:
            print("ERROR: git pull failed")
            return False

        # Verify router file on VM
        code, out, err = run(
            ssh,
            f"test -f {MAS_CODE}/mycosoft_mas/core/routers/security_evidence_api.py && echo present",
        )
        if "present" not in out:
            print("ERROR: security_evidence_api.py not on VM after pull")
            return False
        print("security_evidence_api.py: present on VM")

        # Detect orchestrator runtime
        code, out, err = run(ssh, "systemctl is-active mas-orchestrator 2>/dev/null || echo inactive")
        systemd_active = out.strip() == "active"
        code, out, err = run(ssh, "docker ps --format '{{.Names}}' | grep -E 'myca-orchestrator|mas-orchestrator' || true")
        docker_name = out.strip().splitlines()[0] if out.strip() else ""

        if systemd_active:
            print("Restart via systemd mas-orchestrator (preserves /etc/mycosoft/mas-compliance.env)")
            code, out, err = run(
                ssh,
                "echo $VM_PASSWORD | sudo -S systemctl restart mas-orchestrator 2>&1",
                timeout=120,
            )
            # sudo may need password from env on VM - try without if fails
            if code != 0:
                code, out, err = run(ssh, "sudo systemctl restart mas-orchestrator 2>&1", timeout=120)
            print(out or err)
        elif docker_name:
            print(f"Restart via docker rebuild: {docker_name}")
            run(ssh, f"docker rm -f {docker_name} 2>/dev/null || true")
            # Preserve env from existing container inspect if possible
            code, out, err = run(
                ssh,
                f"""cd {MAS_CODE} && docker build -t mycosoft/mas-agent:latest . 2>&1 | tail -20""",
                timeout=1800,
            )
            print(out[-2000:] if len(out) > 2000 else out)
            # Use env-file merge: repo .env + compliance env if present
            env_flags = ""
            for ef in [f"{MAS_CODE}/.env", "/etc/mycosoft/mas-compliance.env"]:
                code2, out2, _ = run(ssh, f"test -f {ef} && echo yes")
                if "yes" in out2:
                    env_flags += f" --env-file {ef}"
            run_cmd = (
                f"docker run -d --name {docker_name} --restart unless-stopped "
                f"-p 8001:8000 {env_flags} mycosoft/mas-agent:latest"
            )
            code, out, err = run(ssh, run_cmd, timeout=120)
            print(out or err)
        else:
            print("Trying systemd restart as fallback")
            run(ssh, "sudo systemctl restart mas-orchestrator 2>&1")

        print("Waiting 15s for orchestrator...")
        time.sleep(15)
        return True
    finally:
        ssh.close()


def probe_routes() -> dict:
    import urllib.error
    import urllib.request

    routes = {
        "screening_events": "http://192.168.0.188:8001/api/security/ps/screening-events",
        "compliance_score": "http://192.168.0.188:8001/api/compliance/score",
        "compliance_health": "http://192.168.0.188:8001/api/compliance/health",
        "evidence_emit": "http://192.168.0.188:8001/api/security/evidence/emit",
    }
    results: dict = {}
    for name, url in routes.items():
        try:
            req = urllib.request.Request(url, method="GET" if "emit" not in name else "POST")
            with urllib.request.urlopen(req, timeout=15) as resp:
                body = resp.read(500).decode(errors="replace")
                results[name] = {"status": resp.status, "body_preview": body[:200]}
        except urllib.error.HTTPError as e:
            results[name] = {"status": e.code, "body_preview": e.read(200).decode(errors="replace")}
        except Exception as e:
            results[name] = {"status": "error", "body_preview": str(e)}
    return results


def main() -> int:
    load_creds()
    mig_ok = apply_migration_031()
    deploy_ok = deploy_mas_patch_v2()
    print("\n=== Route probes ===")
    probes = probe_routes()
    for k, v in probes.items():
        print(f"  {k}: HTTP {v['status']} — {v['body_preview'][:120]}")

    score = probes.get("compliance_score", {})
    score_ok = isinstance(score.get("status"), int) and score["status"] == 200
    if score_ok and "implementation_percent" in score.get("body_preview", ""):
        import json

        try:
            data = json.loads(score["body_preview"])
            score_ok = data.get("implementation_percent", 0) > 0
            print(f"  score implementation_percent: {data.get('implementation_percent')}")
        except Exception:
            pass

    print("\n=== SUMMARY ===")
    print(f"migration_031: {'Y' if mig_ok else 'N'}")
    print(f"patch_v2_deploy: {'Y' if deploy_ok else 'N'}")
    print(f"score_ok: {'Y' if score_ok else 'N'}")
    return 0 if mig_ok and deploy_ok and score_ok else 1


if __name__ == "__main__":
    sys.exit(main())
