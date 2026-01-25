#!/usr/bin/env python3
"""Execute migration directly"""
import requests
import urllib3
import time
import base64

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

PROXMOX_HOST = "https://192.168.0.202:8006"
PROXMOX_TOKEN = "root@pam!cursor_agent=bc1c9dc7-6fca-4e89-8a1d-557a9d117a3e"
VM_ID = 103
NODE = "pve"

headers = {"Authorization": f"PVEAPIToken={PROXMOX_TOKEN}"}

def exec_cmd(cmd, timeout=120):
    url = f"{PROXMOX_HOST}/api2/json/nodes/{NODE}/qemu/{VM_ID}/agent/exec"
    try:
        data = {"command": "/bin/bash", "input-data": cmd}
        r = requests.post(url, headers=headers, data=data, verify=False, timeout=10)
        if not r.ok:
            return f"Exec failed: {r.status_code}"
        
        pid = r.json().get("data", {}).get("pid")
        if not pid:
            return "No PID"
        
        status_url = f"{PROXMOX_HOST}/api2/json/nodes/{NODE}/qemu/{VM_ID}/agent/exec-status"
        start = time.time()
        
        while time.time() - start < timeout:
            time.sleep(3)
            s = requests.get(status_url, headers=headers, params={"pid": pid}, verify=False, timeout=5)
            if s.ok:
                data = s.json().get("data", {})
                if data.get("exited"):
                    out_b64 = data.get("out-data", "")
                    err_b64 = data.get("err-data", "")
                    try:
                        out = base64.b64decode(out_b64).decode() if out_b64 else ""
                    except:
                        out = out_b64
                    try:
                        err = base64.b64decode(err_b64).decode() if err_b64 else ""
                    except:
                        err = err_b64
                    return out or err or "Command completed"
        return "Timeout"
    except Exception as e:
        return str(e)

print("=" * 60)
print("EXECUTING MIGRATION: 003_agent_logging.sql")
print("=" * 60)

# Step 1: Copy migration file to postgres container
print("\n[1] Copying migration file to postgres container...")
result = exec_cmd("docker cp /home/mycosoft/mycosoft/mas/migrations/003_agent_logging.sql mycosoft-postgres:/tmp/migration.sql 2>&1")
print(f"    Result: {result}")

# Step 2: Run migration inside container
print("\n[2] Executing migration...")
result = exec_cmd("docker exec mycosoft-postgres psql -U mas -d mindex -f /tmp/migration.sql 2>&1", timeout=60)
print(f"    Result:\n{result}")

# Step 3: Verify tables
print("\n[3] Verifying tables created...")
result = exec_cmd("""docker exec mycosoft-postgres psql -U mas -d mindex -c "\\dt agent_*" 2>&1""")
print(f"    Result:\n{result}")

# Step 4: Check row counts
print("\n[4] Checking table structure...")
result = exec_cmd("""docker exec mycosoft-postgres psql -U mas -d mindex -c "SELECT table_name, pg_size_pretty(pg_total_relation_size(quote_ident(table_name))) as size FROM information_schema.tables WHERE table_schema='public' AND table_name LIKE 'agent_%';" 2>&1""")
print(f"    Result:\n{result}")

print("\n" + "=" * 60)
print("MIGRATION COMPLETE")
print("=" * 60)
