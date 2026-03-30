#!/usr/bin/env python3
"""
One-shot: generate ed25519 deploy key, append public key to Sandbox VM authorized_keys
(password auth), push private key to GitHub secrets (production env + repo) for CI SSH.

Reads VM password from .credentials.local (VM_PASSWORD / VM_SSH_PASSWORD). Never prints secrets.
Requires: paramiko, gh CLI authenticated, ssh-keygen on PATH.
Reachability: direct TCP/22 to Sandbox, or set SSH_BASTION_HOST (e.g. MAS 192.168.0.188).
If direct to 192.168.0.187 fails, retries via 192.168.0.188 unless SSH_AUTO_BASTION_ON_FAILURE=0.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = "MycosoftLabs/website"
DEFAULT_HOST = "192.168.0.187"
DEFAULT_BASTION_ON_DIRECT_FAILURE = "192.168.0.188"


def load_credentials(mas_root: Path) -> None:
    creds = mas_root / ".credentials.local"
    if not creds.exists():
        print("ERROR: .credentials.local not found at", creds, file=sys.stderr)
        sys.exit(1)
    for line in creds.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())


def _connect_via_jump(
    bastion_host: str,
    target_host: str,
    user: str,
    password: str,
    timeout: float = 25,
) -> tuple[paramiko.SSHClient, paramiko.SSHClient]:
    """Return (jump_client, target_client). Caller must close target first, then jump."""
    import paramiko

    jump = paramiko.SSHClient()
    jump.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    jump.connect(
        hostname=bastion_host,
        username=user,
        password=password,
        timeout=timeout,
        allow_agent=False,
        look_for_keys=False,
    )
    transport = jump.get_transport()
    if transport is None:
        jump.close()
        raise RuntimeError(f"no SSH transport on bastion {bastion_host}")

    chan = transport.open_channel(
        "direct-tcpip",
        (target_host, 22),
        ("127.0.0.1", 0),
        timeout=timeout,
    )
    target = paramiko.SSHClient()
    target.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    target.connect(
        hostname=target_host,
        username=user,
        password=password,
        sock=chan,
        timeout=timeout,
        allow_agent=False,
        look_for_keys=False,
    )
    return jump, target


def _connect_sandbox(
    host: str,
    user: str,
    password: str,
) -> tuple[paramiko.SSHClient | None, paramiko.SSHClient]:
    """Return (jump_or_none, client). Close client then jump if jump is not None."""
    import paramiko

    bastion_env = os.environ.get("SSH_BASTION_HOST", "").strip()
    if bastion_env:
        jump, client = _connect_via_jump(bastion_env, host, user, password)
        return jump, client

    direct = paramiko.SSHClient()
    direct.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        direct.connect(
            hostname=host,
            username=user,
            password=password,
            timeout=25,
            allow_agent=False,
            look_for_keys=False,
        )
        return None, direct
    except Exception as e1:
        auto = os.environ.get("SSH_AUTO_BASTION_ON_FAILURE", "1").strip().lower() not in (
            "0",
            "false",
            "no",
        )
        if (
            auto
            and host == DEFAULT_HOST
            and DEFAULT_BASTION_ON_DIRECT_FAILURE
            and DEFAULT_BASTION_ON_DIRECT_FAILURE != host
        ):
            print(
                f"WARN: direct SSH to {host} failed ({e1}); trying bastion "
                f"{DEFAULT_BASTION_ON_DIRECT_FAILURE} (set SSH_AUTO_BASTION_ON_FAILURE=0 to disable).",
                file=sys.stderr,
            )
            try:
                return _connect_via_jump(
                    DEFAULT_BASTION_ON_DIRECT_FAILURE, host, user, password
                )
            except Exception as e2:
                print(f"ERROR: bastion path also failed: {e2}", file=sys.stderr)
                raise e1 from e2
        raise


def main() -> None:
    mas_root = Path(__file__).resolve().parent.parent
    load_credentials(mas_root)

    password = os.environ.get("VM_PASSWORD") or os.environ.get("VM_SSH_PASSWORD") or ""
    if not password:
        print("ERROR: VM_PASSWORD / VM_SSH_PASSWORD empty after loading .credentials.local", file=sys.stderr)
        sys.exit(1)

    host = os.environ.get("SANDBOX_SSH_HOST", DEFAULT_HOST)
    user = os.environ.get("VM_SSH_USER", "mycosoft")

    tmp = Path(tempfile.mkdtemp(prefix="gh_deploy_key_"))
    key_path = tmp / "deploy_ci_ed25519"
    pub_path = key_path.with_suffix(".pub")

    try:
        r = subprocess.run(
            [
                "ssh-keygen",
                "-t",
                "ed25519",
                "-N",
                "",
                "-f",
                str(key_path),
                "-C",
                f"github-actions-deploy-{REPO}",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if r.returncode != 0:
            print("ssh-keygen failed:", r.stderr or r.stdout, file=sys.stderr)
            sys.exit(1)

        pub_line = pub_path.read_text(encoding="utf-8").strip()
        if not pub_line.startswith("ssh-ed25519"):
            print("ERROR: unexpected public key format", file=sys.stderr)
            sys.exit(1)

        try:
            jump, client = _connect_sandbox(host, user, password)
        except Exception as e:
            print(f"ERROR: SSH connect to {user}@{host} failed: {e}", file=sys.stderr)
            sys.exit(1)

        try:
            client.exec_command("mkdir -p ~/.ssh && chmod 700 ~/.ssh")
            stdin, stdout, stderr = client.exec_command("cat ~/.ssh/authorized_keys 2>/dev/null || true")
            existing = stdout.read().decode("utf-8", errors="replace")
            err = stderr.read().decode("utf-8", errors="replace")
            if err and "No such file" not in err.lower():
                pass

            if pub_line not in existing.splitlines():
                sftp = client.open_sftp()
                try:
                    ak_path = ".ssh/authorized_keys"
                    try:
                        with sftp.open(ak_path, "r") as rf:
                            cur = rf.read().decode("utf-8", errors="replace")
                    except OSError:
                        cur = ""
                    new_body = cur.rstrip() + ("\n" if cur.strip() else "") + pub_line + "\n"
                    with sftp.open(ak_path, "w") as wf:
                        wf.write(new_body.encode("utf-8"))
                finally:
                    sftp.close()
                client.exec_command("chmod 600 ~/.ssh/authorized_keys")
                print("OK: appended new public key to ~/.ssh/authorized_keys on", host)
            else:
                print("OK: public key already present in authorized_keys on", host)
        finally:
            client.close()
            if jump is not None:
                jump.close()

        for env_arg in (["--env", "production"], []):
            cmd = [
                "gh",
                "secret",
                "set",
                "SSH_KEY",
                "--repo",
                REPO,
                "--body-file",
                str(key_path),
            ] + env_arg
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            if r.returncode != 0:
                target = "production env" if env_arg else "repository"
                print(f"ERROR: gh secret set SSH_KEY ({target}):", r.stderr or r.stdout, file=sys.stderr)
                sys.exit(1)
            print("OK: GitHub SSH_KEY updated for", target)

        print("Done. Re-run Instant Deploy workflow.")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
