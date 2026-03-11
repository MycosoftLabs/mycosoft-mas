"""
Proxmox CLI via SSH — fallback when API auth fails (401).

Runs qm and pvesh commands over SSH as root. Used when Proxmox API
returns 401 and VM_PASSWORD/VM_SSH_PASSWORD works for root@proxmox_host.

Tries paramiko first; if auth fails, falls back to plink (Windows) or ssh.
Hostkey is persisted to config/.proxmox202_hostkey after first extraction.

Date: March 7, 2026
"""
from __future__ import annotations

import json
import logging
import re
import shlex
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger("provision-ssh")

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
HOSTKEY_FILE = REPO_ROOT / "config" / ".proxmox202_hostkey"


def _extract_sha256_hostkey(text: str) -> str | None:
    """Extract SHA256:xxx host key from plink 'host key not cached' output."""
    m = re.search(r"SHA256:([A-Za-z0-9+/=_-]+)", text)
    return f"SHA256:{m.group(1)}" if m else None


def _load_persisted_hostkey() -> str | None:
    """Load hostkey from config/.proxmox202_hostkey if present."""
    if HOSTKEY_FILE.exists():
        try:
            hk = HOSTKEY_FILE.read_text().strip()
            if hk and hk.startswith("SHA256:"):
                return hk
        except Exception as e:
            logger.warning("Could not read hostkey file: %s", e)
    return None


def _save_persisted_hostkey(hostkey: str) -> None:
    """Persist hostkey to config/.proxmox202_hostkey for future runs."""
    try:
        HOSTKEY_FILE.parent.mkdir(parents=True, exist_ok=True)
        HOSTKEY_FILE.write_text(hostkey.strip(), encoding="utf-8")
        logger.info("Persisted hostkey to %s", HOSTKEY_FILE)
    except Exception as e:
        logger.warning("Could not persist hostkey: %s", e)


def _pve_ssh_exec_plink(
    host: str, user: str, password: str, cmd_str: str, timeout: int, hostkey: str | None = None
) -> tuple[bool, str]:
    """Run command via plink (Windows PuTTY). Returns (success, output_or_error).
    Loads hostkey from config/.proxmox202_hostkey if present.
    If hostkey is None and plink fails with 'host key not cached', extracts fingerprint, retries, and persists.
    """
    plink = shutil.which("plink") or shutil.which("plink.exe")
    if not plink:
        return False, "plink not found (install PuTTY or add to PATH)"
    pwd = (password or "").strip().strip('"').strip("'")
    if not pwd:
        return False, "No SSH password provided"

    hk = hostkey or _load_persisted_hostkey()

    def _run(hk_val: str | None, use_stdin: bool = False) -> tuple[bool, str, str]:
        if use_stdin:
            # Pipe password via stdin (-pw -) to avoid special-char interpretation (e.g. !)
            args = [plink, "-batch", "-pw", "-"]
        else:
            args = [plink, "-batch", "-pw", pwd]
        if hk_val:
            args.extend(["-hostkey", hk_val])
        args.extend([f"{user}@{host}", cmd_str])
        try:
            proc = subprocess.run(
                args,
                capture_output=True,
                input=(pwd + "\n") if use_stdin else None,
                text=True,
                timeout=timeout,
                encoding="utf-8",
                errors="replace",
            )
            out = (proc.stdout or "").strip()
            err = (proc.stderr or "").strip()
            combined = f"{out}\n{err}".strip()
            if proc.returncode != 0:
                return False, err or out or f"Exit code {proc.returncode}", combined
            return True, out, combined
        except subprocess.TimeoutExpired:
            return False, "plink timed out", ""
        except Exception as e:
            return False, str(e), ""

    ok, msg, combined = _run(hk)
    if not ok and ("Access denied" in combined or "password" in combined.lower() and "not accepted" in combined.lower()):
        logger.info("Retrying plink with password via stdin (avoids special-char issues)")
        ok, msg, _ = _run(hk, use_stdin=True)
        if ok:
            return True, msg
    if ok:
        return True, msg
    # Retry with extracted hostkey if plink complained about uncached host key
    if not hk and ("host key is not cached" in combined or "Cannot confirm a host key" in combined):
        extracted = _extract_sha256_hostkey(combined)
        if extracted:
            logger.info("Retrying plink with -hostkey %s (stdin password)...", extracted[:32])
            ok, msg, _ = _run(extracted, use_stdin=True)
            if ok:
                _save_persisted_hostkey(extracted)
            return ok, msg
    return False, msg


