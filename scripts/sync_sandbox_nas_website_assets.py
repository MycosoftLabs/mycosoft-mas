#!/usr/bin/env python3
"""
Sync WEBSITE/website/public/assets → Sandbox 192.168.0.187
/opt/mycosoft/media/website/assets (NAS-backed; bind-mounted as /app/public/assets in the website container).

Production Docker uses:
  -v /opt/mycosoft/media/website/assets:/app/public/assets:ro
so media must exist on the VM; files only in the git image are hidden at runtime.

The destination tree is often not writable as user `mycosoft` over SFTP; this script
uploads to ~/website-assets-staging then `sudo rsync` into the NAS path.

After upload, calls website _cloudflare_cache.purge_everything() when creds are set.
"""
from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

import paramiko

# Script lives at .../mycosoft-mas/scripts/; repo parent is MAS, grandparent is CODE
REPO_ROOT = Path(__file__).resolve().parent.parent
CODE_ROOT = REPO_ROOT.parents[1]
DEFAULT_ASSETS = CODE_ROOT / "WEBSITE" / "website" / "public" / "assets"
REMOTE_ROOT = "/opt/mycosoft/media/website/assets"
STAGING = "/home/mycosoft/website-assets-staging"
HOST = os.environ.get("SANDBOX_VM_IP", "192.168.0.187")
USER = os.environ.get("VM_SSH_USER", "mycosoft")


def load_creds() -> None:
    for p in (
        REPO_ROOT / ".credentials.local",
        CODE_ROOT / "WEBSITE" / "website" / ".credentials.local",
        Path.home() / ".mycosoft-credentials",
    ):
        if not p.is_file():
            continue
        for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
            if not line or line.strip().startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            k, v = k.strip(), v.strip().strip("'\"")
            if k and k not in os.environ:
                os.environ[k] = v


def sftp_ensure_dir(sftp: paramiko.SFTPClient, remote_dir: str) -> None:
    """mkdir -p on remote (POSIX)."""
    parts = [p for p in remote_dir.split("/") if p]
    cur = ""
    for p in parts:
        cur = f"{cur}/{p}" if cur else f"/{p}"
        try:
            sftp.stat(cur)
        except (OSError, IOError, FileNotFoundError):
            sftp.mkdir(cur)


def run_sudo(ssh: paramiko.SSHClient, password: str, cmd: str, timeout: int = 3600) -> int:
    """Run `sudo -S` with password on stdin; `cmd` is the argument after sudo (no sudo word)."""
    full_cmd = f"sudo -S {cmd}"
    stdin, stdout, stderr = ssh.exec_command(full_cmd, get_pty=True, timeout=timeout)
    stdin.write(password + "\n")
    stdin.channel.shutdown_write()
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    code = stdout.channel.recv_exit_status()
    if code != 0:
        print(f"sudo failed (exit {code})")
        if out.strip():
            print(out[-4000:])
        if err.strip():
            print("STDERR:", err[-4000:])
    return code


def collect_files(assets: Path) -> list[Path]:
    sub = os.environ.get("MYCOSOFT_ASSET_SUBDIRS", "").strip()
    if not sub:
        return sorted(p for p in assets.rglob("*") if p.is_file())
    out: list[Path] = []
    for name in sub.split():
        p = assets / name
        if p.is_file():
            out.append(p)
        elif p.is_dir():
            out.extend(f for f in p.rglob("*") if f.is_file())
    return sorted(out)


def main() -> int:
    load_creds()
    password = os.environ.get("VM_PASSWORD") or os.environ.get("VM_SSH_PASSWORD") or ""
    if not password:
        print("ERROR: VM_PASSWORD / VM_SSH_PASSWORD (see .credentials.local)")
        return 1

    assets = Path(
        os.environ.get("MYCOSOFT_WEBSITE_ASSETS", str(DEFAULT_ASSETS)),
    ).resolve()
    if not assets.is_dir():
        print(f"ERROR: not a directory: {assets}")
        return 1

    files = collect_files(assets)
    if not files:
        print("ERROR: no files to upload")
        return 1

    print(
        f"Uploading {len(files)} file(s) from {assets} to {USER}@{HOST}:{STAGING}/ "
        f"then sudo rsync -> {REMOTE_ROOT}/",
    )
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(HOST, username=USER, password=password, timeout=60, banner_timeout=60)
    t = ssh.get_transport()
    if t:
        t.set_keepalive(20)

    _, o_init, e_init = ssh.exec_command(
        f"rm -rf {STAGING} && mkdir -p {STAGING} && echo ok",
        timeout=120,
    )
    o_init.read()
    e_init.read()
    if o_init.channel.recv_exit_status() != 0:
        print("ERROR: could not reset staging directory")
        ssh.close()
        return 1

    sftp = ssh.open_sftp()
    try:
        n = 0
        tot = 0
        for p in files:
            rel = p.relative_to(assets).as_posix()
            remote = f"{STAGING.rstrip('/')}/{rel}"
            parent = str(Path(remote).parent).replace("\\", "/")
            sftp_ensure_dir(sftp, parent)
            sftp.put(str(p), remote)
            n += 1
            tot += p.stat().st_size
            if n == 1 or n % 40 == 0 or n == len(files):
                print(f"  {n}/{len(files)}  (latest: {rel})")
    finally:
        sftp.close()

    print("Running sudo rsync to NAS mount (may take several minutes for large video)...")
    # trailing slashes: merge tree into target
    rc = run_sudo(
        ssh,
        password,
        f"rsync -a {STAGING}/ {REMOTE_ROOT}/",
        timeout=7200,
    )
    ssh.exec_command(f"rm -rf {STAGING}", timeout=120)
    ssh.close()
    if rc != 0:
        return rc
    print(f"OK: {n} files staged, ~{tot / (1024 * 1024):.1f} MB")

    wsite = CODE_ROOT / "WEBSITE" / "website"
    cf = wsite / "_cloudflare_cache.py"
    if cf.is_file():
        spec = importlib.util.spec_from_file_location("cfc", cf)
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)  # type: ignore[union-attr]
            if hasattr(mod, "purge_everything"):
                mod.purge_everything()  # type: ignore[misc]
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
