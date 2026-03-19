"""SSH to a host (Jetson or MYCA workspace VM) and run NemoClaw install + onboard. Loads creds from .credentials.local."""
import argparse
import os
import shlex
import sys
from pathlib import Path

parser = argparse.ArgumentParser(description="Install NemoClaw on Jetson or MYCA workspace VM via SSH")
parser.add_argument("--host", default=None, help="Target IP (default: 192.168.0.123 Jetson, or from .credentials.local)")
parser.add_argument("--user", default=None, help="SSH user (default: jetson for 123, mycosoft for 191)")
parser.add_argument(
    "--skip-curl",
    action="store_true",
    help="Skip nvidia.com/nemoclaw.sh (faster re-run: only Docker check + Node 22 NemoClaw + onboard)",
)
args = parser.parse_args()

creds_path = Path(__file__).resolve().parent.parent / ".credentials.local"
default_ip = "192.168.0.123"
jetson_ip = "192.168.0.123"
jetson_user = "jetson"
jetson_pw = ""
gh_token = ""

if creds_path.exists():
    for line in creds_path.read_text().splitlines():
        if "=" in line and not line.strip().startswith("#"):
            k, v = line.split("=", 1)
            k, v = k.strip(), v.strip()
            if k == "JETSON_IP":
                jetson_ip = v
            elif k == "JETSON_SSH_USER":
                jetson_user = v
            elif k in ("JETSON_SSH_PASSWORD", "VM_SSH_PASSWORD", "VM_PASSWORD"):
                jetson_pw = jetson_pw or v
            elif k in ("GH_TOKEN", "GITHUB_TOKEN", "NEMOCLAW_GH_TOKEN"):
                gh_token = gh_token or v

jetson_pw = jetson_pw or os.environ.get("JETSON_SSH_PASSWORD") or os.environ.get("VM_SSH_PASSWORD") or os.environ.get("VM_PASSWORD", "")
gh_token = gh_token or os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN") or ""

if not jetson_pw:
    print("No Jetson/VM password in .credentials.local or env. Set JETSON_SSH_PASSWORD or VM_PASSWORD.")
    sys.exit(1)

# Target host and user: CLI overrides, else infer from host
target_host = args.host or jetson_ip
if args.user:
    target_user = args.user
elif target_host == "192.168.0.191":
    target_user = "mycosoft"
else:
    target_user = jetson_user

import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
print(f"Connecting to {target_user}@{target_host}...")
client.connect(target_host, username=target_user, password=jetson_pw, timeout=30)

def run(cmd, timeout=300):
    stdin, stdout, stderr = client.exec_command(cmd, get_pty=False)
    out = stdout.read().decode(errors="replace")
    err = stderr.read().decode(errors="replace")
    rc = stdout.channel.recv_exit_status()
    return out, err, rc


def safe_print(s, max_len=8000):
    """Print so Windows console (cp1252) never raises UnicodeEncodeError."""
    if not s:
        return
    s = s[:max_len] + ("..." if len(s) > max_len else "")
    try:
        print(s)
    except UnicodeEncodeError:
        print(s.encode("ascii", errors="replace").decode("ascii"))


# 1) Optional: official installer (Node 20; onboard still needs Node 22 step below)
if args.skip_curl:
    print("Skipping curl installer (--skip-curl).")
else:
    print("Running: curl -fsSL https://nvidia.com/nemoclaw.sh | bash ...")
    o, e, _ = run("curl -fsSL https://nvidia.com/nemoclaw.sh | bash", timeout=600)
    safe_print(o or "(no stdout)")
    if e:
        safe_print("stderr: " + e[:1500])

# Escape single quotes for remote shell: ' -> '\''
_pw_esc = jetson_pw.replace("'", "'\"'\"'")

# 2) Ensure Docker is installed and running (required by NemoClaw onboard)
print("\nChecking for Docker on host ...")
o_which, _, rc_which = run("which docker 2>/dev/null", timeout=10)
_, _, rc_unit = run("systemctl list-unit-files 2>/dev/null | grep -q docker.service", timeout=10)
has_docker = rc_which == 0 or rc_unit == 0

if not has_docker:
    print("Docker not found. Installing Docker (apt + get.docker.com) ...")
    run(f"echo '{_pw_esc}' | sudo -S apt-get update -qq", timeout=120)
    # Try nvidia-container on Jetson; skip or ignore failure on non-Jetson (e.g. MYCA VM)
    o_apt, e_apt, rc_apt = run(f"echo '{_pw_esc}' | sudo -S apt-get install -y nvidia-container curl 2>&1", timeout=300)
    safe_print("nvidia-container/curl install exit=%s" % rc_apt)
    safe_print((o_apt or e_apt or "")[:2000])
    if rc_apt != 0:
        safe_print("Warning: nvidia-container install had non-zero exit (OK on non-Jetson). Continuing with Docker.")
    o_get, e_get, rc_get = run(f"echo '{_pw_esc}' | sudo -S bash -c 'curl -fsSL https://get.docker.com | sh' 2>&1", timeout=600)
    safe_print("get.docker.com exit=%s" % rc_get)
    safe_print((o_get or e_get or "")[:3000])
    if rc_get != 0:
        safe_print("Docker install script failed. Check output above.")
    else:
        run(f"echo '{_pw_esc}' | sudo -S systemctl --now enable docker 2>&1", timeout=30)
        run(f"echo '{_pw_esc}' | sudo -S nvidia-ctk runtime configure --runtime=docker 2>&1", timeout=30)
        run(f"echo '{_pw_esc}' | sudo -S systemctl daemon-reload 2>&1", timeout=15)
        run(f"echo '{_pw_esc}' | sudo -S systemctl restart docker 2>&1", timeout=30)
        print("Docker install and enable completed.")
