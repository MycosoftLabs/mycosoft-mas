#!/usr/bin/env python3
"""
MYCA VM 191 — Complete Provisioning Script

Creates MYCA's workspace VM on Proxmox, waits for boot, then deploys
all services. Run from any machine on the LAN (e.g., Sandbox 187).

Usage:
    # Full provisioning (create VM + deploy services)
    python3 provision_myca_vm_191.py

    # Just deploy services (VM already exists)
    python3 provision_myca_vm_191.py --skip-vm-create

    # Dry run
    python3 provision_myca_vm_191.py --dry-run

Requires:
    pip install requests paramiko
"""

import argparse
import json
import logging
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("myca-provision")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
PROXMOX_HOST = os.getenv("PROXMOX_HOST", "192.168.0.202")
PROXMOX_PORT = int(os.getenv("PROXMOX_PORT", "8006"))
PROXMOX_NODE = os.getenv("PROXMOX_NODE", "build")

MYCA_VMID = 191
MYCA_VM_NAME = "myca-191"
MYCA_VM_IP = "192.168.0.191"
MYCA_VM_USER = os.getenv("MYCA_VM_USER", "mycosoft")

# VM hardware spec
VM_CORES = 8
VM_MEMORY_MB = 32768  # 32 GB
VM_DISK_GB = 256
VM_BALLOON_MB = 16384  # min 16 GB

# Ubuntu cloud image (Proxmox should have this template or ISO)
UBUNTU_TEMPLATE = os.getenv("UBUNTU_TEMPLATE", "local:iso/ubuntu-22.04-server-cloudimg-amd64.img")

SCRIPT_DIR = Path(__file__).parent
REPO_ROOT = SCRIPT_DIR.parent.parent
INFRA_DIR = SCRIPT_DIR


def _load_credentials():
    """Load credentials from .credentials.local or environment."""
    cred_paths = [
        REPO_ROOT / ".credentials.local",
        Path.home() / ".mycosoft-credentials",
        Path("/opt/myca/credentials/.env"),
    ]
    for p in cred_paths:
        if p.exists():
            logger.info("Loading credentials from %s", p)
            for line in p.read_text().splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ.setdefault(key.strip(), value.strip())
            break

    return {
        "proxmox_token_id": os.getenv("PROXMOX_TOKEN_ID", ""),
        "proxmox_token_secret": os.getenv("PROXMOX_TOKEN_SECRET", ""),
        "proxmox_password": os.getenv("PROXMOX_PASSWORD", ""),
        "vm_password": os.getenv("VM_PASSWORD", os.getenv("VM_SSH_PASSWORD", "")),
        "ssh_pubkey": os.getenv("SSH_PUBKEY", ""),
    }


# ---------------------------------------------------------------------------
# Phase 1: Create VM on Proxmox
# ---------------------------------------------------------------------------

