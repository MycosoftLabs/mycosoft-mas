#!/usr/bin/env python3
"""
MYCA VM 191 — Full deployment v2: Gateway, desktop tools, noVNC, skills.

Extends deploy_myca_191_full.py with:
- Gateway on port 8100 (HTTP/WS)
- Desktop tools: xdotool, scrot
- noVNC + x11vnc for watching MYCA work
- Skills directory + built-in skills
- discord.py, aioimaplib for comms

Usage:
    python scripts/deploy_myca_191_v2.py
"""

import io
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))


def load_creds():
    creds = {}
    for f in [REPO_ROOT / ".credentials.local", Path.home() / ".mycosoft-credentials"]:
        if f.exists():
            for line in f.read_text().splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    creds[k.strip()] = v.strip()
            break
    return creds


def main():
    creds = load_creds()
    password = creds.get("VM_SSH_PASSWORD") or creds.get("VM_PASSWORD") or os.environ.get("VM_PASSWORD")
    if not password:
        print("ERROR: VM_SSH_PASSWORD or VM_PASSWORD not found in .credentials.local")
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

    def run(cmd: str, check: bool = True) -> tuple:
        _, stdout, stderr = ssh.exec_command(cmd, timeout=120)
        out = stdout.read().decode()
        err = stderr.read().decode()
        code = stdout.channel.recv_exit_status()
        if check and code != 0:
            print(f"  FAILED: {cmd[:80]}...")
            print(f"  stderr: {err[:500]}")
        return code, out, err

    # Run base deployment
    print("\n[0] Running base deployment...")
    code = os.system(f'python "{REPO_ROOT / "scripts" / "deploy_myca_191_full.py"}"')
    if code != 0:
        print("Base deployment had issues; continuing with v2 extras...")

    # SSH stays open; base deploy ran in subprocess. Ensure connection is active.
    try:
        if not ssh.get_transport() or not ssh.get_transport().is_active():
            ssh.connect(VM, username=USER, password=password, timeout=30)
    except Exception:
        ssh.connect(VM, username=USER, password=password, timeout=30)

    # OpenWork / OpenCode setup (Phase 1: MYCA OpenWork Integration)
    print("\n[0b] OpenWork setup (Node.js check, openwork-orchestrator, opencode.json)...")
    run("node -v 2>/dev/null | grep -q 'v2[0-9]\\|v1[89]' || (curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash - && sudo apt-get install -y nodejs)", check=False)
    run("npm install -g openwork-orchestrator 2>/dev/null || true", check=False)
    run("mkdir -p /home/mycosoft/myca-workspace && sudo chown -R mycosoft:mycosoft /home/mycosoft/myca-workspace", check=False)
    run(f"cp -f {REPO_PATH}/mycosoft_mas/myca/config/opencode.json /home/mycosoft/myca-workspace/ 2>/dev/null || true", check=False)
    run("ls -la /home/mycosoft/myca-workspace/opencode.json 2>/dev/null || echo 'opencode.json deploy skipped (run git pull first)'", check=False)

    print("\n[1] Installing desktop tools (xdotool, scrot)...")
    run("sudo apt-get update -qq && sudo apt-get install -y xdotool scrot", check=False)

    print("\n[2] Installing noVNC + x11vnc...")
    run("sudo apt-get install -y novnc websockify x11vnc", check=False)

    print("\n[3] Creating skills directory...")
    run("mkdir -p /opt/myca/skills && sudo chown -R mycosoft:mycosoft /opt/myca")

    print("\n[4] Installing Python deps (discord.py, aioimaplib)...")
    run(f"cd {REPO_PATH} && .venv/bin/pip install -q discord.py aioimaplib 2>/dev/null || true", check=False)

    print("\n[5] Ensuring gateway security, runtime env, and Ollama fallback...")
    # Gateway is started by MYCA OS; ensure systemd service has MYCA_GATEWAY_PORT
    run("grep -q MYCA_GATEWAY_PORT /opt/myca/.env 2>/dev/null || echo 'MYCA_GATEWAY_PORT=8100' | sudo tee -a /opt/myca/.env", check=False)
    run("grep -q MYCA_ENABLE_SHELL_API /opt/myca/.env 2>/dev/null || echo 'MYCA_ENABLE_SHELL_API=false' | sudo tee -a /opt/myca/.env", check=False)
    run("grep -q MYCA_ENABLE_SKILL_INSTALL /opt/myca/.env 2>/dev/null || echo 'MYCA_ENABLE_SKILL_INSTALL=false' | sudo tee -a /opt/myca/.env", check=False)
    run("grep -q MYCA_ENABLE_PERSONAL_AGENCY /opt/myca/.env 2>/dev/null || echo 'MYCA_ENABLE_PERSONAL_AGENCY=true' | sudo tee -a /opt/myca/.env", check=False)
    run("grep -q MYCA_PERSONAL_AGENCY_MAX_PENDING /opt/myca/.env 2>/dev/null || echo 'MYCA_PERSONAL_AGENCY_MAX_PENDING=2' | sudo tee -a /opt/myca/.env", check=False)
    run("grep -q MYCA_TRUSTED_IPS /opt/myca/.env 2>/dev/null || echo 'MYCA_TRUSTED_IPS=127.0.0.1,::1,192.168.0.191,192.168.0.188' | sudo tee -a /opt/myca/.env", check=False)
    run("grep -q MYCA_GATEWAY_API_KEY /opt/myca/.env 2>/dev/null || (echo -n 'MYCA_GATEWAY_API_KEY=' | sudo tee -a /opt/myca/.env >/dev/null && openssl rand -hex 32 | sudo tee -a /opt/myca/.env >/dev/null)", check=False)
    # Phase 4: Ollama fallback for llm_brain when Claude API fails (MAS VM 188)
    run("grep -q OLLAMA_URL /opt/myca/.env 2>/dev/null || echo 'OLLAMA_URL=http://192.168.0.188:11434' | sudo tee -a /opt/myca/.env", check=False)
    run("grep -q OLLAMA_MODEL /opt/myca/.env 2>/dev/null || echo 'OLLAMA_MODEL=llama3.1:8b' | sudo tee -a /opt/myca/.env", check=False)
    run("grep -q NATUREOS_API_URL /opt/myca/.env 2>/dev/null || echo 'NATUREOS_API_URL=http://192.168.0.187:5000' | sudo tee -a /opt/myca/.env", check=False)
    run("grep -q PRESENCE_API_URL /opt/myca/.env 2>/dev/null || echo 'PRESENCE_API_URL=http://192.168.0.187:3000/api/presence' | sudo tee -a /opt/myca/.env", check=False)

    print("\n[6] Ensuring Evolution API (WhatsApp) container...")
    # Evolution API for WhatsApp — port 8083, instance 'myca'
    run(
        "docker ps -q -f name=evolution-api 2>/dev/null | grep -q . || "
        "(docker pull atendai/evolution-api:latest 2>/dev/null || true) && "
        "docker run -d --name evolution-api -p 8083:8080 --restart unless-stopped "
        "-e AUTHENTICATION_API_KEY=${MYCA_EVOLUTION_API_KEY:-$(openssl rand -hex 24)} "
        "atendai/evolution-api:latest 2>/dev/null || true",
        check=False,
    )

    print("\n[7] Restarting MYCA OS...")
    run("sudo systemctl restart myca-os 2>/dev/null || true", check=False)

    ssh.close()
    print("\n" + "=" * 50)
    print("MYCA v2 deployment complete.")
    print("  Gateway: http://192.168.0.191:8100/health")
    print("  noVNC:   http://192.168.0.191:6080 (if x11vnc + websockify running)")
    print("  CLI:     python scripts/myca_cli.py status --url http://192.168.0.191:8100")
    print("=" * 50)


if __name__ == "__main__":
    main()
