#!/usr/bin/env python3
"""Update Gemini key on VM 188 and restart MAS container."""
import os
import paramiko
import time
from pathlib import Path

creds = Path(__file__).parent.parent / ".credentials.local"
for line in creds.read_text().splitlines():
    if line and not line.startswith("#") and "=" in line:
        k, v = line.split("=", 1)
        os.environ[k.strip()] = v.strip()

pw = os.environ.get("VM_SSH_PASSWORD") or os.environ.get("VM_PASSWORD")
client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect("192.168.0.188", username="mycosoft", password=pw, timeout=30)

ENV_PATH = "/home/mycosoft/mycosoft/mas/.env"

def run(cmd, timeout=30):
    stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode(errors="replace")
    err = stderr.read().decode(errors="replace")
    rc = stdout.channel.recv_exit_status()
    return (out + err).strip(), rc

# Read existing .env and replace GEMINI_API_KEY
NEW_KEY = "AIzaSyBH0m35MF2Qj2y5L17xVBlZwwr2jG9jvyw"
out, _ = run(f"cat {ENV_PATH}")
lines = out.splitlines()

updated = False
for i, line in enumerate(lines):
    if line.startswith("GEMINI_API_KEY="):
        lines[i] = f"GEMINI_API_KEY={NEW_KEY}"
        updated = True
        break

if not updated:
    lines.append(f"GEMINI_API_KEY={NEW_KEY}")

new_env = "\n".join(lines) + "\n"

# Write back via tee (avoids heredoc quoting issues)
import tempfile, os
tmp = "/tmp/mas_env_update.txt"
write_cmd = f"printf '%s' {repr(new_env)} > {tmp} && cp {tmp} {ENV_PATH} && rm {tmp}"
out, rc = run(write_cmd, timeout=10)

# Verify
out, _ = run(f"grep GEMINI_API_KEY {ENV_PATH}")
print(f"VM .env GEMINI_API_KEY: {out[:60]}...")

# Restart container with fresh env
print("\nRestarting MAS container...")
run("docker stop myca-orchestrator-new 2>&1; docker rm myca-orchestrator-new 2>&1", timeout=20)
out, rc = run(
    "docker run -d --name myca-orchestrator-new --restart unless-stopped "
    f"-p 8001:8000 --env-file {ENV_PATH} mycosoft/mas-agent:latest",
    timeout=20,
)
print(f"Container started: {out[:80]}")

print("Waiting 15s for startup...")
time.sleep(15)

# Test Gemini directly
print("\n=== Gemini API test ===")
out, _ = run(
    f"curl -s -w '\\n---STATUS:%{{http_code}}---' "
    f"'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={NEW_KEY}' "
    f"-H 'Content-Type: application/json' "
    f"-d '{{\"contents\":[{{\"role\":\"user\",\"parts\":[{{\"text\":\"say hello\"}}]}}]}}' "
    f"--max-time 10",
    timeout=15,
)
print(out[:500])

# Test MYCA chat
print("\n=== MYCA chat test ===")
out, _ = run(
    "curl -s -X POST http://localhost:8001/api/myca/chat "
    "-H 'Content-Type: application/json' "
    "-d '{\"message\": \"hello what is your name\", \"session_id\": \"gemini-test\", \"context\": {}}' "
    "--max-time 25",
    timeout=30,
)
print(out[:500])

client.close()
