#!/usr/bin/env python3
"""Bootstrap cloudflared on Production VM 186: install, configure, enable, start.

Requires: VM_PASSWORD (or VM_SSH_PASSWORD), CLOUDFLARE_TUNNEL_TOKEN_PRODUCTION
VM 186 must be reachable. Run Phase 1 clone first if VM does not exist.

Run from MAS repo: python scripts/_bootstrap_production_cloudflared_186.py
"""

import base64
import os
import sys
from pathlib import Path

import paramiko


def _load_creds():
    creds = Path(__file__).parent.parent / ".credentials.local"
    if creds.exists():
        for line in creds.read_text().splitlines():
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                k, v = k.strip(), v.strip().strip('"\'')
                if k and k not in os.environ:
                    os.environ[k] = v


_load_creds()

VM_HOST = os.getenv("PRODUCTION_VM_HOST", "192.168.0.186")
VM_USER = os.getenv("VM_SSH_USER", "mycosoft")
VM_PASS = os.getenv("VM_PASSWORD") or os.environ.get("VM_SSH_PASSWORD")
TUNNEL_TOKEN = os.getenv("CLOUDFLARE_TUNNEL_TOKEN_PRODUCTION") or os.getenv("CLOUDFLARE_TUNNEL_TOKEN")


def main():
    if not VM_PASS:
        print("ERROR: VM_PASSWORD not set.")
        sys.exit(1)
    if not TUNNEL_TOKEN:
        print("ERROR: CLOUDFLARE_TUNNEL_TOKEN_PRODUCTION not set.")
        print("  Run _cloudflare_create_production_tunnel.py first and add token to .credentials.local")
        sys.exit(1)

    print(f"Connecting to {VM_HOST}...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh.connect(VM_HOST, username=VM_USER, password=VM_PASS, timeout=15)
    except Exception as e:
        print(f"ERROR: SSH failed: {e}")
        print("  Ensure VM 186 is up and reachable. Run Phase 1 clone first.")
        sys.exit(1)

    def run(cmd, timeout=60, use_sudo=False):
        if use_sudo and VM_PASS:
            pw_b64 = base64.b64encode(VM_PASS.encode()).decode()
            tok_b64 = base64.b64encode(TUNNEL_TOKEN.encode()).decode() if "cloudflared service install" in cmd else None
            if tok_b64:
                inner = f"cloudflared service install $(echo {tok_b64!r} | base64 -d)"
            else:
                inner = cmd
            cmd = f"echo {pw_b64!r} | base64 -d | sudo -S bash -c {repr(inner)}"
        stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
        code = stdout.channel.recv_exit_status()
        out = (stdout.read() + stderr.read()).decode(errors="replace").strip()
        return code, out

    # Install cloudflared if missing
    code, _ = run("which cloudflared")
    if code != 0:
        print("Installing cloudflared...")
        install_cmd = (
            "curl -sSL -o /tmp/cf https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 "
            "&& chmod +x /tmp/cf && mv /tmp/cf /usr/local/bin/cloudflared"
        )
        code2, out2 = run(install_cmd, timeout=90, use_sudo=True)
        if code2 != 0:
            print(f"  Install failed: {out2[:300]}")
            print("  Install manually: https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/installation/")
            ssh.close()
            sys.exit(1)
        print("  cloudflared installed.")
    else:
        print("cloudflared already installed.")

    # Stop existing cloudflared to avoid conflicts
    run("systemctl stop cloudflared 2>/dev/null || true", use_sudo=True)
    run("systemctl disable cloudflared 2>/dev/null || true", use_sudo=True)

    # cloudflared service install writes config and creates systemd unit
    # Token must be passed as argument
    print("Configuring cloudflared service...")
    code, out = run(f"cloudflared service install {TUNNEL_TOKEN}", timeout=30, use_sudo=True)
    if code != 0:
        print(f"  Service install failed: {out[:400]}")
        print("  Manual: ssh to VM 186, run: sudo cloudflared service install <TOKEN>")
        ssh.close()
        sys.exit(1)

    run("systemctl daemon-reload", use_sudo=True)
    run("systemctl enable cloudflared", use_sudo=True)
    run("systemctl start cloudflared", use_sudo=True)
    code, out = run("systemctl status cloudflared --no-pager 2>&1 | head -12", use_sudo=True)
    print(out)
    if "active (running)" in out.lower():
        print("\nProduction cloudflared: enabled and started.")
    else:
        print("\nCheck: ssh {}@{} 'sudo journalctl -u cloudflared -n 20'".format(VM_USER, VM_HOST))
    ssh.close()


if __name__ == "__main__":
    main()
