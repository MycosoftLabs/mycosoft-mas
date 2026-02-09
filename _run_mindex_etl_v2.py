"""Run ETL v2 with correct column names."""
import paramiko
import textwrap

HOST = "192.168.0.189"
USER = "mycosoft"
PASS = "REDACTED_VM_SSH_PASSWORD"

def run(ssh, cmd, timeout=300):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode("utf-8", errors="replace").strip()
    err = stderr.read().decode("utf-8", errors="replace").strip()
    if out:
        print(out[:1500].encode("ascii","replace").decode())
    if err and "warning" not in err.lower():
        print(f"ERR: {err[:500].encode('ascii','replace').decode()}")
    return out, err

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PASS, timeout=10)
print("Connected")

# First check the actual column names for all tables
print("=== CHECKING SCHEMAS ===")
for table in ["compounds", "research_papers", "species_images"]:
    out, _ = run(ssh, f"docker exec mindex-postgres psql -U mycosoft -d mindex -c \"SELECT column_name, data_type FROM information_schema.columns WHERE table_schema='core' AND table_name='{table}' ORDER BY ordinal_position;\"")
    print(f"\n--- core.{table} ---")
    print(out)

ssh.close()
