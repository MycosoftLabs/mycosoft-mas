#!/usr/bin/env python3
"""Test MYCA chat and check Gemini API directly."""
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

def run(cmd, timeout=20):
    stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode(errors="replace")
    err = stderr.read().decode(errors="replace")
    return out + err

# Step 1: Test Gemini API directly from the VM with the actual key
print("=== Direct Gemini API test from VM ===")
gemini_key = "AIzaSyA1XciZWVlg-P0EI5D3tCQzqHkoW877LoY"
out = run(
    f"curl -s -w '\\n---STATUS:%{{http_code}}---' "
    f"'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={gemini_key}' "
    f"-H 'Content-Type: application/json' "
    f"-d '{{\"contents\":[{{\"role\":\"user\",\"parts\":[{{\"text\":\"say the word ok\"}}]}}]}}' "
    f"--max-time 15",
    timeout=20,
)
print(out[:800])

# Step 2: Test streaming endpoint
print("\n=== Direct Gemini streaming test from VM ===")
out = run(
    f"curl -s -w '\\n---STATUS:%{{http_code}}---' "
    f"'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:streamGenerateContent?key={gemini_key}&alt=sse' "
    f"-H 'Content-Type: application/json' "
    f"-d '{{\"contents\":[{{\"role\":\"user\",\"parts\":[{{\"text\":\"say the word ok\"}}]}}]}}' "
    f"--max-time 15",
    timeout=20,
)
print(out[:800])

# Step 3: Send chat and get logs
print("\n=== Sending chat request ===")
run("docker exec myca-orchestrator-new true 2>/dev/null || docker start myca-orchestrator-new 2>/dev/null")
time.sleep(3)
chat_out = run(
    "curl -s -X POST http://localhost:8001/api/myca/chat "
    "-H 'Content-Type: application/json' "
    "-d '{\"message\": \"what is 2+2\", \"session_id\": \"debug-2\", \"context\": {}}' "
    "--max-time 20",
    timeout=25,
)
print("Chat:", chat_out[:300])

# Grab logs immediately
time.sleep(1)
print("\n=== Fresh logs after chat ===")
log_out = run("docker logs myca-orchestrator-new 2>&1 | tail -20", timeout=10)
print(log_out[:800])

client.close()
