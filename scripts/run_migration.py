#!/usr/bin/env python3
"""
Run database migration for MAS v2 agent logging tables
Uses Proxmox QEMU Guest Agent to execute on VM
"""
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

def log(msg, level="INFO"):
    ts = time.strftime("%H:%M:%S")
    symbols = {"INFO": "[i]", "OK": "[+]", "WARN": "[!]", "ERR": "[X]", "RUN": "[>]"}
    print(f"[{ts}] {symbols.get(level, '*')} {msg}")

def exec_cmd(cmd, timeout=120, show_output=True):
    """Execute command via QEMU Guest Agent"""
    url = f"{PROXMOX_HOST}/api2/json/nodes/{NODE}/qemu/{VM_ID}/agent/exec"
    try:
        data = {"command": "/bin/bash", "input-data": cmd}
        r = requests.post(url, headers=headers, data=data, verify=False, timeout=10)
        if not r.ok:
            return None, f"Exec failed: {r.status_code}"
        
        pid = r.json().get("data", {}).get("pid")
        if not pid:
            return None, "No PID"
        
        status_url = f"{PROXMOX_HOST}/api2/json/nodes/{NODE}/qemu/{VM_ID}/agent/exec-status"
        start = time.time()
        
        while time.time() - start < timeout:
            time.sleep(2)
            s = requests.get(status_url, headers=headers, params={"pid": pid}, verify=False, timeout=5)
            if s.ok:
                data = s.json().get("data", {})
                if data.get("exited"):
                    code = data.get("exitcode", 0)
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
                    
                    if show_output and (out or err):
                        output = (out or err)[:500]
                        for line in output.split('\n')[:15]:
                            print(f"    {line}")
                    
                    return code == 0, out or err
            
        return None, "Timeout"
    except Exception as e:
        return None, str(e)

def main():
    print("=" * 60)
    print("MINDEX DATABASE MIGRATION - Agent Logging Tables")
    print("=" * 60)
    
    # Step 1: Check PostgreSQL container is running
    log("Checking PostgreSQL container status...")
    success, output = exec_cmd("docker ps --format '{{.Names}}' | grep -i postgres")
    if output and "postgres" in output.lower():
        log("PostgreSQL is running", "OK")
    else:
        log(f"PostgreSQL check: {output}", "WARN")
    
    # Step 2: Check if migration file exists
    log("Checking migration file...")
    success, output = exec_cmd("ls -la /home/mycosoft/mycosoft/mas/migrations/003_agent_logging.sql")
    if success:
        log("Migration file found", "OK")
    else:
        log("Migration file not found!", "ERR")
        return False
    
    # Step 3: Run the migration
    log("Running migration...", "RUN")
    migration_cmd = """
docker exec mycosoft-postgres psql -U mas -d mindex -f /docker-entrypoint-initdb.d/003_agent_logging.sql 2>&1 || \
docker exec mycosoft-postgres psql -U mas -d mindex -c "$(cat /home/mycosoft/mycosoft/mas/migrations/003_agent_logging.sql)" 2>&1
"""
    success, output = exec_cmd(migration_cmd, timeout=60)
    
    # Alternative approach: Copy and run
    if not success or "ERROR" in str(output):
        log("Trying alternative migration approach...", "RUN")
        
        # Copy migration file to container
        copy_cmd = "docker cp /home/mycosoft/mycosoft/mas/migrations/003_agent_logging.sql mycosoft-postgres:/tmp/migration.sql"
        exec_cmd(copy_cmd, show_output=False)
        
        # Run migration from inside container
        run_cmd = "docker exec mycosoft-postgres psql -U mas -d mindex -f /tmp/migration.sql 2>&1"
        success, output = exec_cmd(run_cmd, timeout=60)
    
    if success:
        log("Migration completed successfully", "OK")
    else:
        log(f"Migration may have errors: {output[:200]}", "WARN")
    
    # Step 4: Verify tables were created
    log("Verifying tables created...", "RUN")
    verify_cmd = """docker exec mycosoft-postgres psql -U mas -d mindex -c "SELECT table_name FROM information_schema.tables WHERE table_schema='public' AND table_name LIKE 'agent_%' ORDER BY table_name;" 2>&1"""
    success, output = exec_cmd(verify_cmd)
    
    if "agent_logs" in str(output) and "agent_snapshots" in str(output):
        log("All agent tables created successfully", "OK")
    else:
        log("Some tables may be missing", "WARN")
    
    print("\n" + "=" * 60)
    print("MIGRATION COMPLETE")
    print("=" * 60)
    
    return True

if __name__ == "__main__":
    main()
