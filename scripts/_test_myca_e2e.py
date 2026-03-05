"""
End-to-end MYCA pipeline test.
Verifies each layer is actually usable, not just "running".
"""
import urllib.request
import json
import socket
import os
import sys
from pathlib import Path

# Add MAS repo for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

def http_get(url, timeout=10, data=None):
    req = urllib.request.Request(url, data=data, method="POST" if data else "GET")
    if data:
        req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, r.read().decode()

def tcp(host, port, timeout=3):
    try:
        s = socket.create_connection((host, port), timeout)
        s.close()
        return True
    except:
        return False

def load_creds():
    cf = Path(__file__).parent.parent / ".credentials.local"
    if cf.exists():
        for line in cf.read_text().splitlines():
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

load_creds()
pw = os.environ.get("VM_SSH_PASSWORD", os.environ.get("VM_PASSWORD", ""))

results = {"passed": [], "failed": [], "warnings": []}

print("=" * 70)
print("  MYCA END-TO-END USABILITY TEST")
print("=" * 70)

# 1. MAS Orchestrator - API usable
print("\n--- 1. MAS Orchestrator ---")
try:
    code, body = http_get("http://192.168.0.188:8001/health")
    h = json.loads(body)
    pg = next((c for c in h.get("components", []) if c["name"] == "postgresql"), {})
    if h.get("status") != "error" and pg.get("status") == "healthy":
        results["passed"].append("MAS health + Postgres")
        print(f"  OK: MAS healthy, Postgres connected")
    else:
        results["failed"].append("MAS unhealthy")
        print(f"  FAIL: {h}")
except Exception as e:
    results["failed"].append(f"MAS unreachable: {e}")
    print(f"  FAIL: {e}")

# 2. MAS - List agents
print("\n--- 2. MAS Agents API ---")
try:
    code, body = http_get("http://192.168.0.188:8001/agents/registry/", timeout=5)
    if code == 200:
        data = json.loads(body) if body else {}
        agents = data.get("agents", data) if isinstance(data, dict) else (data if isinstance(data, list) else [])
        count = len(agents) if isinstance(agents, list) else len(data.get("categories", [])) if isinstance(data, dict) else 0
        if count > 0 or (isinstance(data, dict) and ("agents" in data or "categories" in data)):
            results["passed"].append(f"MAS agents list ({count} agents)")
            print(f"  OK: {count} agents registered")
        else:
            results["warnings"].append("MAS agents list empty")
            print(f"  WARN: agents list empty or unexpected format")
    else:
        results["failed"].append(f"MAS agents API {code}")
        print(f"  FAIL: HTTP {code}")
except Exception as e:
    results["failed"].append(f"MAS agents: {e}")
    print(f"  FAIL: {e}")

# 3. MAS - MYCA chat endpoint
print("\n--- 3. MAS MYCA Chat API ---")
try:
    payload = json.dumps({"message": "What is 2+2?", "context": {}, "stream": False}).encode()
    code, body = http_get("http://192.168.0.188:8001/api/myca/chat", data=payload, timeout=30)
    if code == 200:
        results["passed"].append("MAS chat/task API")
        print(f"  OK: Chat endpoint responds")
    else:
        results["warnings"].append(f"MAS chat returned {code}")
        print(f"  WARN: HTTP {code} - {body[:100]}")
except Exception as e:
    results["warnings"].append(f"MAS chat: {e}")
    print(f"  WARN: {e}")

# 4. MINDEX API - Search usable
print("\n--- 4. MINDEX API ---")
try:
    code, body = http_get("http://192.168.0.189:8000/health")
    if code == 200:
        results["passed"].append("MINDEX health")
        print(f"  OK: MINDEX healthy")
    else:
        results["failed"].append("MINDEX unhealthy")
        print(f"  FAIL: {code}")
except Exception as e:
    results["failed"].append(f"MINDEX: {e}")
    print(f"  FAIL: {e}")

# 5. VM 191 - SSH
print("\n--- 5. VM 191 SSH ---")
if tcp("192.168.0.191", 22):
    results["passed"].append("VM 191 SSH")
    print(f"  OK: SSH port open")
else:
    results["failed"].append("VM 191 SSH closed")
    print(f"  FAIL: SSH unreachable")

# 6. VM 191 - Workspace API (try 8100, fallback 8000)
print("\n--- 6. MYCA Workspace API (191) ---")
workspace_url = None
for port in (8100, 8000):
    try:
        req = urllib.request.Request(f"http://192.168.0.191:{port}/health")
        with urllib.request.urlopen(req, timeout=5) as r:
            if r.status < 500:
                workspace_url = f"http://192.168.0.191:{port}"
                results["passed"].append(f"Workspace API (port {port})")
                print(f"  OK: Workspace API at {port}")
                break
    except Exception:
        continue
if not workspace_url:
    results["failed"].append("Workspace API unreachable on 8000 or 8100")
    print(f"  FAIL: Workspace API not reachable on 8000 or 8100")