else:
    print("Docker already present. Starting Docker service ...")
    _start_docker = f"echo '{_pw_esc}' | sudo -S systemctl start docker 2>&1"
    o_d, e_d, rc_d = run(_start_docker, timeout=30)
    safe_print("Docker start exit code: %s" % rc_d)
    safe_print(o_d or "(no stdout)")
    if e_d and "not found" not in e_d.lower():
        safe_print("stderr: " + e_d[:500])

# Verify Docker is actually running
print("\nVerifying Docker status ...")
o_status, e_status, rc_status = run("systemctl is-active docker 2>/dev/null || true", timeout=10)
status_line = (o_status or "").strip()
safe_print("systemctl is-active docker -> exit=%s out=%r" % (rc_status, status_line))
if status_line != "active":
    safe_print("Running 'docker info' to see why ...")
    o_info, e_info, rc_info = run("docker info 2>&1", timeout=10)
    safe_print("docker info exit=%s" % rc_info)
    safe_print((o_info or e_info or "(no output)")[:1000])

import time
time.sleep(3)

# 3) NemoClaw + OpenShell need Node >= 22.12. Reinstall via nvm 22 (official script often uses Node 20).
nemoclaw_bin = f"/home/{target_user}/.npm-global/bin/nemoclaw"
# nvm refuses to run if ~/.npmrc contains prefix/globalconfig — must move it aside for this session.
def _nvm_with_npmrc_stash(inner_bash: str) -> str:
    return (
        'B="$HOME/.npmrc.nemoclawstash.$$"; '
        'trap \'if [ -f "$B" ]; then mv "$B" "$HOME/.npmrc"; fi\' EXIT; '
        '[ -f "$HOME/.npmrc" ] && mv "$HOME/.npmrc" "$B"; '
        + inner_bash
    )


nvm_nemoclaw = _nvm_with_npmrc_stash(
    "set -e; "
    "export NVM_DIR=$HOME/.nvm; "
    "([ -s $NVM_DIR/nvm.sh ] || curl -fsSL https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.4/install.sh | bash); "
    ". $NVM_DIR/nvm.sh; nvm install 22; nvm use 22; "
    "VER=$(nvm version); nvm use --delete-prefix \"$VER\" --silent 2>/dev/null || true; "
    "export PATH=\"$HOME/.nvm/versions/node/$VER/bin:$PATH\"; "
    "node -v; npm install -g git+https://github.com/nvidia/NemoClaw.git"
)
print("\nInstalling/upgrading NemoClaw under Node 22 (required for OpenShell) ...")
o_nvm, e_nvm, rc_nvm = run(f"bash -lc {shlex.quote(nvm_nemoclaw)}", timeout=900)
safe_print("nvm22 + NemoClaw install exit=%s" % rc_nvm)
safe_print((o_nvm or e_nvm or "")[:6000])
if rc_nvm != 0:
    print("Warning: Node 22 NemoClaw install had errors; onboard may still fail.")

# 4) Onboard: GH_TOKEN needed for OpenShell CLI download (gh API). Pass via temp file (no token in argv).
if not gh_token:
    print(
        "\nNote: No GH_TOKEN/GITHUB_TOKEN in .credentials.local or env. "
        "OpenShell install may fail. Add GH_TOKEN=<pat> to .credentials.local and re-run."
    )

print("\nRunning: nemoclaw onboard (non-interactive, Node 22) ...")
_onboard_core = (
    "set -e; export NVM_DIR=$HOME/.nvm && . $NVM_DIR/nvm.sh && nvm use 22 && "
    "VER=$(nvm version) && nvm use --delete-prefix \"$VER\" --silent 2>/dev/null || true && "
    "export PATH=\"$HOME/.nvm/versions/node/$VER/bin:$PATH\" && "
    "command -v nemoclaw && NON_INTERACTIVE=1 nemoclaw onboard --non-interactive"
)
onboard_inner = _nvm_with_npmrc_stash(_onboard_core)
if gh_token:
    tok_path = f"/home/{target_user}/.nemoclaw_gh_token_tmp"
    try:
        sftp = client.open_sftp()
        with sftp.file(tok_path, "w") as f:
            f.write(gh_token)
        sftp.chmod(tok_path, 0o600)
        sftp.close()
    except Exception as ex:
        safe_print("SFTP token write failed: %s" % ex)
        tok_path = None
    if tok_path:
        onboard_inner = (
            f"export GH_TOKEN=$(cat {tok_path}) && rm -f {tok_path} && " + onboard_inner
        )

o2, e2, rc2 = run(f"bash -lc {shlex.quote(onboard_inner)}", timeout=600)
if rc2 != 0 and "unknown option" in ((e2 or "") + (o2 or "")).lower():
    fallback = onboard_inner.replace(" onboard --non-interactive", " onboard")
    o2, e2, rc2 = run(f"bash -lc {shlex.quote(fallback)}", timeout=600)
safe_print("nemoclaw onboard exit code: %s" % rc2)
safe_print(o2 or "(no stdout)")
if e2:
    safe_print("stderr: " + e2[:1500])

client.close()
print("\nDone.")
