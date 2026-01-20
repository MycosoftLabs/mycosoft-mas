#!/usr/bin/env python3
"""Fix Cloudflare tunnel routing for MINDEX (and optionally NatureOS) APIs.

Why:
- The VM runs MINDEX on localhost:8000, but without Cloudflare ingress rules
  requests like https://sandbox.mycosoft.com/api/mindex/* can return 404 from the website.

What this does:
- Inserts path-based ingress rules before the catch-all (http_status) rule:
  - /api/mindex/* and /api/mindex -> http://localhost:8000

Notes:
- This is routing only. It does NOT start containers.
"""

import paramiko
import sys
from io import StringIO

import yaml

VM_IP = "192.168.0.187"
VM_USER = "mycosoft"
VM_PASSWORD = "Mushroom1!Mushroom1!"


def main() -> None:
  try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
  except Exception:
    pass

  ssh = paramiko.SSHClient()
  ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
  ssh.connect(VM_IP, username=VM_USER, password=VM_PASSWORD)

  print("Fixing Cloudflare MINDEX routes...")

  # Read current config
  _, stdout, _ = ssh.exec_command("cat ~/.cloudflared/config.yml")
  config_str = stdout.read().decode("utf-8", errors="replace")
  config = yaml.safe_load(StringIO(config_str)) or {}
  ingress = list(config.get("ingress", []))

  print(f"Current ingress rules: {len(ingress)}")

  # Remove existing MINDEX routes (avoid duplicates/drift)
  def is_mindex_route(rule: object) -> bool:
    if not isinstance(rule, dict):
      return False
    service = str(rule.get("service", ""))
    path = str(rule.get("path", ""))
    return "/api/mindex" in path or "localhost:8000" in service

  ingress = [r for r in ingress if not is_mindex_route(r)]

  # Find catch-all index (http_status)
  catch_idx = len(ingress)
  for i, r in enumerate(ingress):
    if isinstance(r, dict) and str(r.get("service", "")).startswith("http_status"):
      catch_idx = i
      break

  mindex_routes = [
    {"hostname": "sandbox.mycosoft.com", "service": "http://localhost:8000", "path": "/api/mindex/*"},
    {"hostname": "sandbox.mycosoft.com", "service": "http://localhost:8000", "path": "/api/mindex"},
  ]

  ingress = ingress[:catch_idx] + mindex_routes + ingress[catch_idx:]
  config["ingress"] = ingress

  config_yaml = yaml.dump(config, default_flow_style=False, sort_keys=False)

  # Write updated config
  ssh.exec_command(
    "cat > /tmp/cf_fixed_mindex.yml << 'CFEOF'\n" + config_yaml + "\nCFEOF"
  )[1].read()

  ssh.exec_command(
    "cp ~/.cloudflared/config.yml ~/.cloudflared/config.yml.backup_mindex && "
    "mv /tmp/cf_fixed_mindex.yml ~/.cloudflared/config.yml"
  )[1].read()

  # Restart tunnel
  ssh.exec_command(f'echo "{VM_PASSWORD}" | sudo -S systemctl restart cloudflared')[1].read()

  print("[OK] Cloudflare config updated and tunnel restarted")
  print(f"   Added {len(mindex_routes)} MINDEX routes")

  ssh.close()


if __name__ == "__main__":
  main()

