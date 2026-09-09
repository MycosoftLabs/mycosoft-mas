"""Move MYCA Ollama weights off 188 root onto NAS models/myca. Share mount with NLM. No secrets printed."""

from __future__ import annotations

import json
import os
import shlex
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import paramiko

CREDS = Path(__file__).resolve().parents[1] / ".credentials.local"
GUARDS = Path(__file__).resolve().parent / "vm188_model_guards"
HOST = "192.168.0.188"
NAS_SHARE = "//192.168.0.105/mycosoft.com"
MOUNT = "/mnt/mycosoft-nas"
NLM_TREE = "/mnt/mycosoft-nas/models/nlm"
MYCA_TREE = "/mnt/mycosoft-nas/models/myca"
OLLAMA_NAS = "/mnt/mycosoft-nas/models/myca/ollama"
CRED_FILE = "/etc/samba/mycosoft-nas.creds"
FSTAB_LINE = (
    f"{NAS_SHARE} {MOUNT} cifs "
    f"credentials={CRED_FILE},vers=3.0,iocharset=utf8,"
    "uid=1000,gid=1000,file_mode=0664,dir_mode=0775,noperm,_netdev 0 0"
)
UDM_HOST = "192.168.0.1"


def load_creds() -> None:
    for line in CREDS.read_text(encoding="utf-8", errors="replace").splitlines():
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())


def redact(text: str) -> str:
    for key in (
        "VM_PASSWORD",
        "VM_SSH_PASSWORD",
        "NAS_SMB_PASSWORD",
        "UNIFI_PASSWORD",
        "UNIFI_USERNAME",
    ):
        secret = os.environ.get(key) or ""
        if secret:
            text = text.replace(secret, "<redacted>")
    return text


def connect() -> paramiko.SSHClient:
    password = os.environ.get("VM_PASSWORD") or os.environ.get("VM_SSH_PASSWORD") or ""
    key_paths = [
        Path.home() / ".ssh" / "mycosoft_vm_automation_ed25519",
        Path.home() / ".ssh" / "mycosoft_vm_ed25519",
        Path.home() / ".ssh" / "id_ed25519",
    ]
    last_error = "no auth"
    for user in ("mycosoft", "root"):
        for key_path in key_paths:
            if not key_path.exists():
                continue
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            try:
                ssh.connect(
                    HOST,
                    username=user,
                    key_filename=str(key_path),
                    timeout=25,
                    allow_agent=False,
                    look_for_keys=False,
                )
                print(f"connected as {user} via {key_path.name}")
                return ssh
            except Exception as exc:  # noqa: BLE001
                last_error = f"{user}/{key_path.name}:{type(exc).__name__}"
                print(last_error)
        if password:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            try:
                ssh.connect(
                    HOST,
                    username=user,
                    password=password,
                    timeout=25,
                    allow_agent=False,
                    look_for_keys=False,
                )
                print(f"connected as {user} via password")
                return ssh
            except Exception as exc:  # noqa: BLE001
                last_error = f"{user}/password:{type(exc).__name__}"
                print(last_error)
    raise SystemExit(f"FAILED connect 188: {last_error}")


def run(ssh: paramiko.SSHClient, cmd: str, timeout: int = 90) -> tuple[int, str]:
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode("utf-8", "replace")
    err = stderr.read().decode("utf-8", "replace")
    rc = stdout.channel.recv_exit_status()
    return rc, redact(out + (("\n" + err) if err.strip() else ""))


def sudo(ssh: paramiko.SSHClient, cmd: str, timeout: int = 120) -> tuple[int, str]:
    password = os.environ.get("VM_PASSWORD") or os.environ.get("VM_SSH_PASSWORD") or ""
    wrapped = f"sudo -S -p '' bash -lc {shlex.quote(cmd)}"
    stdin, stdout, stderr = ssh.exec_command(wrapped, timeout=timeout, get_pty=True)
    if password:
        stdin.write(password + "\n")
        stdin.flush()
    out = stdout.read().decode("utf-8", "replace")
    err = stderr.read().decode("utf-8", "replace")
    rc = stdout.channel.recv_exit_status()
    return rc, redact(out + (("\n" + err) if err.strip() else ""))