def _pve_ssh_exec_sshpass(host: str, user: str, password: str, cmd_str: str, timeout: int) -> tuple[bool, str]:
    """Run command via ssh + sshpass (Linux). Returns (success, output_or_error)."""
    ssh = shutil.which("ssh")
    sshpass = shutil.which("sshpass")
    if not ssh:
        return False, "ssh not found"
    if not sshpass:
        return False, "sshpass not found"
    pwd = (password or "").strip().strip('"').strip("'")
    if not pwd:
        return False, "No SSH password provided"
    try:
        proc = subprocess.run(
            ["sshpass", "-p", pwd, "ssh", "-o", "StrictHostKeyChecking=no", "-o", "ConnectTimeout=15",
             f"{user}@{host}", cmd_str],
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding="utf-8",
            errors="replace",
        )
        out = (proc.stdout or "").strip()
        err = (proc.stderr or "").strip()
        if proc.returncode != 0:
            return False, err or out or f"Exit code {proc.returncode}"
        return True, out
    except subprocess.TimeoutExpired:
        return False, "ssh timed out"
    except Exception as e:
        return False, str(e)


def _try_paramiko_connect(
    client: Any,
    host: str,
    user: str,
    password: str | None,
    pkey: Any = None,
    look_for_keys: bool = False,
    allow_agent: bool = False,
) -> bool:
    """Attempt paramiko connect. Returns True if connected."""
    try:
        client.connect(
            host,
            username=user,
            password=password,
            pkey=pkey,
            timeout=15,
            banner_timeout=15,
            auth_timeout=15,
            allow_agent=allow_agent,
            look_for_keys=look_for_keys,
        )
        return True
    except Exception:
        return False


def _load_proxmox202_ssh_key() -> Path | None:
    """Resolve Proxmox 202 SSH key path: PROXMOX202_SSH_KEY env or config/proxmox202_id_rsa."""
    import os
    env_path = os.environ.get("PROXMOX202_SSH_KEY", "").strip()
    if env_path:
        p = Path(env_path).expanduser()
        if p.exists():
            return p
    cfg = REPO_ROOT / "config" / "proxmox202_id_rsa"
    if cfg.exists():
        return cfg
    return None


