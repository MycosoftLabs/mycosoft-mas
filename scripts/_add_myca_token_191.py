#!/usr/bin/env python3
"""Add GitHub or API tokens to VM 191's myca-workspace .env.

Usage:
  python scripts/_add_myca_token_191.py --github TOKEN
  python scripts/_add_myca_token_191.py --anthropic KEY
  python scripts/_add_myca_token_191.py --openai KEY
  python scripts/_add_myca_token_191.py --env KEY=VALUE
  python scripts/_add_myca_token_191.py --gh-login   # run: echo TOKEN | gh auth login --with-token

If token not provided, reads from local .env / .credentials.local.
"""
import argparse
import os
import sys

ROOT = os.path.join(os.path.dirname(__file__), "..")
VM_IP = "192.168.0.191"
VM_USER = "mycosoft"
KEY_PATH = os.path.expanduser("~/.ssh/myca_vm191")

# Load local env
env = {}
creds = {}
for f, d in [(os.path.join(ROOT, ".env"), env), (os.path.join(ROOT, ".credentials.local"), creds)]:
    if os.path.exists(f):
        for line in open(f, encoding="utf-8").read().splitlines():
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                d[k.strip()] = v.strip()
env.update(creds)

VM_PASSWORD = env.get("VM_PASSWORD") or env.get("VM_SSH_PASSWORD", "")

sys.path.insert(0, ROOT)
import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
try:
    if os.path.exists(KEY_PATH):
        ssh.connect(VM_IP, username=VM_USER, pkey=paramiko.Ed25519Key.from_private_key_file(KEY_PATH), timeout=20)
    else:
        ssh.connect(VM_IP, username=VM_USER, password=VM_PASSWORD, timeout=20)
except Exception as e:
    print(f"SSH failed: {e}")
    sys.exit(1)

def run(cmd, timeout=60):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    return stdout.read().decode("utf-8", errors="replace").strip(), stderr.read().decode("utf-8", errors="replace").strip()

def sudo(cmd, timeout=60):
    stdin, stdout, stderr = ssh.exec_command("sudo -S bash -c " + repr(cmd), timeout=timeout)
    if VM_PASSWORD:
        stdin.write(VM_PASSWORD + "\n")
        stdin.flush()
    stdin.channel.shutdown_write()
    return stdout.read().decode("utf-8", errors="replace").strip(), stderr.read().decode("utf-8", errors="replace").strip()

def main():
    ap = argparse.ArgumentParser(description="Add tokens to VM 191")
    ap.add_argument("--github", nargs="?", default=None, const="", help="GITHUB_TOKEN (or read from env)")
    ap.add_argument("--anthropic", nargs="?", default=None, const="", help="ANTHROPIC_API_KEY")
    ap.add_argument("--openai", nargs="?", default=None, const="", help="OPENAI_API_KEY")
    ap.add_argument("--env", action="append", help="KEY=VALUE to add")
    ap.add_argument("--gh-login", action="store_true", help="Run gh auth login --with-token using GITHUB_TOKEN")
    args = ap.parse_args()

    # Build updates
    updates = {}
    if args.github is not None:
        updates["GITHUB_TOKEN"] = args.github or env.get("GITHUB_TOKEN", "")
    if args.anthropic is not None:
        updates["ANTHROPIC_API_KEY"] = args.anthropic or env.get("ANTHROPIC_API_KEY", "")
    if args.openai is not None:
        updates["OPENAI_API_KEY"] = args.openai or env.get("OPENAI_API_KEY", "")
    for kv in (args.env or []):
        if "=" in kv:
            k, v = kv.split("=", 1)
            updates[k.strip()] = v

    if not updates and not args.gh_login:
        print("No tokens to add. Use --github, --anthropic, --openai, or --env KEY=VALUE")
        sys.exit(0)

    # Fetch current .env from VM
    sftp = ssh.open_sftp()
    remote_env = "/home/mycosoft/myca-workspace/.env"
    run("mkdir -p ~/myca-workspace")
    try:
        with sftp.open(remote_env, "r") as f:
            current = f.read().decode("utf-8", errors="replace")
    except FileNotFoundError:
        current = ""

    lines = []
    seen = set()
    for line in current.splitlines():
        if "=" in line and not line.strip().startswith("#"):
            k = line.split("=", 1)[0].strip()
            if k in updates:
                lines.append(f"{k}={updates[k]}")
                seen.add(k)
                continue
        lines.append(line)

    for k, v in updates.items():
        if k not in seen:
            lines.append(f"{k}={v}")

    new_content = "\n".join(lines) + "\n"
    with sftp.open(remote_env, "w") as f:
        f.write(new_content)
    run("chmod 600 ~/myca-workspace/.env")
    sftp.close()

    print("Updated ~/myca-workspace/.env on VM 191:", ", ".join(updates.keys()) if updates else "(none)")

    if args.gh_login:
        token = updates.get("GITHUB_TOKEN") or env.get("GITHUB_TOKEN", "")
        if token:
            stdin, stdout, stderr = ssh.exec_command("source ~/myca-workspace/.env 2>/dev/null; gh auth login --with-token", timeout=30)
            stdin.write(token + "\n")
            stdin.flush()
            stdin.channel.shutdown_write()
            out = stdout.read().decode("utf-8", errors="replace")
            err = stderr.read().decode("utf-8", errors="replace")
            if "Logged in" in out or "Logged in" in err:
                print("gh auth login --with-token: OK")
            else:
                print(out or err or "Check gh auth status: gh auth status")
        else:
            print("No GITHUB_TOKEN to run gh auth login")

if __name__ == "__main__":
    main()
