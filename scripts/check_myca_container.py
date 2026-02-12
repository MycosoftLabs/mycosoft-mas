#!/usr/bin/env python3
"""Check MAS container logs for consciousness import errors."""
import paramiko

VM = "192.168.0.188"
USER = "mycosoft"
PASS = "REDACTED_VM_SSH_PASSWORD"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(VM, username=USER, password=PASS, timeout=15)

# Check container status
stdin, stdout, stderr = ssh.exec_command("docker ps | grep myca-orchestrator-new", timeout=15)
print("CONTAINER STATUS:")
print(stdout.read().decode())

# Check for import errors
stdin, stdout, stderr = ssh.exec_command("docker logs myca-orchestrator-new 2>&1 | grep -E '(ImportError|ModuleNotFoundError|consciousness)' | tail -30", timeout=30)
print("\nIMPORT/CONSCIOUSNESS LOGS:")
logs = stdout.read().decode()
print(logs if logs.strip() else "(No consciousness-related errors found)")

# Check if consciousness API is actually available
stdin, stdout, stderr = ssh.exec_command("docker exec myca-orchestrator-new python3 -c 'from mycosoft_mas.core.routers.consciousness_api import router; print(\"Consciousness router imported successfully\")'", timeout=15)
print("\nDIRECT IMPORT TEST:")
out = stdout.read().decode()
err = stderr.read().decode()
print(out if out.strip() else err)

# List all registered routes
stdin, stdout, stderr = ssh.exec_command("curl -s http://127.0.0.1:8000/docs 2>&1 | grep -o '/api/[^\"]*' | sort -u", timeout=30)
print("\nREGISTERED API ROUTES:")
print(stdout.read().decode()[:2000])

ssh.close()
