"""SSH 241: run Start-LegionVoice-24x7.ps1 -SkipFirewall from common repo paths."""
from __future__ import annotations

import sys
from pathlib import Path

import paramiko

HOST = "192.168.0.241"
USER = "owner1"
KEY = Path.home() / ".ssh" / "id_ed25519"

# One line: pick first existing script path, then invoke.
RUNNER = (
    r'$p1=Join-Path $env:USERPROFILE "mycosoft-mas\scripts\gpu-node\windows\Start-LegionVoice-24x7.ps1";'
    r'$p2=Join-Path $env:USERPROFILE "Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas\scripts\gpu-node\windows\Start-LegionVoice-24x7.ps1";'
    r'$p3=Join-Path $env:USERPROFILE "Desktop\mycosoft-mas\scripts\gpu-node\windows\Start-LegionVoice-24x7.ps1";'
    r'if (Test-Path $p1) { & $p1 -SkipFirewall }'
    r' elseif (Test-Path $p2) { & $p2 -SkipFirewall }'
    r' elseif (Test-Path $p3) { & $p3 -SkipFirewall }'
    r' else { Write-Output "MISSING_SCRIPT"; exit 2 }'
)


def main() -> None:
    if not KEY.is_file():
        raise SystemExit(f"Missing {KEY}")
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(HOST, username=USER, key_filename=str(KEY), timeout=30)

    cmd = f'powershell -NoProfile -ExecutionPolicy Bypass -Command "{RUNNER}"'
    print("=== Start-LegionVoice-24x7 ===")
    _, o, e = c.exec_command(cmd, timeout=400)
    print((o.read() + e.read()).decode("utf-8", errors="replace")[-12000:])

    print("=== bridge /health ===")
    _, o2, e2 = c.exec_command(
        'powershell -NoProfile -Command "try { '
        '(Invoke-WebRequest -UseBasicParsing -Uri http://127.0.0.1:8999/health -TimeoutSec 12).Content } '
        'catch { $_.Exception.Message }"',
        timeout=25,
    )
    print((o2.read() + e2.read()).decode("utf-8", errors="replace"))

    print("=== netstat LISTENING voice ports ===")
    for port in ("8998", "8999", "11434"):
        _, o3, e3 = c.exec_command(
            f"cmd.exe /c netstat -an | findstr LISTENING | findstr :{port}",
            timeout=15,
        )
        line = (o3.read() + e3.read()).decode("utf-8", "replace").strip()
        if line:
            print(port, line[:200])

    c.close()


if __name__ == "__main__":
    main()