def pve_ssh_exec(
    host: str,
    user: str,
    password: str,
    cmd: str | list[str],
    timeout: int = 60,
) -> tuple[bool, str]:
    """
    Run command on Proxmox host via SSH. Returns (success, output_or_error).
    cmd can be a string (passed to shell) or list of args (exec'd directly).
    Auth order: 1) PROXMOX202_SSH_KEY / config/proxmox202_id_rsa, 2) password via paramiko,
    3) ~/.ssh keys (id_ed25519, id_rsa), 4) plink/sshpass.
    """
    cmd_str = cmd if isinstance(cmd, str) else " ".join(shlex.quote(str(c)) for c in cmd)
    pwd = (password or "").strip().strip('"').strip("'") or None

    # Try paramiko: first Proxmox-specific key, then password, then ~/.ssh keys
    try:
        import paramiko
    except ImportError:
        pass
    else:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        connected = False
        try:
            # 1) PROXMOX202_SSH_KEY or config/proxmox202_id_rsa
            key_path = _load_proxmox202_ssh_key()
            if key_path:
                for key_cls in [paramiko.Ed25519Key, paramiko.RSAKey]:
                    try:
                        pkey = key_cls.from_private_key_file(str(key_path))
                        if _try_paramiko_connect(
                            client, host, user, None,
                            pkey=pkey, look_for_keys=False, allow_agent=False,
                        ):
                            connected = True
                            logger.info("SSH key auth succeeded (%s)", key_path.name)
                            break
                    except Exception:
                        continue
                if connected:
                    pass  # fall through to exec
            # 2) Password
            if not connected and pwd:
                connected = _try_paramiko_connect(
                    client, host, user, pwd,
                    look_for_keys=False, allow_agent=False,
                )
            if not connected:
                # 3) ~/.ssh keys (file-based)
                ssh_dir = Path.home() / ".ssh"
                key_specs = [
                    ("id_ed25519", paramiko.Ed25519Key),
                    ("id_rsa", paramiko.RSAKey),
                ]
                for key_name, key_cls in key_specs:
                    kp = ssh_dir / key_name
                    if kp.exists():
                        try:
                            pkey = key_cls.from_private_key_file(str(kp))
                        except Exception:
                            continue
                        if _try_paramiko_connect(
                            client, host, user, None,
                            pkey=pkey, look_for_keys=False, allow_agent=False,
                        ):
                            connected = True
                            logger.info("SSH key auth succeeded (%s)", key_name)
                            break
            if not connected:
                # 4) SSH agent + look_for_keys (Pageant, ssh-agent, default keys)
                connected = _try_paramiko_connect(
                    client, host, user, None,
                    pkey=None, look_for_keys=True, allow_agent=True,
                )
                if connected:
                    logger.info("SSH auth succeeded (agent/keys)")
            if connected:
                stdin, stdout, stderr = client.exec_command(cmd_str, timeout=timeout)
                out = (stdout.read() or b"").decode(errors="replace").strip()
                err = (stderr.read() or b"").decode(errors="replace").strip()
                code = stdout.channel.recv_exit_status()
                client.close()
                if code != 0:
                    return False, err or out or f"Exit code {code}"
                return True, out
        except Exception as e:
            err_msg = str(e)
            auth_fail = "Authentication failed" in err_msg or "Auth failed" in err_msg or "password" in err_msg.lower()
            if auth_fail:
                logger.info("Paramiko auth failed, trying plink/ssh fallback: %s", err_msg[:80])
            else:
                return False, err_msg
        finally:
            try:
                client.close()
            except Exception:
                pass

    # Fallback: plink (Windows) or sshpass (Linux) — requires password
    if pwd:
        if sys.platform == "win32":
            ok, out = _pve_ssh_exec_plink(host, user, password, cmd_str, timeout)
            if ok:
                return True, out
            return False, out
        ok, out = _pve_ssh_exec_sshpass(host, user, password, cmd_str, timeout)
        return ok, out
    return False, "No SSH password or key: add PROXMOX202_PASSWORD to .credentials.local, set PROXMOX202_SSH_KEY, or place key at config/proxmox202_id_rsa for root@192.168.0.202"


def pve_ssh_status(
    host: str,
    node: str,
    user: str,
    password: str,
) -> tuple[bool, dict[str, Any] | str]:
    """Get node status via pvesh. Returns (ok, data_or_error)."""
    ok, out = pve_ssh_exec(
        host, user, password,
        ["pvesh", "get", f"/nodes/{node}/status", "--output-format", "json"],
        timeout=15,
    )
    if not ok:
        return False, out
    try:
        return True, json.loads(out)
    except json.JSONDecodeError:
        return False, out


def pve_ssh_list_resources(
    host: str,
    user: str,
    password: str,
) -> tuple[bool, list[dict] | str]:
    """List cluster resources (VMs) via pvesh. Returns (ok, vm_list_or_error)."""
    ok, out = pve_ssh_exec(
        host, user, password,
        ["pvesh", "get", "/cluster/resources", "--type", "vm", "--output-format", "json"],
        timeout=15,
    )
    if not ok:
        return False, out
    try:
        data = json.loads(out)
        return True, data if isinstance(data, list) else []
    except json.JSONDecodeError:
        return False, out


def pve_ssh_clone(
    host: str,
    template_vmid: int,
    newid: int,
    name: str,
    user: str,
    password: str,
    full: int = 1,
    timeout: int = 1800,
) -> tuple[bool, str]:
    """Clone VM/template via qm clone. Returns (ok, message)."""
    # qm clone <vmid> <newid> --name <name> --full 1
    ok, out = pve_ssh_exec(
        host, user, password,
        ["qm", "clone", str(template_vmid), str(newid), "--name", name, f"--full={full}"],
        timeout=timeout,
    )
    return ok, out


