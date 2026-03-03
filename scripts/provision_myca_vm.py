"""
MYCA VM Provisioning Script

SSHes to the new MYCA VM (192.168.0.191) and configures it for the
OpenClaw/MYCA multi-platform architecture:
- Docker & Docker Compose
- Service user (myca)
- Directory structure for credentials, logs, config
- UFW firewall rules
- Caddy reverse proxy
- Deploys Cowork's docker-compose.myca-vm.yml

Usage:
    python scripts/provision_myca_vm.py [--dry-run] [--skip-docker-compose]

Requires:
    pip install paramiko
"""

import argparse
import asyncio
import logging
import os
import sys
import time
from pathlib import Path

try:
    import paramiko
except ImportError:
    print("paramiko required: pip install paramiko")
    sys.exit(1)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

MYCA_VM_IP = os.getenv("MYCA_VM_IP", "192.168.0.191")
MYCA_VM_USER = os.getenv("MYCA_VM_USER", "mycosoft")


def _load_credentials() -> str:
    """Load VM password from .credentials.local (never hardcode)."""
    creds_paths = [
        Path(__file__).parent.parent / ".credentials.local",
        Path.home() / ".mycosoft-credentials",
    ]
    for p in creds_paths:
        if p.exists():
            for line in p.read_text().splitlines():
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ.setdefault(key.strip(), value.strip())
            break

    password = os.environ.get("VM_PASSWORD") or os.environ.get("VM_SSH_PASSWORD", "")
    if not password:
        logger.error("No VM_PASSWORD found in .credentials.local or environment")
        sys.exit(1)
    return password


def _ssh_connect(password: str) -> paramiko.SSHClient:
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    logger.info("Connecting to MYCA VM at %s ...", MYCA_VM_IP)
    ssh.connect(MYCA_VM_IP, username=MYCA_VM_USER, password=password, timeout=30)
    logger.info("Connected.")
    return ssh


def _run(ssh: paramiko.SSHClient, cmd: str, sudo: bool = False,
         password: str = "", check: bool = True) -> tuple[int, str, str]:
    """Run a command on the remote VM via SSH."""
    if sudo:
        cmd = f"echo '{password}' | sudo -S bash -c '{cmd}'"
    logger.info("  >> %s", cmd[:120] + ("..." if len(cmd) > 120 else ""))
    stdin_, stdout_, stderr_ = ssh.exec_command(cmd, timeout=120)
    exit_code = stdout_.channel.recv_exit_status()
    out = stdout_.read().decode(errors="replace").strip()
    err = stderr_.read().decode(errors="replace").strip()
    if exit_code != 0 and check:
        logger.warning("  EXIT %d  stderr: %s", exit_code, err[:200])
    return exit_code, out, err


def provision(dry_run: bool = False, skip_compose: bool = False):
    password = _load_credentials()
    if dry_run:
        logger.info("[DRY RUN] Would connect to %s@%s and run provisioning", MYCA_VM_USER, MYCA_VM_IP)
        return

    ssh = _ssh_connect(password)
    try:
        _step_install_docker(ssh, password)
        _step_create_user(ssh, password)
        _step_create_dirs(ssh, password)
        _step_firewall(ssh, password)
        _step_install_caddy(ssh, password)
        if not skip_compose:
            _step_deploy_compose(ssh, password)
        _step_verify(ssh, password)
        logger.info("MYCA VM provisioning complete.")
    finally:
        ssh.close()


def _step_install_docker(ssh: paramiko.SSHClient, pw: str):
    logger.info("=== Step 1: Install Docker & Docker Compose ===")
    cmds = [
        "apt-get update -qq",
        "apt-get install -y -qq ca-certificates curl gnupg lsb-release",
        "install -m 0755 -d /etc/apt/keyrings",
        "curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc",
        "chmod a+r /etc/apt/keyrings/docker.asc",
        (
            'echo "deb [arch=$(dpkg --print-architecture) '
            'signed-by=/etc/apt/keyrings/docker.asc] '
            'https://download.docker.com/linux/ubuntu '
            '$(. /etc/os-release && echo $VERSION_CODENAME) stable" '
            '> /etc/apt/sources.list.d/docker.list'
        ),
        "apt-get update -qq",
        "apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin",
        "systemctl enable docker",
        "systemctl start docker",
    ]
    for cmd in cmds:
        _run(ssh, cmd, sudo=True, password=pw, check=False)
    code, out, _ = _run(ssh, "docker --version", check=False)
    logger.info("Docker version: %s", out)


