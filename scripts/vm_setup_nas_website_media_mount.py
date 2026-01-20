#!/usr/bin/env python3
"""Mount NAS SMB share on the sandbox VM at /opt/mycosoft/media/website/assets.

This makes website media deploys instant: copy files to NAS, and the website serves them via the bind mount.

Requirements (provide via args):
  --nas-host        (e.g. 192.168.0.50)
  --share           (e.g. mycosoft-media)
  --subpath         (e.g. website/assets)  [optional]
  --username / --password (or --guest)
"""

from __future__ import annotations

import argparse
import shlex
import sys

import paramiko

VM_IP = "192.168.0.187"
VM_USER = "mycosoft"
VM_PASS = "REDACTED_VM_SSH_PASSWORD"

MOUNTPOINT = "/opt/mycosoft/media/website/assets"
CREDS_FILE = "/etc/samba/mycosoft-nas.creds"
FSTAB_MARKER = "# mycosoft-nas-assets"


def run(ssh: paramiko.SSHClient, cmd: str) -> str:
    stdin, stdout, stderr = ssh.exec_command(cmd)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    return (out + ("\n" + err if err.strip() else "")).strip()


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    ap = argparse.ArgumentParser()
    ap.add_argument("--nas-host", required=True)
    ap.add_argument("--share", required=True)
    ap.add_argument("--subpath", default="")
    ap.add_argument("--username")
    ap.add_argument("--password")
    ap.add_argument("--guest", action="store_true")
    args = ap.parse_args()

    if not args.guest and (not args.username or not args.password):
        raise SystemExit("Provide --guest OR (--username and --password).")

    # SMB source path: //host/share[/subpath]
    smb_source = f"//{args.nas_host}/{args.share}"
    if args.subpath:
        smb_source = smb_source.rstrip("/") + "/" + args.subpath.strip("/")

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(VM_IP, username=VM_USER, password=VM_PASS, timeout=30)

    print("[1] Install cifs-utils")
    print(run(ssh, "sudo apt-get update -y && sudo apt-get install -y cifs-utils"))

    print("\n[2] Create mountpoint")
    print(run(ssh, f"sudo mkdir -p {shlex.quote(MOUNTPOINT)} && sudo chown -R mycosoft:mycosoft /opt/mycosoft/media || true"))

    if args.guest:
        print("\n[3] Configure guest mount (no creds file)")
        mount_opts = "guest,vers=3.0,iocharset=utf8,file_mode=0644,dir_mode=0755,nofail,_netdev"
        fstab_line = f"{smb_source} {MOUNTPOINT} cifs {mount_opts} 0 0"
    else:
        print("\n[3] Write credentials file")
        user = args.username.replace("'", "'\"'\"'")
        pw = args.password.replace("'", "'\"'\"'")
        print(
            run(
                ssh,
                "sudo install -d -m 0700 /etc/samba && "
                + f"sudo bash -lc 'cat > {CREDS_FILE} <<EOF\nusername={user}\npassword={pw}\nEOF\nchmod 600 {CREDS_FILE}'",
            )
        )
        mount_opts = f"credentials={CREDS_FILE},vers=3.0,iocharset=utf8,uid=mycosoft,gid=mycosoft,file_mode=0644,dir_mode=0755,nofail,_netdev"
        fstab_line = f"{smb_source} {MOUNTPOINT} cifs {mount_opts} 0 0"

    print("\n[4] Update /etc/fstab (idempotent)")
    escaped = fstab_line.replace("'", "'\"'\"'")
    print(
        run(
            ssh,
            "sudo bash -lc "
            + shlex.quote(
                f"grep -q '{FSTAB_MARKER}' /etc/fstab || echo '{FSTAB_MARKER}' >> /etc/fstab; "
                f"grep -q \"{escaped}\" /etc/fstab || echo \"{escaped}\" >> /etc/fstab"
            ),
        )
    )

    print("\n[5] Mount now")
    print(run(ssh, "sudo mount -a || true; mount | grep -i cifs || true"))

    print("\n[6] Verify directory listing")
    print(run(ssh, f"ls -la {shlex.quote(MOUNTPOINT)} | head -n 60 || true"))

    ssh.close()


if __name__ == "__main__":
    main()