def create_vm_on_proxmox(creds: dict, dry_run: bool = False) -> bool:
    """Create MYCA VM 191 via Proxmox API."""
    import requests
    import urllib3
    urllib3.disable_warnings()

    base_url = f"https://{PROXMOX_HOST}:{PROXMOX_PORT}/api2/json"

    # Auth headers
    if creds["proxmox_token_id"] and creds["proxmox_token_secret"]:
        headers = {
            "Authorization": f"PVEAPIToken={creds['proxmox_token_id']}={creds['proxmox_token_secret']}"
        }
    elif creds["proxmox_password"]:
        logger.info("Authenticating with password...")
        resp = requests.post(
            f"{base_url}/access/ticket",
            data={"username": "root@pam", "password": creds["proxmox_password"]},
            verify=False, timeout=10,
        )
        resp.raise_for_status()
        ticket_data = resp.json()["data"]
        headers = {
            "Cookie": f"PVEAuthCookie={ticket_data['ticket']}",
            "CSRFPreventionToken": ticket_data["CSRFPreventionToken"],
        }
    else:
        logger.error("No Proxmox credentials found. Set PROXMOX_TOKEN_ID/PROXMOX_TOKEN_SECRET or PROXMOX_PASSWORD")
        return False

    # Check if VM already exists
    logger.info("Checking if VM %d already exists...", MYCA_VMID)
    try:
        resp = requests.get(
            f"{base_url}/nodes/{PROXMOX_NODE}/qemu/{MYCA_VMID}/status/current",
            headers=headers, verify=False, timeout=10,
        )
        if resp.status_code == 200:
            status = resp.json().get("data", {}).get("status", "unknown")
            logger.info("VM %d already exists (status: %s)", MYCA_VMID, status)
            if status != "running":
                if not dry_run:
                    logger.info("Starting VM %d...", MYCA_VMID)
                    requests.post(
                        f"{base_url}/nodes/{PROXMOX_NODE}/qemu/{MYCA_VMID}/status/start",
                        headers=headers, verify=False, timeout=10,
                    )
            return True
    except Exception:
        pass

    # Read cloud-init user-data
    cloud_init_path = INFRA_DIR / "cloud-init-user-data.yml"
    cloud_init_data = ""
    if cloud_init_path.exists():
        cloud_init_data = cloud_init_path.read_text()

    vm_config = {
        "vmid": MYCA_VMID,
        "name": MYCA_VM_NAME,
        "description": "MYCA AI Secretary - Workspace VM",
        "cores": VM_CORES,
        "memory": VM_MEMORY_MB,
        "balloon": VM_BALLOON_MB,
        "cpu": "host",
        "ostype": "l26",
        "scsihw": "virtio-scsi-pci",
        "agent": 1,
        "onboot": 1,
        "boot": "order=scsi0",
        "scsi0": f"local-lvm:{VM_DISK_GB}",
        "net0": "virtio,bridge=vmbr0",
        "ide2": f"{UBUNTU_TEMPLATE},media=cdrom",
        # Cloud-init drive
        "ide0": "local-lvm:cloudinit",
        "ciuser": MYCA_VM_USER,
        "ipconfig0": f"ip={MYCA_VM_IP}/24,gw=192.168.0.1",
        "nameserver": "192.168.0.1 1.1.1.1",
        "searchdomain": "mycosoft.local",
        "serial0": "socket",
        "vga": "serial0",
    }

    if creds["vm_password"]:
        vm_config["cipassword"] = creds["vm_password"]
    if creds["ssh_pubkey"]:
        vm_config["sshkeys"] = creds["ssh_pubkey"]

    logger.info("=" * 60)
    logger.info("  Creating MYCA VM %d on Proxmox node '%s'", MYCA_VMID, PROXMOX_NODE)
    logger.info("=" * 60)
    for k, v in vm_config.items():
        if k not in ("cipassword", "sshkeys"):
            logger.info("  %-20s: %s", k, v)

    if dry_run:
        logger.info("[DRY RUN] Would create VM with above config")
        return True

    try:
        resp = requests.post(
            f"{base_url}/nodes/{PROXMOX_NODE}/qemu",
            headers=headers,
            data=vm_config,
            verify=False,
            timeout=60,
        )
        resp.raise_for_status()
        task_id = resp.json().get("data", "")
        logger.info("VM creation task started: %s", task_id)

        # Wait for task completion
        for _ in range(60):
            time.sleep(5)
            try:
                status_resp = requests.get(
                    f"{base_url}/nodes/{PROXMOX_NODE}/tasks/{task_id}/status",
                    headers=headers, verify=False, timeout=10,
                )
                task_status = status_resp.json().get("data", {})
                if task_status.get("status") == "stopped":
                    if task_status.get("exitstatus") == "OK":
                        logger.info("VM %d created successfully!", MYCA_VMID)
                        break
                    else:
                        logger.error("VM creation failed: %s", task_status.get("exitstatus"))
                        return False
            except Exception:
                continue
        else:
            logger.warning("VM creation timed out waiting for task - may still be running")

        # Start the VM
        logger.info("Starting VM %d...", MYCA_VMID)
        requests.post(
            f"{base_url}/nodes/{PROXMOX_NODE}/qemu/{MYCA_VMID}/status/start",
            headers=headers, verify=False, timeout=10,
        )
        return True

    except Exception as exc:
        logger.error("Failed to create VM: %s", exc)
        return False


# ---------------------------------------------------------------------------
# Phase 2: Wait for VM to be reachable
# ---------------------------------------------------------------------------

def wait_for_vm(timeout_seconds: int = 300) -> bool:
    """Wait for MYCA VM to respond on SSH port."""
    logger.info("Waiting for VM %s to become reachable (timeout: %ds)...", MYCA_VM_IP, timeout_seconds)
    start = time.time()
    while time.time() - start < timeout_seconds:
        try:
            sock = socket.create_connection((MYCA_VM_IP, 22), timeout=5)
            sock.close()
            logger.info("VM %s is reachable on port 22!", MYCA_VM_IP)
            # Give cloud-init a bit more time to finish
            logger.info("Waiting 30s for cloud-init to complete...")
            time.sleep(30)
            return True
        except (socket.timeout, ConnectionRefusedError, OSError):
            time.sleep(10)
    logger.error("VM %s did not become reachable within %ds", MYCA_VM_IP, timeout_seconds)
    return False