def _step_create_user(ssh: paramiko.SSHClient, pw: str):
    logger.info("=== Step 2: Create service user 'myca' ===")
    _run(ssh, "id myca || useradd -r -m -s /bin/bash myca", sudo=True, password=pw, check=False)
    _run(ssh, "usermod -aG docker myca", sudo=True, password=pw, check=False)
    _run(ssh, f"usermod -aG docker {MYCA_VM_USER}", sudo=True, password=pw, check=False)


def _step_create_dirs(ssh: paramiko.SSHClient, pw: str):
    logger.info("=== Step 3: Create directory structure ===")
    dirs = [
        "/opt/myca",
        "/opt/myca/credentials/discord",
        "/opt/myca/credentials/slack",
        "/opt/myca/credentials/asana",
        "/opt/myca/credentials/signal",
        "/opt/myca/credentials/whatsapp",
        "/opt/myca/credentials/google",
        "/opt/myca/credentials/notion",
        "/opt/myca/logs/workflows",
        "/opt/myca/logs/api",
        "/opt/myca/logs/credentials",
        "/opt/myca/logs/security",
        "/opt/myca/config",
        "/opt/myca/data",
        "/opt/myca/sandbox",
    ]
    _run(ssh, f"mkdir -p {' '.join(dirs)}", sudo=True, password=pw, check=False)
    _run(ssh, "chown -R myca:myca /opt/myca", sudo=True, password=pw, check=False)
    _run(ssh, "chmod -R 750 /opt/myca/credentials", sudo=True, password=pw, check=False)


def _step_firewall(ssh: paramiko.SSHClient, pw: str):
    logger.info("=== Step 4: Configure UFW firewall ===")
    ports = [
        "22/tcp",    # SSH
        "80/tcp",    # Caddy HTTP
        "443/tcp",   # Caddy HTTPS
        "5678/tcp",  # n8n
        "8000/tcp",  # FastAPI core
        "8001/tcp",  # MAS orchestrator
        "8089/tcp",  # signal-cli
        "9000/tcp",  # Node Daemon WS
    ]
    _run(ssh, "apt-get install -y -qq ufw", sudo=True, password=pw, check=False)
    for port in ports:
        _run(ssh, f"ufw allow {port}", sudo=True, password=pw, check=False)
    # Allow inter-VM traffic on LAN
    _run(ssh, "ufw allow from 192.168.0.0/24", sudo=True, password=pw, check=False)
    _run(ssh, "ufw --force enable", sudo=True, password=pw, check=False)
    _run(ssh, "ufw status verbose", sudo=True, password=pw)


def _step_install_caddy(ssh: paramiko.SSHClient, pw: str):
    logger.info("=== Step 5: Install Caddy reverse proxy ===")
    cmds = [
        "apt-get install -y -qq debian-keyring debian-archive-keyring apt-transport-https",
        "curl -1sLf https://dl.cloudsmith.io/public/caddy/stable/gpg.key | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg 2>/dev/null || true",
        "curl -1sLf https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt > /etc/apt/sources.list.d/caddy-stable.list",
        "apt-get update -qq",
        "apt-get install -y -qq caddy",
        "systemctl enable caddy",
    ]
    for cmd in cmds:
        _run(ssh, cmd, sudo=True, password=pw, check=False)


def _step_deploy_compose(ssh: paramiko.SSHClient, pw: str):
    """Deploy Cowork's docker-compose if it exists locally. Otherwise skip."""
    logger.info("=== Step 6: Deploy docker-compose.myca-vm.yml ===")
    compose_path = Path(__file__).parent.parent / "docker-compose.myca-vm.yml"
    if not compose_path.exists():
        logger.warning("docker-compose.myca-vm.yml not found locally (Cowork provides this). Skipping.")
        return
    sftp = ssh.open_sftp()
    sftp.put(str(compose_path), "/opt/myca/docker-compose.yml")
    sftp.close()
    _run(ssh, "cd /opt/myca && docker compose up -d", sudo=True, password=pw, check=False)


def _step_verify(ssh: paramiko.SSHClient, pw: str):
    logger.info("=== Step 7: Verify ===")
    _run(ssh, "docker ps --format 'table {{.Names}}\\t{{.Status}}\\t{{.Ports}}'", check=False)
    _run(ssh, "ufw status numbered", sudo=True, password=pw, check=False)
    code, out, _ = _run(ssh, "systemctl is-active docker", check=False)
    logger.info("Docker service: %s", out)
    code, out, _ = _run(ssh, "systemctl is-active caddy", check=False)
    logger.info("Caddy service: %s", out)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Provision MYCA VM (192.168.0.191)")
    parser.add_argument("--dry-run", action="store_true", help="Print actions without executing")
    parser.add_argument("--skip-docker-compose", action="store_true", help="Skip docker compose deployment")
    args = parser.parse_args()
    provision(dry_run=args.dry_run, skip_compose=args.skip_docker_compose)
