#!/usr/bin/env python3
"""Pre-flight checks for bringing mycosoft.com and mycosoft.org live.

Run from MAS repo: python scripts/_preflight_production_live.py

Checks:
- VM 186 reachable
- Credentials present (VM_PASSWORD, CLOUDFLARE_TUNNEL_TOKEN_PRODUCTION, CLOUDFLARE_ZONE_ID_PRODUCTION)
- MAS (188:8001) and MINDEX (189:8000) API health
- Supabase env vars (NEXT_PUBLIC_SUPABASE_URL, NEXT_PUBLIC_SUPABASE_ANON_KEY) for auth
- Prints next steps for Phase 2–4
"""

import os
import socket
import subprocess
import sys
import urllib.request
from pathlib import Path


def _load_creds():
    mas_root = Path(__file__).parent.parent
    code_root = mas_root.parent
    for base in (
        mas_root / ".credentials.local",
        code_root / "website" / ".credentials.local",
        code_root / "website" / ".env.local",
        code_root / "WEBSITE" / "website" / ".credentials.local",
        code_root / "WEBSITE" / "website" / ".env.local",
    ):
        if base.exists():
            for line in base.read_text().splitlines():
                if line and not line.startswith("#") and "=" in line:
                    k, _, v = line.partition("=")
                    k, v = k.strip(), v.strip().strip('"\'')
                    if k and k not in os.environ:
                        os.environ[k] = v


def _ping(host: str, timeout: float = 2.0) -> bool:
    try:
        result = subprocess.run(
            ["ping", "-n", "1", "-w", str(int(timeout * 1000)), host],
            capture_output=True,
            timeout=timeout + 1,
        )
        return result.returncode == 0
    except Exception:
        return False


def _ssh_port_open(host: str, port: int = 22, timeout: float = 5.0) -> bool:
    """Check if SSH port is reachable."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception:
        return False


def _http_ok(url: str, timeout: float = 5.0) -> bool:
    """Check if HTTP GET returns 2xx."""
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return 200 <= resp.status < 300
    except Exception:
        return False


def main():
    _load_creds()

    VM = "192.168.0.186"
    ok = True

    print("Pre-flight checks for mycosoft.com / mycosoft.org\n" + "=" * 50)

    # 1. VM 186 reachable (ping)
    print(f"\n1. VM 186 reachable ({VM})...")
    if _ping(VM):
        print("   Ping: OK")
    else:
        print("   Ping: FAIL")
        print("   -> Power on Production VM in Proxmox. Ensure IP 192.168.0.186.")
        ok = False

    # 1b. SSH port 22 open
    print(f"   SSH (port 22)...")
    if _ssh_port_open(VM):
        print("   SSH: OK")
    else:
        print("   SSH: FAIL (port 22 unreachable)")
        print("   -> Use Proxmox console on VM 186. Run: sudo systemctl enable ssh && sudo systemctl start ssh")
        print("   -> Check firewall: sudo ufw allow 22; sudo ufw status")
        ok = False

    # 2. Credentials
    print("\n2. Credentials...")
    vm_pass = os.getenv("VM_PASSWORD") or os.getenv("VM_SSH_PASSWORD")
    tok = os.getenv("CLOUDFLARE_TUNNEL_TOKEN_PRODUCTION") or os.getenv("CLOUDFLARE_TUNNEL_TOKEN")
    zone = os.getenv("CLOUDFLARE_ZONE_ID_PRODUCTION") or os.getenv("CLOUDFLARE_ZONE_ID")
    cf_token = os.getenv("CLOUDFLARE_API_TOKEN")

    if vm_pass:
        print("   VM_PASSWORD: OK")
    else:
        print("   VM_PASSWORD: MISSING (add to .credentials.local)")
        ok = False

    if tok:
        print("   CLOUDFLARE_TUNNEL_TOKEN_PRODUCTION: OK")
    else:
        print("   CLOUDFLARE_TUNNEL_TOKEN_PRODUCTION: MISSING")
        print("   -> Create Production tunnel in Cloudflare (Zero Trust > Tunnels), then add token.")
        ok = False

    if zone:
        print("   CLOUDFLARE_ZONE_ID_PRODUCTION: OK")
    else:
        print("   CLOUDFLARE_ZONE_ID_PRODUCTION: MISSING (optional for purge)")

    if cf_token:
        print("   CLOUDFLARE_API_TOKEN: OK")
    else:
        print("   CLOUDFLARE_API_TOKEN: MISSING (optional for purge)")

    # 3. MAS and MINDEX API health
    print("\n3. MAS and MINDEX API health...")
    mas_ok = _http_ok("http://192.168.0.188:8001/health")
    mindex_ok = _http_ok("http://192.168.0.189:8000/health")
    if mas_ok:
        print("   MAS (188:8001): OK")
    else:
        print("   MAS (188:8001): FAIL (unreachable)")
        print("   -> Ensure MAS orchestrator is running on VM 188.")
        ok = False
    if mindex_ok:
        print("   MINDEX (189:8000): OK")
    else:
        print("   MINDEX (189:8000): FAIL (unreachable)")
        print("   -> Ensure MINDEX API is running on VM 189.")
        ok = False

    # 4. Supabase (for auth on live site)
    print("\n4. Supabase (auth on live mycosoft.com)...")
    supabase_url = os.getenv("NEXT_PUBLIC_SUPABASE_URL")
    supabase_key = os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY")
    if supabase_url and supabase_key:
        print("   NEXT_PUBLIC_SUPABASE_URL: OK")
        print("   NEXT_PUBLIC_SUPABASE_ANON_KEY: OK")
        print("   -> Add redirect URLs in Supabase: https://mycosoft.com, https://sandbox.mycosoft.com")
    else:
        print("   NEXT_PUBLIC_SUPABASE_URL or NEXT_PUBLIC_SUPABASE_ANON_KEY: MISSING")
        print("   -> Add to .env.local or .credentials.local for Docker build.")
        print("   -> Auth features will not work without these build-time vars.")
        ok = False

    print("\n" + "=" * 50)
    if ok:
        print("Pre-flight OK. Run:")
        print("  1. python scripts/_bootstrap_production_cloudflared_186.py")
        print("  2. cd WEBSITE/website && python _rebuild_production.py")
        print("  3. Verify: https://mycosoft.com, https://mycosoft.org")
    else:
        print("Fix issues above, then re-run this script.")
        sys.exit(1)


if __name__ == "__main__":
    main()