# ---------------------------------------------------------------------------
# Phase 3: Post-boot provisioning via SSH
# ---------------------------------------------------------------------------

def provision_via_ssh(creds: dict, dry_run: bool = False) -> bool:
    """SSH into the VM and deploy MYCA services."""
    try:
        import paramiko
    except ImportError:
        logger.error("paramiko required: pip install paramiko")
        return False

    password = creds["vm_password"]
    if not password:
        logger.error("VM_PASSWORD not set - cannot SSH to VM")
        return False

    if dry_run:
        logger.info("[DRY RUN] Would SSH to %s and deploy services", MYCA_VM_IP)
        return True

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        logger.info("Connecting via SSH to %s@%s ...", MYCA_VM_USER, MYCA_VM_IP)
        ssh.connect(MYCA_VM_IP, username=MYCA_VM_USER, password=password, timeout=30)
        logger.info("SSH connected.")
    except Exception as exc:
        logger.error("SSH connection failed: %s", exc)
        return False

    def run(cmd, sudo=False, check=True):
        if sudo:
            cmd = f"echo '{password}' | sudo -S bash -c '{cmd}'"
        logger.info("  >> %s", cmd[:120] + ("..." if len(cmd) > 120 else ""))
        _, stdout, stderr = ssh.exec_command(cmd, timeout=300)
        exit_code = stdout.channel.recv_exit_status()
        out = stdout.read().decode(errors="replace").strip()
        err = stderr.read().decode(errors="replace").strip()
        if exit_code != 0 and check:
            logger.warning("  EXIT %d: %s", exit_code, err[:300])
        return exit_code, out, err

    try:
        # 1. Verify Docker is installed (cloud-init should have done this)
        logger.info("=== Verifying Docker installation ===")
        code, out, _ = run("docker --version", check=False)
        if code != 0:
            logger.info("Docker not found, installing...")
            docker_cmds = [
                "apt-get update -qq",
                "apt-get install -y -qq ca-certificates curl gnupg lsb-release",
                "install -m 0755 -d /etc/apt/keyrings",
                "curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc",
                "chmod a+r /etc/apt/keyrings/docker.asc",
                'echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo $VERSION_CODENAME) stable" > /etc/apt/sources.list.d/docker.list',
                "apt-get update -qq",
                "apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin",
                "systemctl enable docker && systemctl start docker",
                f"usermod -aG docker {MYCA_VM_USER}",
            ]
            for cmd in docker_cmds:
                run(cmd, sudo=True, check=False)
        else:
            logger.info("Docker: %s", out)

        # 2. Create directory structure (idempotent)
        logger.info("=== Creating directory structure ===")
        dirs = [
            "/opt/myca/credentials/{discord,slack,asana,signal,whatsapp,google,notion,github}",
            "/opt/myca/logs/{api,workflows,security,gateway}",
            "/opt/myca/{config,data,sandbox,caddy}",
            "/opt/myca/n8n/workflows",
            "/opt/myca/mycosoft-mas",
        ]
        run(f"mkdir -p {' '.join(dirs)}", sudo=True, check=False)
        run("chown -R myca:myca /opt/myca 2>/dev/null || chown -R mycosoft:mycosoft /opt/myca", sudo=True, check=False)
        run("chmod -R 750 /opt/myca/credentials", sudo=True, check=False)

        # 3. Upload docker-compose and Caddyfile
        logger.info("=== Uploading service configs ===")
        sftp = ssh.open_sftp()

        compose_src = REPO_ROOT / "infra" / "myca-vm" / "docker-compose.myca-workspace.yml"
        if compose_src.exists():
            sftp.put(str(compose_src), "/opt/myca/docker-compose.yml")
            logger.info("Uploaded docker-compose.yml")
        else:
            # Fall back to the older compose file
            compose_alt = REPO_ROOT / "infra" / "docker-compose.myca-vm.yml"
            if compose_alt.exists():
                sftp.put(str(compose_alt), "/opt/myca/docker-compose.yml")
                logger.info("Uploaded docker-compose.yml (from infra/)")

        caddyfile_src = INFRA_DIR / "Caddyfile"
        if caddyfile_src.exists():
            sftp.put(str(caddyfile_src), "/opt/myca/caddy/Caddyfile")
            logger.info("Uploaded Caddyfile")

        env_src = INFRA_DIR / ".env.myca"
        if env_src.exists():
            sftp.put(str(env_src), "/opt/myca/.env")
            logger.info("Uploaded .env")

        sftp.close()

        # 4. Clone the MAS repo for MYCA's workspace code
        logger.info("=== Cloning MAS repo ===")
        run(
            "cd /opt/myca/mycosoft-mas && git pull 2>/dev/null || "
            "git clone https://github.com/MycosoftLabs/mycosoft-mas.git /opt/myca/mycosoft-mas",
            check=False,
        )

        # 5. Deploy docker-compose stack
        logger.info("=== Deploying MYCA services ===")
        run("cd /opt/myca && docker compose down 2>/dev/null; docker compose up -d", sudo=True, check=False)

        # 6. Verify services
        logger.info("=== Verifying services ===")
        time.sleep(15)  # Let containers start
        code, out, _ = run("docker ps --format 'table {{.Names}}\\t{{.Status}}\\t{{.Ports}}'", check=False)
        logger.info("Running containers:\n%s", out)

        # 7. Health check
        logger.info("=== Health checks ===")
        for service, port in [("Redis", 6379), ("n8n", 5678), ("FastAPI", 8000)]:
            code, _, _ = run(f"curl -sf http://localhost:{port}/ >/dev/null 2>&1 && echo ok || echo fail", check=False)

        logger.info("=" * 60)
        logger.info("  MYCA VM 191 provisioning complete!")
        logger.info("  IP: %s", MYCA_VM_IP)
        logger.info("  Services: docker compose at /opt/myca/")
        logger.info("=" * 60)
        return True

    finally:
        ssh.close()


