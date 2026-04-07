"""Pull Nemotron Ollama models on MAS VM 188, set Nemotron env overrides, restart mas-orchestrator.

- Pulls nemotron-3-nano:4b (~3GB). Optionally pulls nemotron-3-super if root fs has >=85G free.
- Writes /etc/systemd/system/mas-orchestrator.service.d/nemotron-ollama.conf (sudo).
- Restarts mas-orchestrator.

Loads VM credentials from .credentials.local.
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import paramiko

REPO = Path(__file__).resolve().parent.parent

NANO_TAG = "nemotron-3-nano:4b"
SUPER_TAG = "nemotron-3-super:latest"
MIN_FREE_GB_FOR_SUPER = 85


def load_creds() -> str:
    p = REPO / ".credentials.local"
    for line in p.read_text().splitlines():
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ[k.strip()] = v.strip()
    pw = os.environ.get("VM_PASSWORD") or os.environ.get("VM_SSH_PASSWORD")
    if not pw:
        raise SystemExit("No VM_PASSWORD / VM_SSH_PASSWORD")
    return pw


def exec_plain(client: paramiko.SSHClient, cmd: str, timeout: float = 120) -> tuple[int, str, str]:
    _, stdout, stderr = client.exec_command(cmd, timeout=int(timeout) + 30)
    out = stdout.read().decode("utf-8", "replace")
    err = stderr.read().decode("utf-8", "replace")
    return stdout.channel.recv_exit_status(), out, err


def sudo_stdin(client: paramiko.SSHClient, pw: str, remote_cmd: str, stdin_payload: bytes | None, timeout: float) -> tuple[int, str, str]:
    stdin, stdout, stderr = client.exec_command(remote_cmd, timeout=int(timeout) + 60)
    stdin.write((pw + "\n").encode("utf-8"))
    if stdin_payload:
        stdin.write(stdin_payload)
    stdin.close()
    out = stdout.read().decode("utf-8", "replace")
    err = stderr.read().decode("utf-8", "replace")
    return stdout.channel.recv_exit_status(), out, err


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    pw = load_creds()
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect("192.168.0.188", username="mycosoft", password=pw, timeout=45)

    _, df_out, _ = exec_plain(c, "df -BG / | tail -1", timeout=20)
    print("Disk:", df_out.strip())
    free_g = 0
    parts = df_out.split()
    if len(parts) >= 4:
        try:
            free_g = int(parts[3].replace("G", ""))
        except ValueError:
            free_g = 0

    print(f"=== sudo ollama pull {NANO_TAG} (may take several minutes) ===")
    code, out, err = sudo_stdin(c, pw, f"sudo -S ollama pull {NANO_TAG}", None, timeout=7200)
    print(out[-8000:] if len(out) > 8000 else out)
    if err.strip():
        print("stderr:", err[-2000:])
    if code != 0:
        print(f"WARN: ollama pull exit {code}")

    if free_g >= MIN_FREE_GB_FOR_SUPER:
        print(f"=== sudo ollama pull {SUPER_TAG} (disk headroom) ===")
        code2, out2, err2 = sudo_stdin(c, pw, f"sudo -S ollama pull {SUPER_TAG}", None, timeout=7200)
        print(out2[-4000:] if len(out2) > 4000 else out2)
        if err2.strip():
            print("stderr:", err2[-1500:])
        if code2 != 0:
            print(f"WARN: super pull exit {code2}")
    else:
        print(f"Skip {SUPER_TAG}: free ~{free_g}G < {MIN_FREE_GB_FOR_SUPER}G")

    _, super_list, _ = exec_plain(c, "ollama list 2>/dev/null | grep nemotron-3-super || true", timeout=30)
    model = SUPER_TAG.strip() if "nemotron-3-super" in super_list else NANO_TAG
    print(f"Role model for CORPORATE/SUPER/NLM/CONSCIOUSNESS: {model}")

    drop_in = f"""# Managed by scripts/_pull_nemotron_mas_188.py — Ollama OpenAI-compat on same host
[Service]
Environment=MYCA_BACKEND_MODE=nemotron
Environment=NEMOTRON_MODEL_CORPORATE={model}
Environment=NEMOTRON_MODEL_SUPER={model}
Environment=NEMOTRON_MODEL_NANO={NANO_TAG}
Environment=NEMOTRON_MODEL_DEVICE={NANO_TAG}
Environment=NEMOTRON_MODEL_INFRA={NANO_TAG}
Environment=NEMOTRON_MODEL_ROUTE={NANO_TAG}
Environment=NEMOTRON_MODEL_NLM={model}
Environment=NEMOTRON_MODEL_CONSCIOUSNESS={model}
"""
    print("=== systemd drop-in nemotron-ollama.conf ===")
    code_m, _, e_m = sudo_stdin(
        c,
        pw,
        "sudo -S mkdir -p /etc/systemd/system/mas-orchestrator.service.d",
        None,
        timeout=60,
    )
    if code_m != 0 and e_m:
        print("mkdir stderr:", e_m[-500:])

    code_t, _, e_t = sudo_stdin(
        c,
        pw,
        "sudo -S tee /etc/systemd/system/mas-orchestrator.service.d/nemotron-ollama.conf > /dev/null",
        drop_in.encode("utf-8"),
        timeout=60,
    )
    if code_t != 0:
        raise SystemExit(f"tee drop-in failed: {e_t}")

    code_d, _, e_d = sudo_stdin(c, pw, "sudo -S systemctl daemon-reload", None, timeout=120)
    if code_d != 0:
        print("daemon-reload stderr:", e_d[-800:])

    ch = c.get_transport().open_session()
    ch.get_pty()
    ch.exec_command("sudo -S systemctl restart mas-orchestrator")
    ch.send(pw + "\n")
    for _ in range(120):
        if ch.exit_status_ready():
            break
        time.sleep(0.25)
    ch.close()

    print("=== Wait for /live ===")
    for attempt in range(48):
        time.sleep(2.5)
        _, live_try, _ = exec_plain(
            c,
            "curl -sS -m 5 -o /dev/null -w '%{http_code}' http://127.0.0.1:8001/live",
            timeout=15,
        )
        if live_try.strip() == "200":
            print(f"/live 200 after ~{(attempt + 1) * 2.5:.0f}s")
            break
    else:
        print("WARN: /live not 200 in time")

    _, st, _ = exec_plain(c, "systemctl is-active mas-orchestrator", timeout=20)
    print("mas-orchestrator:", st.strip())

    _, models, _ = exec_plain(c, "curl -sS http://127.0.0.1:11434/v1/models | head -c 2000", timeout=20)
    print("Ollama /v1/models:", models[:1500])

    c.close()
    print("Done.")


if __name__ == "__main__":
    main()
