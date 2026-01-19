#!/usr/bin/env python3
"""
Mycosoft - Fast Media Sync to Sandbox VM (Paramiko SFTP)
=======================================================

Goal:
- Upload large website media files (mp4/webm/etc) to the VM quickly, without git/docker rebuild.

Default behavior:
- Sync ONLY videos from: WEBSITE/public/assets
- To VM: /opt/mycosoft/media/website/assets

Why:
- Docker builds should not include multi-GB media in the build context.
- Media should be updated independently (instant) via a volume mount.
"""

from __future__ import annotations

import hashlib
import os
import posixpath
import sys
from dataclasses import dataclass
from pathlib import Path

import paramiko

sys.stdout.reconfigure(encoding="utf-8", errors="replace")


@dataclass(frozen=True)
class VmTarget:
    host: str
    username: str
    password: str


VIDEO_EXTS = {".mp4", ".webm", ".mov"}


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def sftp_mkdirs(sftp: paramiko.SFTPClient, remote_dir: str) -> None:
    # Create remote directories like mkdir -p
    parts: list[str] = []
    cur = remote_dir
    while cur not in ("/", ""):
        parts.append(cur)
        cur = posixpath.dirname(cur)
    for d in reversed(parts):
        try:
            sftp.stat(d)
        except FileNotFoundError:
            sftp.mkdir(d)


def should_upload(
    *,
    local_path: Path,
    remote_path: str,
    sftp: paramiko.SFTPClient,
    verify_hash: bool,
) -> tuple[bool, str]:
    try:
        st = sftp.stat(remote_path)
    except FileNotFoundError:
        return True, "missing"

    if st.st_size != local_path.stat().st_size:
        return True, "size-diff"

    if not verify_hash:
        return False, "same-size"

    # Hash compare (more expensive, but still reasonable per-file)
    local_hash = sha256_file(local_path)
    # Download remote file hash by streaming it (avoid temp file)
    h = hashlib.sha256()
    with sftp.open(remote_path, "rb") as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
    remote_hash = h.hexdigest()

    if local_hash != remote_hash:
        return True, "hash-diff"

    return False, "same-hash"


def main() -> int:
    # Local source is outside this MAS repo; keep the default explicit.
    local_assets = Path(r"C:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website\public\assets")
    vm_assets_root = "/opt/mycosoft/media/website/assets"

    target = VmTarget(host="192.168.0.187", username="mycosoft", password="Mushroom1!Mushroom1!")
    verify_hash = False  # speed default; enable when debugging.

    if not local_assets.exists():
        print(f"[ERROR] Local assets folder not found: {local_assets}")
        return 1

    videos: list[Path] = []
    for p in local_assets.rglob("*"):
        if p.is_file() and p.suffix.lower() in VIDEO_EXTS:
            videos.append(p)

    if not videos:
        print(f"[WARN] No video files found under: {local_assets}")
        return 0

    print("============================================================")
    print(" Mycosoft Media Sync (Paramiko SFTP)")
    print("------------------------------------------------------------")
    print(f" Local: {local_assets}")
    print(f" VM   : {target.username}@{target.host}:{vm_assets_root}")
    print(f" Files: {len(videos)} (video only)")
    print("============================================================")

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(target.host, username=target.username, password=target.password, timeout=30)

    sftp = ssh.open_sftp()
    try:
        # Ensure base exists
        sftp_mkdirs(sftp, "/opt/mycosoft/media/website")
        sftp_mkdirs(sftp, vm_assets_root)

        uploaded = 0
        skipped = 0

        for local_file in sorted(videos, key=lambda x: str(x).lower()):
            rel = local_file.relative_to(local_assets).as_posix()
            remote_path = posixpath.join(vm_assets_root, rel)
            remote_dir = posixpath.dirname(remote_path)
            sftp_mkdirs(sftp, remote_dir)

            do_upload, reason = should_upload(
                local_path=local_file, remote_path=remote_path, sftp=sftp, verify_hash=verify_hash
            )
            if not do_upload:
                skipped += 1
                continue

            print(f"[UPLOAD] {rel} ({reason})")
            sftp.put(str(local_file), remote_path)
            uploaded += 1

        print("------------------------------------------------------------")
        print(f"[DONE] uploaded={uploaded} skipped={skipped}")
        print("Next: ensure docker-compose mounts /opt/mycosoft/media/website/assets into website /app/public/assets")
        return 0
    finally:
        try:
            sftp.close()
        except Exception:
            pass
        ssh.close()


if __name__ == "__main__":
    raise SystemExit(main())

