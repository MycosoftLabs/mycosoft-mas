#!/usr/bin/env python3
"""
Sync required website videos to Sandbox VM NAS mount.
SSHs to 192.168.0.187, checks /opt/mycosoft/media/website/assets/<path>,
downloads from mycosoft.org (or configured URL) if missing.
Uses VM_PASSWORD from .credentials.local (same pattern as _run_sandbox_deploy_steps.py).
"""
import os
import sys
from pathlib import Path

# Load credentials
creds = Path(__file__).resolve().parent.parent / ".credentials.local"
if not creds.exists():
    print("ERROR: .credentials.local not found")
    sys.exit(1)
for line in creds.read_text().splitlines():
    if line and not line.startswith("#") and "=" in line:
        k, v = line.split("=", 1)
        os.environ[k.strip()] = v.strip()

VM_PASS = os.environ.get("VM_PASSWORD") or os.environ.get("VM_SSH_PASSWORD")
if not VM_PASS:
    print("ERROR: VM_PASSWORD or VM_SSH_PASSWORD not set")
    sys.exit(1)

import paramiko

HOST = "192.168.0.187"
USER = "mycosoft"
ASSETS_BASE = "/opt/mycosoft/media/website/assets"

# (relative_path, [source_urls] or None if manual source only)
# Multiple URLs tried in order; first successful wins.
REQUIRED_VIDEOS = [
    (
        "videos/mycelium-bg.mp4",
        [
            "https://mycosoft.org/videos/mycelium-bg.mp4",
            "https://sandbox.mycosoft.com/assets/videos/mycelium-bg.mp4",
        ],
    ),
    (
        "about us/Mycosoft Commercial 1.mp4",
        [
            "https://mycosoft.org/assets/about%20us/Mycosoft%20Commercial%201.mp4",
            "https://sandbox.mycosoft.com/assets/about%20us/Mycosoft%20Commercial%201.mp4",
        ],
    ),
    (
        "sporebase/Sporebase1publish.mp4",
        [
            "https://mycosoft.org/assets/sporebase/Sporebase1publish.mp4",
            "https://sandbox.mycosoft.com/assets/sporebase/Sporebase1publish.mp4",
        ],
    ),
    (
        "myconode/grok_video_2026-01-22-19-17-42.mp4",
        None,  # Custom/internal — not on mycosoft.org; copy from dev machine
    ),
    (
        "mushroom1/waterfall 1.mp4",
        [
            "https://mycosoft.org/assets/mushroom1/waterfall%201.mp4",
            "https://sandbox.mycosoft.com/assets/mushroom1/waterfall%201.mp4",
        ],
    ),
]


def run(ssh, cmd, timeout=120):
    _, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    try:
        out = stdout.read().decode(errors="replace")
        err = stderr.read().decode(errors="replace")
        code = stdout.channel.recv_exit_status()
    except (TimeoutError, Exception) as e:
        out = ""
        err = str(e)
        code = -1
    return code, out, err


def main():
    print("Connecting to 192.168.0.187...")
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(HOST, username=USER, password=VM_PASS, timeout=30)
    transport = c.get_transport()
    if transport:
        transport.set_keepalive(30)

    created = []
    existed = []
    missing_source = []
    download_failed = []

    for rel_path, urls in REQUIRED_VIDEOS:
        full_path = f"{ASSETS_BASE}/{rel_path}"
        dir_path = str(Path(rel_path).parent)

        # Check if file exists
        code, out, err = run(c, f"test -f '{full_path}' && echo EXISTS || echo MISSING", timeout=10)
        if "EXISTS" in (out + err):
            existed.append(rel_path)
            print(f"  OK (exists): {rel_path}")
            continue

        if urls is None:
            missing_source.append(rel_path)
            print(f"  SKIP (no source URL): {rel_path}")
            continue

        # Create directory
        mkdir_cmd = f"mkdir -p '{ASSETS_BASE}/{dir_path}'"
        run(c, mkdir_cmd, timeout=10)

        # Try each URL until one succeeds
        last_err = None
        for url in urls:
            download_cmd = f"curl -fsSL -o '{full_path}' '{url}'"
            code, out, err = run(c, download_cmd, timeout=180)
            last_err = (out + err).strip()[:200]

            if code == 0:
                code2, out2, _ = run(c, f"test -s '{full_path}' && stat -c '%s' '{full_path}'", timeout=10)
                if code2 == 0 and out2.strip().isdigit() and int(out2.strip()) > 0:
                    created.append(rel_path)
                    print(f"  CREATED: {rel_path} (from {url})")
                    break
                run(c, f"rm -f '{full_path}'", timeout=5)
                last_err = "downloaded but empty or invalid"
            else:
                run(c, f"rm -f '{full_path}'", timeout=5)
        else:
            download_failed.append((rel_path, urls[0], last_err or "unknown"))
            print(f"  FAILED: {rel_path}")

    c.close()

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"  Existed:     {len(existed)}")
    print(f"  Created:     {len(created)}")
    print(f"  No source:   {len(missing_source)}")
    print(f"  Failed:      {len(download_failed)}")

    if existed:
        print("\nAlready on NAS:")
        for p in existed:
            print(f"  - {p}")

    if created:
        print("\nDownloaded to NAS:")
        for p in created:
            print(f"  - {p}")

    if missing_source:
        print("\nNo source URL (copy manually from local/CDN):")
        for p in missing_source:
            print(f"  - {p}")

    if download_failed:
        print("\nDownload failed (mycosoft.org may not have these; use different CDN or copy manually):")
        for path, url, reason in download_failed:
            print(f"  - {path}")
            print(f"    URL: {url}")
            print(f"    Reason: {reason}")

    # Doc: URLs to use if mycosoft.org doesn't have files
    print("\n" + "=" * 60)
    print("SOURCE URL NOTES")
    print("=" * 60)
    print("If mycosoft.org returns 404 for any file, use one of:")
    print("  1. Copy from local dev machine: \\\\192.168.0.105\\mycosoft.com\\website\\assets\\")
    print("  2. Use different CDN (e.g. Vercel Blob, Cloudflare R2) and update script URLs")
    print("  3. Inline videos in Next.js public/ for small files (not recommended for large videos)")
    print("\nKnown gaps:")
    print("  - grok_video_2026-01-22-19-17-42.mp4: custom file, not on mycosoft.org")
    print("  - Other device videos may need manual upload to NAS or CDN")

    sys.exit(0 if not download_failed and not missing_source else 1)


if __name__ == "__main__":
    main()