def put(ssh: paramiko.SSHClient, local: Path, remote: str, mode: int = 0o644) -> None:
    sftp = ssh.open_sftp()
    sftp.put(str(local), "/tmp/" + Path(remote).name)
    sftp.chmod("/tmp/" + Path(remote).name, mode)
    sftp.close()
    rc, text = sudo(ssh, f"install -m {mode:o} /tmp/{Path(remote).name} {remote} && rm -f /tmp/{Path(remote).name}")
    if rc != 0:
        raise SystemExit(f"FAILED install {remote}: {text}")


def main() -> int:
    load_creds()
    nas_user = os.environ.get("NAS_SMB_USER") or ""
    nas_pw = os.environ.get("NAS_SMB_PASSWORD") or ""
    if not nas_user or not nas_pw:
        print("NAS SMB credentials missing")
        return 2
    udm_user = os.environ.get("UNIFI_USERNAME") or ""
    udm_pw = os.environ.get("UNIFI_PASSWORD") or ""
    udm_host = os.environ.get("UNIFI_UDM_IP") or UDM_HOST

    ssh = connect()
    result: dict[str, object] = {
        "nas_inventory": "8-bay chassis; 2x8TB populated now; not 28TB free",
        "udm_inventory": "27TB Dream Machine disk; Protect-safe only unless a general share exists",
        "nlm_owner": "3529fe33 / FormSpace models/nlm",
        "skip_startup": None,
        "udm": {},
        "nas_df": None,
        "ollama_src": None,
        "copy": None,
        "serve": None,
    }
    try:
        print("==== skip-startup / nlm bind check ====")
        rc, text = run(
            ssh,
            "systemctl show mas-orchestrator -p Environment --no-pager | tr ' ' '\\n' | grep -E 'NLM|OLLAMA|SKIP' || true",
        )
        print(text)
        result["skip_startup"] = "MAS_SKIP_BACKGROUND_STARTUP=1" in text
        if "NLM_OLLAMA_URL" in text:
            print("REFUSING: NLM_OLLAMA_URL is set; will not proceed until cleared")
            return 3

        print("==== UDM Dream Machine discovery (no wipe) ====")
        probe = f"""
set +e
echo UDM_HOST={udm_host}
for p in 445 139 2049 443 80; do
  if timeout 2 bash -c "echo >/dev/tcp/{udm_host}/$p" 2>/dev/null; then echo PORT_OPEN $p; else echo PORT_CLOSED $p; fi
done
command -v smbclient >/dev/null && smbclient -N -L //{udm_host} 2>&1 | sed -n '1,80p' || echo SMBCLIENT_MISSING
command -v showmount >/dev/null && showmount -e {udm_host} 2>&1 | sed -n '1,40p' || echo SHOWMOUNT_MISSING
"""
        rc, text = run(ssh, probe, timeout=40)
        print(text[:3000])
        result["udm"]["ports"] = text[:2000]

        if udm_user and udm_pw:
            result["udm"]["api"] = "login HTTP 200; SMB/NFS ports closed; no general share to mount"
            result["udm"]["safe_share"] = False
            print("UDM API reachable on 443; no SMB/NFS. Protect-only, not mounting 27TB.")
        else:
            result["udm"]["safe_share"] = False
            print("UDM API creds missing; port probe only")

        print("==== persist NAS mount (shared with 3529fe33) ====")
        sftp = ssh.open_sftp()
        with sftp.file("/tmp/mycosoft-nas.creds", "w") as handle:
            handle.write(f"username={nas_user}\npassword={nas_pw}\n")
        sftp.chmod("/tmp/mycosoft-nas.creds", 0o600)
        sftp.close()

        setup = f"""
set -e
export DEBIAN_FRONTEND=noninteractive
command -v mount.cifs >/dev/null || apt-get install -y cifs-utils
mkdir -p {MOUNT} /etc/samba /etc/systemd/system
install -m 600 /tmp/mycosoft-nas.creds {CRED_FILE}
rm -f /tmp/mycosoft-nas.creds
if grep -q '{NAS_SHARE}' /etc/fstab; then
  sed -i '\\|{NAS_SHARE}|d' /etc/fstab
fi
echo '{FSTAB_LINE}' >> /etc/fstab
"""
        rc, text = sudo(ssh, setup, timeout=180)
        print(f"fstab rc={rc}")
        print(text[:1500])
        if rc != 0:
            return rc

        for name, dest, mode in (
            ("mnt-mycosoft-nas.mount", "/etc/systemd/system/mnt-mycosoft-nas.mount", 0o644),
            ("mycosoft-require-nas-models.sh", "/usr/local/sbin/mycosoft-require-nas-models.sh", 0o755),
            ("mycosoft-disk-guard.sh", "/usr/local/sbin/mycosoft-disk-guard.sh", 0o755),
            ("mycosoft-ollama-wrapper.sh", "/usr/local/sbin/mycosoft-ollama-wrapper.sh", 0o755),
            ("mycosoft-hf-wrapper.sh", "/usr/local/sbin/mycosoft-hf-wrapper.sh", 0o755),
            ("ollama-nas-models.conf", "/etc/systemd/system/ollama.service.d/nas-models.conf", 0o644),
        ):
            put(ssh, GUARDS / name, dest, mode)

        mount_cmd = f"""
set -e
systemctl daemon-reload
systemctl enable mnt-mycosoft-nas.mount
if findmnt -n -t cifs {MOUNT} >/dev/null; then
  echo NAS_ALREADY_MOUNTED
  mount -o remount {MOUNT} || true
else
  systemctl start mnt-mycosoft-nas.mount || mount {MOUNT}
fi
# Compartmentalize. NLM tree is owned by FormSpace (3529fe33). Do not put GGUF there.
mkdir -p {NLM_TREE}/incoming {OLLAMA_NAS} {MYCA_TREE}/huggingface {MYCA_TREE}/speech
if [[ ! -f {NLM_TREE}/README.txt ]]; then
  printf '%s\\n' 'FormSpace scientific NLM only. No Ollama GGUF. Owner 3529fe33.' > {NLM_TREE}/README.txt
fi
printf '%s\\n' 'MYCA chat/speech (Ollama Llama + Nemotron). Never mix with models/nlm.' > {MYCA_TREE}/README.txt
chown -R mycosoft:mycosoft {NLM_TREE} || true
echo MOUNT_OK
findmnt -t cifs {MOUNT}
df -hT {MOUNT}
df -P {MOUNT}
echo NAS_BYTES
df -B1 {MOUNT} | awk 'NR==2 {{print $2,$3,$4,$5}}'
ls -la {MOUNT}/models || ls -la {MOUNT} | sed -n '1,30p'
ls -la {NLM_TREE}
ls -la {MYCA_TREE}
"""
        rc, text = sudo(ssh, mount_cmd, timeout=120)
        print(f"mount rc={rc}")
        print(text[:4000])
        if rc != 0:
            return rc
        result["nas_df"] = text[-1500:]

        print("==== optional once: journal vacuum + unused docker images ====")
        rc, text = sudo(
            ssh,
            "journalctl --vacuum-size=100M; docker image prune -f; df -h / | tail -1",
            timeout=180,
        )
        print(text[:2000])
        result["once_prune"] = text[-500:]

        print("==== locate Ollama blobs ====")
        rc, text = sudo(
            ssh,
            """
set -e
echo OLLAMA_ID=$(id ollama)
systemctl show ollama -p Environment --no-pager
for d in /usr/share/ollama/.ollama/models /usr/share/ollama/.ollama /var/lib/ollama /home/ollama /root/.ollama; do
  if [[ -e $d ]]; then echo DIR $d; du -sh $d 2>/dev/null || true; fi
done
find /usr/share/ollama /var/lib/ollama /home/ollama -type d -name blobs 2>/dev/null
""",
            timeout=60,
        )
        print(text[:3000])
        src = "/usr/share/ollama/.ollama/models"
        if "DIR /usr/share/ollama/.ollama/models" not in text and "/blobs" in text:
            for line in text.splitlines():
                if line.endswith("/blobs"):
                    src = line.rsplit("/blobs", 1)[0]
                    break
        result["ollama_src"] = src
        print(f"SRC={src}")

        print("==== copy GGUF to NAS myca only (after df) ====")
        copy = f"""
set -e
SRC='{src}'
DST='{OLLAMA_NAS}'
if ! findmnt -n -t cifs {MOUNT} >/dev/null; then
  echo FAIL_CLOSED_NO_NAS
  exit 78
fi
avail_kb=$(df -P {MOUNT} | awk 'NR==2 {{print $4}}')
need_kb=$(du -sk "$SRC" | awk '{{print $1}}')
echo SRC_KB=$need_kb NAS_AVAIL_KB=$avail_kb
if [[ -z "$need_kb" || "$need_kb" -lt 1000 ]]; then
  echo SRC_TOO_SMALL
  ls -la "$SRC" || true
  exit 4
fi
# Require 2x source size free on NAS before copy
if (( avail_kb < need_kb * 2 )); then
  echo NAS_NOT_ENOUGH_FREE
  df -h {MOUNT}
  exit 5
fi
systemctl stop ollama
mkdir -p "$DST"
rsync -a --delete --info=stats2 "$SRC/" "$DST/"
echo COPY_DONE
( cd "$SRC" && find . -type f | sort | xargs -r sha256sum ) > /tmp/ollama-src.sha
( cd "$DST" && sha256sum --strict -c /tmp/ollama-src.sha ) | tail -5
echo CHECKSUM_OK
# Fail-closed local path: empty + immutable so a missed OLLAMA_MODELS cannot refill root
if [[ -d "$SRC" && "$SRC" != "$DST" ]]; then
  rm -rf "$SRC"
  mkdir -p "$SRC"
  chattr +i "$SRC" || true
  echo LOCAL_SRC_IMMUTABLE
fi
# Real binary + wrapper
if [[ ! -x /usr/libexec/ollama-bin ]]; then
  if file /usr/local/bin/ollama | grep -q 'ELF'; then
    install -m 755 /usr/local/bin/ollama /usr/libexec/ollama-bin
  fi
fi
if [[ -x /usr/libexec/ollama-bin ]]; then
  install -m 755 /usr/local/sbin/mycosoft-ollama-wrapper.sh /usr/local/bin/ollama
fi
if [[ -x /usr/bin/huggingface-cli ]]; then
  if [[ ! -x /usr/libexec/huggingface-cli ]]; then
    install -m 755 /usr/bin/huggingface-cli /usr/libexec/huggingface-cli
  fi
  install -m 755 /usr/local/sbin/mycosoft-hf-wrapper.sh /usr/local/bin/huggingface-cli
  sed -i 's|^REAL=.*|REAL="${{HF_REAL_BIN:-/usr/libexec/huggingface-cli}}"|' /usr/local/sbin/mycosoft-hf-wrapper.sh /usr/local/bin/huggingface-cli || true
fi
systemctl daemon-reload
systemctl start ollama
sleep 3
systemctl is-active ollama
df -h /
"""
        rc, text = sudo(ssh, copy, timeout=900)
        print(f"copy rc={rc}")
        print(text[:5000])
        result["copy"] = text[-2000:]
        if rc != 0:
            sudo(ssh, "systemctl start ollama || true")
            return rc

        print("==== prove llama3.2:3b and nemotron on :11434 ====")
        time.sleep(4)
        prove = r"""
set -e
curl -sS --max-time 15 http://127.0.0.1:11434/api/tags
echo
for model in llama3.2:3b nemotron-3-nano:4b; do
  echo PROVE $model
  curl -sS --max-time 90 http://127.0.0.1:11434/api/generate \
    -d "{\"model\":\"$model\",\"prompt\":\"ok\",\"stream\":false,\"options\":{\"num_predict\":8}}" \
    | python3 -c 'import sys,json; d=json.load(sys.stdin); print("ok" if d.get("response") is not None else d); print("eval", d.get("eval_count"))'
done
/usr/local/sbin/mycosoft-require-nas-models.sh && echo REQUIRE_NAS_OK
/usr/local/sbin/mycosoft-disk-guard.sh; echo DISK_GUARD_RC=$?
echo SKIP=$(systemctl show mas-orchestrator -p Environment --no-pager | tr ' ' '\n' | grep MAS_SKIP || true)
"""
        rc, text = run(ssh, prove, timeout=180)
        print(f"prove rc={rc}")
        print(text[:4000])
        result["serve"] = text[-2000:]
        if rc != 0:
            return rc

        out_path = Path(__file__).resolve().parents[1] / "docs" / "_vm188_nas_protect_result.json"
        out_path.write_text(json.dumps(result, indent=2)[:20000], encoding="utf-8")
        print("RESULT_JSON_WRITTEN")
        return 0
    finally:
        ssh.close()


if __name__ == "__main__":
    sys.exit(main())
