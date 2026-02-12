#!/usr/bin/env python3
"""
VM deployment verification and cleanup. Uses credentials from .credentials.local.
Run from MAS repo root: python scripts/vm_verify_and_cleanup.py
"""
import os
import sys
from pathlib import Path

# Load credentials from .credentials.local (MAS repo root)
def load_credentials():
    root = Path(__file__).resolve().parent.parent
    for p in [root / ".credentials.local", Path.home() / ".mycosoft-credentials"]:
        if p.exists():
            for line in p.read_text().splitlines():
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ[k.strip()] = v.strip()
            break
    return os.environ.get("VM_SSH_PASSWORD") or os.environ.get("VM_PASSWORD")


def ssh_run(client, cmd, timeout=60):
    stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode("utf-8", errors="replace").strip()
    err = stderr.read().decode("utf-8", errors="replace").strip()
    return out, err


def main():
    password = load_credentials()
    if not password:
        print("ERROR: VM_SSH_PASSWORD not set. Create .credentials.local with VM_SSH_PASSWORD=...")
        sys.exit(1)

    user = os.environ.get("VM_SSH_USER", "mycosoft")
    vms = [
        ("187", "192.168.0.187", "Sandbox (website)"),
        ("188", "192.168.0.188", "MAS (orchestrator)"),
        ("189", "192.168.0.189", "MINDEX (DB)"),
    ]

    try:
        import paramiko
    except ImportError:
        print("Install paramiko: poetry add --group dev paramiko")
        sys.exit(1)

    for label, host, role in vms:
        print("\n" + "=" * 60)
        print(f"VM {label} ({host}) - {role}")
        print("=" * 60)
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            client.connect(host, username=user, password=password, timeout=15)
        except Exception as e:
            print(f"  SSH failed: {e}")
            continue

        if label == "187":
            out, _ = ssh_run(client, "docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}' 2>/dev/null")
            print(out or "(no docker or no containers)")
            code, _ = ssh_run(client, "curl -s -o /dev/null -w '%{http_code}' http://localhost:3000 2>/dev/null || echo 000")
            print(f"  Website (3000): HTTP {code}")
            # Start website container if not running (with NAS mount)
            if code != "200" and "200" not in str(code):
                out, _ = ssh_run(client, "docker ps -a --format '{{.Names}} {{.Status}}' 2>/dev/null")
                if "mycosoft-website" in out and "Up" not in out:
                    print("  Starting existing container mycosoft-website...")
                    ssh_run(client, "docker start mycosoft-website 2>/dev/null")
                elif "mycosoft-website" not in out:
                    img_out, _ = ssh_run(client, "docker images --format '{{.Repository}}:{{.Tag}}' 2>/dev/null | grep -E 'website|mycosoft' | head -1")
                    img = (img_out or "mycosoft-always-on-mycosoft-website:latest").strip()
                    run_cmd = (
                        f"docker run -d --name mycosoft-website -p 3000:3000 "
                        f"-v /opt/mycosoft/media/website/assets:/app/public/assets:ro "
                        f"--restart unless-stopped {img} 2>&1"
                    )
                    start_out, start_err = ssh_run(client, run_cmd)
                    if start_out and ("Error" in start_out or "No such image" in start_out):
                        print(f"  Could not start: {start_out[:200]}")
                    else:
                        print(f"  Started website container (image {img})")
            # Optional: /opt/mycosoft/mas
            out, _ = ssh_run(client, "test -d /opt/mycosoft/mas && (cd /opt/mycosoft/mas && git status --short 2>/dev/null | head -3) || echo 'dir missing or not a repo'")
            print(f"  /opt/mycosoft/mas: {out or 'ok'}")
        elif label == "188":
            out, _ = ssh_run(client, "curl -s http://localhost:8001/health 2>/dev/null || echo '{}'")
            print(f"  MAS health: {out[:200]}")
            out, _ = ssh_run(client, "docker ps --format '{{.Names}}\t{{.Status}}' 2>/dev/null | grep -E 'myca|mas' || true")
            print(f"  MAS container: {out or 'n/a'}")
        elif label == "189":
            out, _ = ssh_run(client, "docker ps --format 'table {{.Names}}\t{{.Status}}' 2>/dev/null")
            print(out or "(no docker)")
            out, _ = ssh_run(client, "docker exec -i $(docker ps -q -f name=postgres 2>/dev/null | head -1) pg_isready -U postgres 2>/dev/null || echo 'postgres not ready'")
            print(f"  PostgreSQL: {out.strip() or 'n/a'}")

        client.close()

    print("\n" + "=" * 60)
    print("Verification done.")
    print("=" * 60)


if __name__ == "__main__":
    main()