# ---------------------------------------------------------------------------
# Phase 4: Verify from outside
# ---------------------------------------------------------------------------

def verify_deployment() -> dict:
    """Quick verification that MYCA VM services respond."""
    results = {}
    checks = {
        "ssh": (MYCA_VM_IP, 22),
        "redis": (MYCA_VM_IP, 6379),
        "n8n": (MYCA_VM_IP, 5678),
        "fastapi": (MYCA_VM_IP, 8000),
    }
    for name, (host, port) in checks.items():
        try:
            sock = socket.create_connection((host, port), timeout=5)
            sock.close()
            results[name] = "reachable"
        except Exception:
            results[name] = "unreachable"

    logger.info("Verification results:")
    for name, status in results.items():
        logger.info("  %-10s: %s", name, status)
    return results


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Provision MYCA VM 191 — complete one-command setup",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Full provisioning
  python3 provision_myca_vm_191.py

  # VM already exists, just deploy services
  python3 provision_myca_vm_191.py --skip-vm-create

  # Preview what would happen
  python3 provision_myca_vm_191.py --dry-run

Environment variables:
  PROXMOX_HOST          Proxmox API host (default: 192.168.0.202)
  PROXMOX_NODE          Proxmox node name (default: build)
  PROXMOX_TOKEN_ID      API token ID (e.g., root@pam!myca)
  PROXMOX_TOKEN_SECRET  API token secret
  PROXMOX_PASSWORD      Alternative: root password
  VM_PASSWORD           Password for mycosoft user on new VM
  SSH_PUBKEY            SSH public key to inject via cloud-init
        """,
    )
    parser.add_argument("--dry-run", action="store_true", help="Preview without executing")
    parser.add_argument("--skip-vm-create", action="store_true", help="Skip Proxmox VM creation")
    parser.add_argument("--skip-deploy", action="store_true", help="Skip service deployment")
    parser.add_argument("--verify-only", action="store_true", help="Only run verification checks")
    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("  MYCA VM 191 — Provisioning Script")
    logger.info("  Proxmox: %s:%d (node: %s)", PROXMOX_HOST, PROXMOX_PORT, PROXMOX_NODE)
    logger.info("  Target:  %s (VMID %d)", MYCA_VM_IP, MYCA_VMID)
    logger.info("=" * 60)

    creds = _load_credentials()

    if args.verify_only:
        verify_deployment()
        return

    # Phase 1: Create VM
    if not args.skip_vm_create:
        if not create_vm_on_proxmox(creds, dry_run=args.dry_run):
            logger.error("VM creation failed. Aborting.")
            sys.exit(1)

    # Phase 2: Wait for VM
    if not args.dry_run and not args.skip_deploy:
        if not wait_for_vm():
            logger.error("VM not reachable. Check Proxmox console.")
            sys.exit(1)

    # Phase 3: Deploy services
    if not args.skip_deploy:
        if not provision_via_ssh(creds, dry_run=args.dry_run):
            logger.error("Service deployment failed.")
            sys.exit(1)

    # Phase 4: Verify
    if not args.dry_run:
        verify_deployment()

    logger.info("Done. MYCA's workspace is ready at %s", MYCA_VM_IP)


if __name__ == "__main__":
    main()
