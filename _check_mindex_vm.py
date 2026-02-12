"""Check MINDEX VM state -- SSH in and report on services, database, data."""
import os
import sys
import paramiko

# Load credentials from environment - NEVER hardcode passwords
HOST = os.environ.get("MINDEX_VM_HOST", "192.168.0.189")
USER = os.environ.get("VM_USER", "mycosoft")
PASS = os.environ.get("VM_PASSWORD")

if not PASS:
    print("ERROR: Set VM_PASSWORD environment variable. Never hardcode passwords!")
    sys.exit(1)

def run(ssh, cmd):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=15)
    out = stdout.read().decode().strip()
    err = stderr.read().decode().strip()
    return out, err

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    ssh.connect(HOST, username=USER, password=PASS, timeout=10)
    print("=== CONNECTED TO MINDEX VM ===")

    out, _ = run(ssh, "hostname && uptime")
    print(f"\n[HOST]\n{out}")

    # Docker containers
    out, _ = run(ssh, "docker ps -a --format 'table {{.Names}}\\t{{.Status}}\\t{{.Ports}}' 2>/dev/null || echo 'NO DOCKER'")
    print(f"\n[DOCKER CONTAINERS]\n{out}")

    # Systemd services
    out, _ = run(ssh, "systemctl list-units --type=service --state=running --no-pager 2>/dev/null | grep -iE 'postgres|redis|qdrant|mindex|api|nginx'")
    print(f"\n[RUNNING SERVICES]\n{out or 'None matched'}")

    # Check PostgreSQL
    out, _ = run(ssh, "sudo -S systemctl status postgresql 2>/dev/null | head -5 || echo 'no systemd postgres'")
    print(f"\n[POSTGRESQL STATUS]\n{out}")

    # Check if postgres is listening
    out, _ = run(ssh, "ss -tlnp | grep -E '5432|6333|6379|8000'")
    print(f"\n[LISTENING PORTS]\n{out or 'None on expected ports'}")

    # Check MINDEX database tables - use environment variable for password
    db_pass = os.environ.get("MINDEX_DB_PASSWORD", "")
    db_pass_cmd = f"PGPASSWORD='{db_pass}'" if db_pass else ""
    out, err = run(ssh, f"{db_pass_cmd} psql -U mycosoft -d mindex -h localhost -c \"SELECT schemaname, tablename FROM pg_tables WHERE schemaname NOT IN ('pg_catalog','information_schema') ORDER BY schemaname, tablename;\" 2>/dev/null")
    if not out:
        out, err = run(ssh, "sudo -u postgres psql -d mindex -c \"SELECT schemaname, tablename FROM pg_tables WHERE schemaname NOT IN ('pg_catalog','information_schema') ORDER BY schemaname, tablename;\" 2>/dev/null")
    print(f"\n[MINDEX TABLES]\n{out or err or 'Could not query'}")

    # Check taxa count
    out, err = run(ssh, f"{db_pass_cmd} psql -U mycosoft -d mindex -h localhost -c \"SELECT COUNT(*) as taxa_count FROM taxa;\" 2>/dev/null")
    if not out:
        out, err = run(ssh, "sudo -u postgres psql -d mindex -c \"SELECT COUNT(*) as taxa_count FROM taxa;\" 2>/dev/null")
    print(f"\n[TAXA COUNT]\n{out or err or 'Could not query'}")

    # Check sample taxa data
    out, err = run(ssh, f"{db_pass_cmd} psql -U mycosoft -d mindex -h localhost -c \"SELECT id, scientific_name, common_name, rank, source, image_url IS NOT NULL as has_image FROM taxa LIMIT 10;\" 2>/dev/null")
    if not out:
        out, err = run(ssh, "sudo -u postgres psql -d mindex -c \"SELECT id, scientific_name, common_name, rank, source, image_url IS NOT NULL as has_image FROM taxa LIMIT 10;\" 2>/dev/null")
    print(f"\n[SAMPLE TAXA]\n{out or err or 'Could not query'}")

    # Check counts of other tables
    for table in ["observations", "compounds", "genomes", "traits", "external_ids", "synonyms"]:
        out, _ = run(ssh, f"{db_pass_cmd} psql -U mycosoft -d mindex -h localhost -c \"SELECT COUNT(*) FROM {table};\" 2>/dev/null")
        if not out:
            out, _ = run(ssh, f"sudo -u postgres psql -d mindex -c \"SELECT COUNT(*) FROM {table};\" 2>/dev/null")
        count = out.split('\n')[2].strip() if out and len(out.split('\n')) > 2 else "N/A"
        print(f"  {table}: {count}")

    # Check /opt/mycosoft
    out, _ = run(ssh, "ls -la /opt/mycosoft/ 2>/dev/null || echo 'No /opt/mycosoft'")
    print(f"\n[/opt/mycosoft]\n{out}")

    # Check MINDEX API process
    out, _ = run(ssh, "ps aux | grep -iE 'mindex|uvicorn|fastapi|gunicorn' | grep -v grep")
    print(f"\n[MINDEX API PROCESSES]\n{out or 'None running'}")

    # Check if MINDEX repo exists
    out, _ = run(ssh, "ls -la /opt/mycosoft/mindex/ 2>/dev/null || ls -la ~/mindex/ 2>/dev/null || echo 'No mindex repo found'")
    print(f"\n[MINDEX REPO]\n{out}")

    ssh.close()
    print("\n=== DONE ===")

except Exception as e:
    print(f"SSH FAILED: {e}")
