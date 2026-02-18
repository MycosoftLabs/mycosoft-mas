"""Check table columns for compounds and dna_sequences."""
import paramiko

HOST = "192.168.0.189"
USER = "mycosoft"
PASSWORD = "REDACTED_VM_SSH_PASSWORD"

def main():
    print(f"Connecting to {HOST}...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(HOST, username=USER, password=PASSWORD, timeout=10)
    print("Connected!\n")
    
    tables = [
        ("core", "compounds"),
        ("core", "dna_sequences"),
    ]
    
    for schema, table in tables:
        print(f"=== {schema}.{table} columns ===")
        _, stdout, stderr = ssh.exec_command(
            f'''docker exec mindex-postgres psql -U mycosoft -d mindex -c "SELECT column_name, data_type FROM information_schema.columns WHERE table_schema = '{schema}' AND table_name = '{table}';"'''
        )
        print(stdout.read().decode())
        
        print(f"=== {schema}.{table} count ===")
        _, stdout, stderr = ssh.exec_command(
            f'''docker exec mindex-postgres psql -U mycosoft -d mindex -c "SELECT COUNT(*) FROM {schema}.{table};"'''
        )
        print(stdout.read().decode())
        err = stderr.read().decode()
        if err:
            print(f"Error: {err}")
    
    ssh.close()

if __name__ == "__main__":
    main()
