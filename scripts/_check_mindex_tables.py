"""Check MINDEX table structure."""
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
        
        # List all tables in core schema
        print("=== Tables in core schema ===")
        _, stdout, stderr = ssh.exec_command(
            '''docker exec mindex-postgres psql -U mycosoft -d mindex -c "SELECT table_name FROM information_schema.tables WHERE table_schema = 'core';"'''
        )
        print(stdout.read().decode())
        
        # Check core.taxon columns
        print("=== Columns in core.taxon ===")
        _, stdout, stderr = ssh.exec_command(
            '''docker exec mindex-postgres psql -U mycosoft -d mindex -c "SELECT column_name, data_type FROM information_schema.columns WHERE table_schema = 'core' AND table_name = 'taxon';"'''
        )
        print(stdout.read().decode())
        
        # Test raw SQL query from unified_search
        print("=== Test raw search query ===")
        _, stdout, stderr = ssh.exec_command(
            '''docker exec mindex-postgres psql -U mycosoft -d mindex -c "SELECT id, canonical_name, common_name, rank FROM core.taxon WHERE canonical_name ILIKE '%Amanita%' LIMIT 5;"'''
        )
        print(stdout.read().decode())
        err = stderr.read().decode()
        if err:
            print(f"Stderr: {err}")
        
        ssh.close()
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