def pve_ssh_start(
    host: str,
    vmid: int,
    user: str,
    password: str,
) -> tuple[bool, str]:
    """Start VM via qm start. Returns (ok, message)."""
    ok, out = pve_ssh_exec(host, user, password, ["qm", "start", str(vmid)], timeout=60)
    return ok, out


def pve_ssh_stop(
    host: str,
    vmid: int,
    user: str,
    password: str,
    force: bool = False,
) -> tuple[bool, str]:
    """Stop VM via qm stop. Returns (ok, message)."""
    cmd = ["qm", "stop", str(vmid)]
    if force:
        cmd.append("--skiplock")
    ok, out = pve_ssh_exec(host, user, password, cmd, timeout=60)
    return ok, out


def pve_ssh_scp_put(
    host: str,
    user: str,
    password: str,
    local_path: str | Path,
    remote_path: str,
    timeout: int = 120,
) -> tuple[bool, str]:
    """
    SCP a file to Proxmox host. Returns (ok, message).
    Uses paramiko SFTP if available, else scp/pscp subprocess.
    """
    local_path = Path(local_path)
    if not local_path.exists():
        return False, f"Local file not found: {local_path}"

    pwd = (password or "").strip().strip('"').strip("'") or None

    # Try paramiko SFTP
    try:
        import paramiko
    except ImportError:
        pass
    else:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        connected = False
        try:
            key_path = _load_proxmox202_ssh_key()
            if key_path:
                for key_cls in [paramiko.Ed25519Key, paramiko.RSAKey]:
                    try:
                        pkey = key_cls.from_private_key_file(str(key_path))
                        if _try_paramiko_connect(client, host, user, None, pkey=pkey, look_for_keys=False, allow_agent=False):
                            connected = True
                            break
                    except Exception:
                        continue
            if not connected and pwd:
                connected = _try_paramiko_connect(client, host, user, pwd, look_for_keys=False, allow_agent=False)
            if not connected:
                connected = _try_paramiko_connect(client, host, user, None, pkey=None, look_for_keys=True, allow_agent=True)
            if connected:
                sftp = client.open_sftp()
                sftp.put(str(local_path), remote_path)
                sftp.close()
                client.close()
                return True, f"Uploaded {local_path.name} to {remote_path}"
        except Exception as e:
            if "Authentication failed" not in str(e):
                return False, str(e)
        finally:
            try:
                client.close()
            except Exception:
                pass

    # Fallback: scp (Linux) or pscp (Windows)
    if pwd:
        if sys.platform == "win32":
            pscp = shutil.which("pscp") or shutil.which("pscp.exe")
            if pscp:
                try:
                    proc = subprocess.run(
                        [pscp, "-batch", "-pw", pwd, str(local_path), f"{user}@{host}:{remote_path}"],
                        capture_output=True,
                        text=True,
                        timeout=timeout,
                        encoding="utf-8",
                        errors="replace",
                    )
                    if proc.returncode == 0:
                        return True, f"Uploaded {local_path.name} to {remote_path}"
                    return False, (proc.stderr or proc.stdout or f"Exit {proc.returncode}").strip()
                except Exception as e:
                    return False, str(e)
        else:
            scp = shutil.which("scp")
            sshpass = shutil.which("sshpass")
            if scp and sshpass:
                try:
                    proc = subprocess.run(
                        ["sshpass", "-p", pwd, "scp", "-o", "StrictHostKeyChecking=no", str(local_path), f"{user}@{host}:{remote_path}"],
                        capture_output=True,
                        text=True,
                        timeout=timeout,
                        encoding="utf-8",
                        errors="replace",
                    )
                    if proc.returncode == 0:
                        return True, f"Uploaded {local_path.name} to {remote_path}"
                    return False, (proc.stderr or proc.stdout or f"Exit {proc.returncode}").strip()
                except Exception as e:
                    return False, str(e)
    return False, "SCP failed: no paramiko, and no pscp/scp+sshpass with password"


