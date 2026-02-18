"""Check MINDEX API logs."""
import paramiko
import sys

HOST = "192.168.0.189"
USER = "mycosoft"
PASSWORD = "REDACTED_VM_SSH_PASSWORD"

def main():
    print(f"Connecting to {HOST}...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        ssh.connect(HOST, username=USER, password=PASSWORD, timeout=10)
        print("Connected!\n")
        
        # Get last 50 lines of mindex-api logs
        print("=== MINDEX API Logs (last 50 lines) ===")
        _, stdout, stderr = ssh.exec_command("docker logs mindex-api --tail 50")
        logs = stdout.read().decode()
        errs = stderr.read().decode()
        print(logs)
        if errs:
            print(errs)
        
        # Check postgres connection
        print("\n=== Testing Postgres Connection ===")
        _, stdout, stderr = ssh.exec_command(
            "docker exec mindex-postgres psql -U mycosoft -d mindex -c \"SELECT 1 as test;\""
        )
        print(stdout.read().decode())
        print(stderr.read().decode())
        
        ssh.close()
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
