#!/usr/bin/env python3
"""
Full MYCA deployment to VM 191 — Clone, setup, migrate, deploy .env, start services.

Runs from dev machine. Uses paramiko for password-based SSH.
Loads credentials from .env, .credentials.local, ~/.mycosoft-credentials.

Usage:
    python scripts/deploy_myca_191_full.py
    python scripts/deploy_myca_191_full.py --env-only   # Only push .env and restart
"""

import io
import os
import sys
from pathlib import Path

# Add repo root to path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))


def load_credentials() -> dict:
    """Load from .env, .credentials.local, ~/.mycosoft-credentials. Later sources override earlier."""
    creds = {}
    for f in [
        REPO_ROOT / ".env",
        REPO_ROOT / ".credentials.local",
        Path.home() / ".mycosoft-credentials",
    ]:
        if f.exists():
            for line in f.read_text().splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    creds[k.strip()] = v.strip()
    return creds


def build_myca_env(creds: dict) -> str:
    """Build /opt/myca/.env content from template + credentials."""
    template = (REPO_ROOT / "deploy" / "myca_os.env.template").read_text(encoding="utf-8")
    import re

    # (cred_key, env_var) — one cred can map to multiple env vars via duplicate ckey
    mapping: list[tuple[str, str]] = [
        ("MINDEX_DB_PASSWORD", "MINDEX_PG_PASSWORD"),
        ("MINDEX_PG_PASSWORD", "MINDEX_PG_PASSWORD"),
        ("N8N_API_KEY", "MYCA_N8N_API_KEY"),
        ("MAS_N8N_API_KEY", "MAS_N8N_API_KEY"),
        ("ANTHROPIC_API_KEY", "ANTHROPIC_API_KEY"),
        ("OPENAI_API_KEY", "OPENAI_API_KEY"),
        ("GITHUB_TOKEN", "GITHUB_TOKEN"),
        # Discord — set both so channels_health and DiscordClient find it
        ("DISCORD_BOT_TOKEN", "DISCORD_BOT_TOKEN"),
        ("DISCORD_BOT_TOKEN", "MYCA_DISCORD_TOKEN"),
        ("MYCA_DISCORD_TOKEN", "DISCORD_BOT_TOKEN"),
        ("MYCA_DISCORD_TOKEN", "MYCA_DISCORD_TOKEN"),
        ("DISCORD_WEBHOOK_URL", "DISCORD_WEBHOOK_URL"),
        ("DISCORD_MYCA_WEBHOOK", "DISCORD_WEBHOOK_URL"),
        ("MORGAN_DISCORD_ID", "MORGAN_DISCORD_ID"),
        # Slack — channels_health checks SLACK_APP_TOKEN, MYCA_SLACK_APP_TOKEN, SLACK_OAUTH_TOKEN, MYCA_SLACK_BOT_TOKEN
        ("SLACK_BOT_TOKEN", "SLACK_BOT_TOKEN"),
        ("SLACK_BOT_TOKEN", "MYCA_SLACK_BOT_TOKEN"),
        ("SLACK_APP_TOKEN", "SLACK_APP_TOKEN"),
        ("SLACK_APP_TOKEN", "MYCA_SLACK_APP_TOKEN"),
        ("SLACK_OAUTH_TOKEN", "SLACK_OAUTH_TOKEN"),
        ("SLACK_OAUTH_TOKEN", "SLACK_BOT_TOKEN"),
        ("MYCA_SLACK_BOT_TOKEN", "SLACK_BOT_TOKEN"),
        ("MYCA_SLACK_BOT_TOKEN", "MYCA_SLACK_BOT_TOKEN"),
        ("MYCA_SLACK_APP_TOKEN", "SLACK_APP_TOKEN"),
        ("MYCA_SLACK_APP_TOKEN", "MYCA_SLACK_APP_TOKEN"),
        # Asana
        ("ASANA_PAT", "ASANA_PAT"),
        ("ASANA_ACCESS_TOKEN", "ASANA_PAT"),
        ("ASANA_API_KEY", "ASANA_PAT"),
        ("MYCA_ASANA_TOKEN", "ASANA_PAT"),
        ("ASANA_WORKSPACE_ID", "ASANA_WORKSPACE_ID"),
        # Signal — channels_health checks MYCA_SIGNAL_NUMBER, SIGNAL_SENDER_NUMBER
        ("SIGNAL_SENDER_NUMBER", "SIGNAL_SENDER_NUMBER"),
        ("SIGNAL_SENDER_NUMBER", "MYCA_SIGNAL_NUMBER"),
        ("MYCA_SIGNAL_NUMBER", "SIGNAL_SENDER_NUMBER"),
        ("MYCA_SIGNAL_NUMBER", "MYCA_SIGNAL_NUMBER"),
        ("SIGNAL_API_URL", "SIGNAL_API_URL"),
        ("MYCA_SIGNAL_CLI_URL", "MYCA_SIGNAL_CLI_URL"),
        ("MORGAN_SIGNAL_NUMBER", "MORGAN_SIGNAL_NUMBER"),
        # WhatsApp / Evolution API
        ("WHATSAPP_API_URL", "WHATSAPP_API_URL"),
        ("MYCA_EVOLUTION_API_URL", "MYCA_EVOLUTION_API_URL"),
        ("MYCA_WHATSAPP_INSTANCE", "MYCA_WHATSAPP_INSTANCE"),
        ("MORGAN_WHATSAPP_NUMBER", "MORGAN_WHATSAPP_NUMBER"),
        # Email
        ("SMTP_USER", "SMTP_USER"),
        ("SMTP_PASSWORD", "SMTP_PASSWORD"),
        ("IMAP_USER", "IMAP_USER"),
        ("IMAP_PASSWORD", "IMAP_PASSWORD"),
        ("NOTION_API_KEY", "NOTION_API_KEY"),
    ]
    for ckey, evar in mapping:
        if evar and ckey in creds and creds[ckey]:
            val = creds[ckey]
            template = re.sub(
                rf"^({re.escape(evar)}=).*$",
                lambda m, v=val: m.group(1) + v,
                template,
                flags=re.MULTILINE,
            )
    return template


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--env-only", action="store_true", help="Only push .env and restart myca-os")
    args = ap.parse_args()

    creds = load_credentials()
    password = creds.get("VM_SSH_PASSWORD") or creds.get("VM_PASSWORD") or os.environ.get("VM_PASSWORD")
    if not password:
        print("ERROR: VM_SSH_PASSWORD or VM_PASSWORD not found in .env / .credentials.local / ~/.mycosoft-credentials")
        sys.exit(1)

    try:
        import paramiko
    except ImportError:
        print("Install paramiko: pip install paramiko")
        sys.exit(1)

    VM = "192.168.0.191"
    USER = creds.get("VM_SSH_USER", "mycosoft")
    REPO_PATH = "/home/mycosoft/repos/mycosoft-mas"

    print("Connecting to VM 191...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh.connect(VM, username=USER, password=password, timeout=30)
    except Exception as e:
        print(f"SSH failed: {e}")
        sys.exit(1)

    def run(cmd: str, check: bool = True) -> tuple[int, str, str]:
        _, stdout, stderr = ssh.exec_command(cmd, timeout=120)
        out = stdout.read().decode()
        err = stderr.read().decode()
        code = stdout.channel.recv_exit_status()
        if check and code != 0:
            print(f"  FAILED: {cmd}")
            print(f"  stderr: {err[:500]}")
        return code, out, err

    if args.env_only:
        print("\n[env-only] Pushing .env and restarting...")
        run("sudo mkdir -p /opt/myca/{logs,data,backups} && sudo chown -R mycosoft:mycosoft /opt/myca")
        env_content = build_myca_env(creds)
        sftp = ssh.open_sftp()
        try:
            sftp.putfo(io.BytesIO(env_content.encode("utf-8")), "/opt/myca/.env")
        finally:
            sftp.close()
        run("sudo systemctl restart myca-os 2>/dev/null || true")
        run("sleep 2")
        code, out, _ = run("curl -s http://localhost:8000/channels 2>/dev/null | head -c 500", check=False)
        print(f"\n  Channels response: {out[:300] if out else '(empty)'}...")
        ssh.close()
        print("\n  Done. Verify: curl http://192.168.0.191:8000/channels")
        return

    print("\n[1/8] Creating directories...")
    run("sudo mkdir -p /opt/myca/{logs,data,backups} && sudo chown -R mycosoft:mycosoft /opt/myca")
    run("mkdir -p /home/mycosoft/repos /home/mycosoft/documents /home/mycosoft/downloads")

    print("\n[2/8] Cloning/pulling repo...")
    code, out, _ = run(f"test -d {REPO_PATH} && cd {REPO_PATH} && git fetch origin && git checkout main && git pull origin main", check=False)
    if code != 0:
        run(f"cd /home/mycosoft/repos && git clone https://github.com/MycosoftLabs/mycosoft-mas.git 2>/dev/null || git clone https://github.com/mycosoft/mas.git mycosoft-mas 2>/dev/null || true")
        run(f"test -d {REPO_PATH} && cd {REPO_PATH} && git pull origin main", check=False)

    print("\n[3/8] Setting up Python venv...")
    # MAS requires Python >=3.11; try 3.12, 3.11, then python3
    py_cmd = "python3"
    for cand in ["python3.12", "python3.11", "python3"]:
        code, _, _ = run(f"which {cand} 2>/dev/null", check=False)
        if code == 0:
            vcode, _, _ = run(f"{cand} -c 'import sys; sys.exit(0 if sys.version_info >= (3,11) else 1)'", check=False)
            if vcode == 0:
                py_cmd = cand
                break
    if py_cmd == "python3":
        vcode, _, _ = run("python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3,11) else 1)'", check=False)
        if vcode != 0:
            print("  Installing Python 3.11 via deadsnakes...")
            run("sudo add-apt-repository -y ppa:deadsnakes/ppa", check=False)
            run("sudo apt-get update -qq", check=False)
            run("sudo apt-get install -y python3.11 python3.11-venv", check=False)
            code, _, _ = run("which python3.11 2>/dev/null", check=False)
            py_cmd = "python3.11" if code == 0 else py_cmd
    print(f"  Using: {py_cmd}")
    run(f"cd {REPO_PATH} && {py_cmd} -m venv .venv 2>/dev/null || true")
    run(f"cd {REPO_PATH} && .venv/bin/pip install -q -e . 2>/dev/null || .venv/bin/pip install -q -e .")
    run(f"cd {REPO_PATH} && .venv/bin/pip install -q aiohttp asyncpg redis playwright 2>/dev/null || true")

    print("\n[4/8] Deploying .env...")
    env_content = build_myca_env(creds)
    # Use SFTP to avoid shell escaping issues with special chars in .env
    sftp = ssh.open_sftp()
    try:
        sftp.putfo(io.BytesIO(env_content.encode("utf-8")), "/opt/myca/.env")
    finally:
        sftp.close()

    print("\n[5/8] Deploying systemd service...")
    run(f"sudo cp {REPO_PATH}/deploy/myca-os.service /etc/systemd/system/myca-os.service 2>/dev/null || true")
    run("sudo systemctl daemon-reload 2>/dev/null || true")

    print("\n[6/8] Running migration on MINDEX 189...")
    mig_file = REPO_ROOT / "migrations" / "005_myca_os_tables.sql"
    if mig_file.exists():
        pg_pass = creds.get("MINDEX_PG_PASSWORD") or creds.get("MINDEX_DB_PASSWORD") or os.environ.get("MINDEX_DB_PASSWORD")
        if pg_pass:
            # Use .pgpass via SFTP to avoid shell-escaping the password
            def escape_pgpass(p: str) -> str:
                return p.replace("\\", "\\\\").replace(":", "\\:")
            pgpass_line = f"192.168.0.189:5432:mycosoft_mas:mycosoft:{escape_pgpass(pg_pass)}\n"
            sftp = ssh.open_sftp()
            try:
                sftp.putfo(io.BytesIO(pgpass_line.encode("utf-8")), "/tmp/.pgpass")
            finally:
                sftp.close()
            run("chmod 600 /tmp/.pgpass")
            code, out, err = run(
                f"PGPASSFILE=/tmp/.pgpass psql -h 192.168.0.189 -p 5432 -U mycosoft -d mycosoft_mas -f {REPO_PATH}/migrations/005_myca_os_tables.sql 2>&1",
                check=False,
            )
            run("rm -f /tmp/.pgpass")
            if code != 0:
                print("  Migration failed or psql not installed (install postgresql-client if needed)")
            else:
                print("  Migration applied")
        else:
            print("  Migration skipped (MINDEX_PG_PASSWORD not set)")
    else:
        print("  Migration file not found, skipping")

    print("\n[7/8] Stopping old MYCA OS...")
    run("sudo systemctl stop myca-os 2>/dev/null || true")
    run("tmux kill-session -t myca-os 2>/dev/null || true")

    print("\n[8/8] Starting MYCA OS...")
    run(f"sudo systemctl enable myca-os 2>/dev/null || true")
    code, _, _ = run("sudo systemctl start myca-os", check=False)
    if code != 0:
        # Fallback to tmux
        print("  systemd failed, using tmux...")
        run(f"tmux new-session -d -s myca-os 'cd {REPO_PATH} && .venv/bin/python -m mycosoft_mas.myca.os 2>&1 | tee -a /opt/myca/logs/myca_os.log'")

    # Verify
    run("sleep 3")
    code, out, _ = run("sudo systemctl is-active myca-os 2>/dev/null || tmux has-session -t myca-os 2>/dev/null && echo active || echo inactive", check=False)
    status = "active" if "active" in out or "RUNNING" in str(out) else "unknown"
    print(f"\n  MYCA OS status: {status}")

    ssh.close()
    print("\n" + "=" * 50)
    print("Deployment complete. MYCA OS should be running on VM 191.")
    print("  Logs: /opt/myca/logs/myca_os.log")
    print("  Attach: ssh mycosoft@192.168.0.191 -t 'tmux attach -t myca-os'")
    print("=" * 50)


if __name__ == "__main__":
    main()