def pve_ssh_attach_iso_and_set_boot(
    host: str,
    vmid: int,
    iso_volid: str,
    user: str,
    password: str,
) -> tuple[bool, str]:
    """
    Attach ISO to ide2 (CD drive) and set boot order to CD first, then sata0 (disk).
    iso_volid: e.g. "local:iso/Win11_24H2_English_x64.iso"
    Stops VM first if running (required for config change), then starts after.
    Returns (ok, message).
    """
    ide2_val = f"{iso_volid},media=cdrom"
    boot_order = "ide2;sata0"

    ok_stop, stop_out = pve_ssh_stop(host, vmid, user, password, force=True)
    if ok_stop:
        time.sleep(3)
    # VM may already be stopped

    ok, out = pve_ssh_exec(
        host,
        user,
        password,
        ["qm", "set", str(vmid), "--ide2", ide2_val, "--boot", f"order={boot_order}"],
        timeout=30,
    )
    if not ok:
        return False, str(out)

    ok_start, start_out = pve_ssh_exec(host, user, password, ["qm", "start", str(vmid)], timeout=60)
    if not ok_start:
        return True, f"ISO attached, boot order set — VM failed to start: {start_out}"
    return True, f"ISO attached, boot order=ide2;sata0 — VM started. Boot from Windows installer."


def pve_ssh_attach_dual_iso_and_set_boot(
    host: str,
    vmid: int,
    iso_installer: str,
    iso_autounattend: str,
    user: str,
    password: str,
) -> tuple[bool, str]:
    """
    Attach two ISOs for Windows unattended install:
    - ide2: Windows installer (e.g. local:iso/Win10_22H2_English_x64.iso)
    - ide3: autounattend ISO (e.g. local:iso/autounattend_csuite.iso)
    Boot order: ide2;sata0 (installer boots first; Setup reads autounattend from ide3).
    Stops VM first if running, then starts after. Returns (ok, message).
    """
    ide2_val = f"{iso_installer},media=cdrom"
    ide3_val = f"{iso_autounattend},media=cdrom"
    boot_order = "ide2;sata0"

    ok_stop, _ = pve_ssh_stop(host, vmid, user, password, force=True)
    if ok_stop:
        time.sleep(3)

    ok, out = pve_ssh_exec(
        host,
        user,
        password,
        ["qm", "set", str(vmid), "--ide2", ide2_val, "--ide3", ide3_val, "--boot", f"order={boot_order}"],
        timeout=30,
    )
    if not ok:
        return False, str(out)

    ok_start, start_out = pve_ssh_exec(host, user, password, ["qm", "start", str(vmid)], timeout=60)
    if not ok_start:
        return True, f"Dual ISO attached — VM failed to start: {start_out}"
    return True, "Dual ISO attached (ide2=installer, ide3=autounattend). VM started — unattended install in progress."


def pve_ssh_detach_iso(
    host: str,
    vmid: int,
    user: str,
    password: str,
) -> tuple[bool, str]:
    """
    Detach ide2 and ide3 (clear CD drives), set boot order to sata0.
    Stops VM first if running. Does not start VM. Use after install completes, before cloning.
    Returns (ok, message).
    """
    ok_stop, _ = pve_ssh_stop(host, vmid, user, password, force=True)
    if ok_stop:
        time.sleep(3)

    ok, out = pve_ssh_exec(
        host,
        user,
        password,
        ["qm", "set", str(vmid), "--ide2", "none", "--ide3", "none", "--boot", "order=sata0"],
        timeout=30,
    )
    if not ok:
        return False, str(out)
    return True, "ISOs detached, boot order=sata0 (disk)."


def pve_ssh_unlock(
    host: str,
    vmid: int,
    user: str,
    password: str,
) -> tuple[bool, str]:
    """Unlock VM via qm unlock. Returns (ok, message)."""
    ok, out = pve_ssh_exec(host, user, password, ["qm", "unlock", str(vmid)], timeout=10)
    return ok, out


def pve_ssh_destroy(
    host: str,
    vmid: int,
    user: str,
    password: str,
    purge: bool = True,
) -> tuple[bool, str]:
    """Destroy VM via qm destroy. Returns (ok, message)."""
    cmd = ["qm", "destroy", str(vmid)]
    if purge:
        cmd.append("--purge")
    ok, out = pve_ssh_exec(host, user, password, cmd, timeout=120)
    return ok, out