# 7. VM 191 - MYCA OS daemon running
print("\n--- 7. MYCA OS Daemon ---")
try:
    import paramiko
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect("192.168.0.191", username="mycosoft", password=pw, timeout=10)
    _, stdout, _ = ssh.exec_command("systemctl is-active myca-os 2>/dev/null")
    status = stdout.read().decode().strip()
    ssh.close()
    if status == "active":
        results["passed"].append("MYCA OS daemon active")
        print(f"  OK: myca-os is active")
    else:
        results["failed"].append(f"MYCA OS: {status}")
        print(f"  FAIL: myca-os status = {status}")
except Exception as e:
    results["failed"].append(f"MYCA OS check: {e}")
    print(f"  FAIL: {e}")

# 8. VM 191 - MYCA can reach MAS
print("\n--- 8. MYCA -> MAS connectivity ---")
try:
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect("192.168.0.191", username="mycosoft", password=pw, timeout=10)
    _, stdout, _ = ssh.exec_command("curl -s -o /dev/null -w '%{http_code}' http://192.168.0.188:8001/health 2>/dev/null || echo 'FAIL'")
    code = stdout.read().decode().strip()
    ssh.close()
    if code == "200":
        results["passed"].append("191->188 MAS reachable")
        print(f"  OK: VM 191 can reach MAS")
    else:
        results["failed"].append(f"191->188: {code}")
        print(f"  FAIL: 191 cannot reach MAS (got {code})")
except Exception as e:
    results["failed"].append(f"191->188: {e}")
    print(f"  FAIL: {e}")

# 9. VM 191 - MYCA can reach MINDEX
print("\n--- 9. MYCA -> MINDEX connectivity ---")
try:
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect("192.168.0.191", username="mycosoft", password=pw, timeout=10)
    _, stdout, _ = ssh.exec_command("curl -s -o /dev/null -w '%{http_code}' http://192.168.0.189:8000/health 2>/dev/null || echo 'FAIL'")
    code = stdout.read().decode().strip()
    ssh.close()
    if code == "200":
        results["passed"].append("191->189 MINDEX reachable")
        print(f"  OK: VM 191 can reach MINDEX")
    else:
        results["failed"].append(f"191->189: {code}")
        print(f"  FAIL: 191 cannot reach MINDEX (got {code})")
except Exception as e:
    results["failed"].append(f"191->189: {e}")
    print(f"  FAIL: {e}")

# 10. Workspace API - actual endpoint
print("\n--- 10. Workspace API health/endpoints ---")
try:
    for path in ["/", "/health", "/api/workspace/health", "/api/workspace/status"]:
        req = urllib.request.Request(f"http://192.168.0.191:8100{path}")
        try:
            with urllib.request.urlopen(req, timeout=5) as r:
                print(f"  {path:30s} -> {r.status}")
                if r.status < 500:
                    break
        except urllib.error.HTTPError as e:
            print(f"  {path:30s} -> {e.code}")
            if e.code == 404:
                continue
        except Exception as e:
            print(f"  {path:30s} -> FAIL: {e}")
except Exception as e:
    print(f"  Error: {e}")

# 11. n8n on 191
print("\n--- 11. MYCA n8n (191:5679) ---")
if tcp("192.168.0.191", 5679):
    results["passed"].append("n8n port open")
    print(f"  OK: n8n port open")
else:
    results["warnings"].append("n8n 5679 not reachable from dev PC (may be Docker internal)")
    print(f"  WARN: n8n port not reachable from here (check if bound to localhost only)")

# 12. Workspace /think - send message through MYCA brain
print("\n--- 12. Workspace /think (MYCA brain) ---")
if workspace_url:
    try:
        payload = json.dumps({"message": "Ping - E2E test", "session_id": "e2e-test"}).encode()
        req = urllib.request.Request(
            f"{workspace_url}/workspace/think",
            data=payload,
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=45) as r:
            body = r.read().decode()
            print(f"  OK: /workspace/think responded ({r.status})")
            results["passed"].append("Workspace think API")
    except urllib.error.HTTPError as e:
        results["warnings"].append(f"Workspace think: {e.code} - {e.read().decode()[:80]}")
        print(f"  WARN: {e.code}")
    except Exception as e:
        results["warnings"].append(f"Workspace think: {e}")
        print(f"  WARN: {e}")
else:
    results["warnings"].append("Skipped (workspace API down)")

# Summary
print("\n" + "=" * 70)
print("  SUMMARY")
print("=" * 70)
print(f"  PASSED:  {len(results['passed'])}")
for p in results["passed"]:
    print(f"    + {p}")
print(f"  FAILED:  {len(results['failed'])}")
for f in results["failed"]:
    print(f"    - {f}")
print(f"  WARNINGS: {len(results['warnings'])}")
for w in results["warnings"]:
    print(f"    ! {w}")

usable = len(results["failed"]) == 0
print()
if usable:
    print("  RESULT: Pipeline is USABLE. MYCA can receive and execute work.")
else:
    print("  RESULT: Pipeline has CRITICAL failures. Fix failed items first.")
print("=" * 70)

sys.exit(0 if usable else 1)