def pve_ssh_create_blank_vm(
    host: str,
    vmid: int,
    name: str,
    spec: dict[str, Any],
    storage: str,
    bridge: str,
    iso_path: str | None,
    description: str,
    user: str,
    password: str,
    ostype: str = "win10",
) -> tuple[bool, str]:
    """
    Create a blank VM via qm create, with optional ISO attached for Windows install.
    Uses SATA for system disk (not VirtIO SCSI) so Windows installer can see the disk
    without external drivers.
    ostype: "win10" (default, works on all hosts) or "win11" (requires TPM, OVMF).
    Returns (ok, message).
    """
    cores = spec.get("cores", 4)
    memory = spec.get("memory_mb", 16384)
    disk_gb = spec.get("disk_gb", 128)
    boot_order = "ide2;sata0" if iso_path else "sata0"
    os_val = "win11" if ostype == "win11" else "win10"
    args = [
        "qm", "create", str(vmid),
        "--name", name,
        "--cores", str(cores),
        "--memory", str(memory),
        "--sockets", "1",
        "--cpu", "host",
        "--ostype", os_val,
        "--agent", "1",
        "--onboot", "1",
        "--sata0", f"{storage}:{disk_gb},discard=on",
        "--net0", f"virtio,bridge={bridge}",
        "--boot", f"order={boot_order}",
    ]
    if iso_path:
        args.extend(["--ide2", f"{iso_path},media=cdrom"])
    args.extend(["--description", shlex.quote(description)])
    ok, out = pve_ssh_exec(host, user, password, " ".join(args), timeout=120)
    if not ok:
        return False, out
    ok2, start_out = pve_ssh_exec(host, user, password, ["qm", "start", str(vmid)], timeout=60)
    if not ok2:
        return True, f"VM {vmid} created but failed to start: {start_out}"
    return True, f"VM {vmid} ({name}) created and started — boot from Windows installer via Proxmox console."


def pve_ssh_set_description(
    host: str,
    vmid: int,
    description: str,
    user: str,
    password: str,
) -> tuple[bool, str]:
    """Set VM description via qm set. Returns (ok, message)."""
    # Escape for shell
    desc = description.replace('"', '\\"')
    ok, out = pve_ssh_exec(
        host, user, password,
        f'qm set {vmid} --description "{desc}"',
        timeout=10,
    )
    return ok, out


def pve_ssh_discover_windows_template(
    host: str,
    user: str,
    password: str,
) -> int | None:
    """
    Discover Windows 11 template from cluster resources via SSH.
    Returns VMID of best match, or None.
    """
    ok, data = pve_ssh_list_resources(host, user, password)
    if not ok or not isinstance(data, list):
        return None
    templates = [v for v in data if v.get("type") == "qemu" and v.get("template")]
    if not templates:
        return None

    def score(v: dict) -> int:
        name = (v.get("name") or "").lower()
        if "win11" in name:
            return 3
        if "windows" in name:
            return 2
        return 1

    best = max(templates, key=score)
    return int(best["vmid"])


def pve_ssh_list_qemu(
    host: str,
    node: str,
    user: str,
    password: str,
) -> tuple[bool, list[dict] | str]:
    """List QEMU VMs on node. Returns (ok, list_or_error)."""
    ok, out = pve_ssh_exec(
        host, user, password,
        ["pvesh", "get", f"/nodes/{node}/qemu", "--output-format", "json"],
        timeout=15,
    )
    if not ok:
        return False, out
    try:
        data = json.loads(out)
        return True, data if isinstance(data, list) else []
    except json.JSONDecodeError:
        return False, out


def pve_ssh_delete_vm(
    host: str,
    vmid: int,
    user: str,
    password: str,
    stop_first: bool = True,
) -> tuple[bool, str]:
    """Stop and destroy VM via SSH. Returns (ok, message)."""
    if stop_first:
        ok_stop, _ = pve_ssh_stop(host, vmid, user, password, force=True)
        if ok_stop:
            time.sleep(2)
    ok, out = pve_ssh_destroy(host, vmid, user, password, purge=True)
    return ok, out
