"""Check what compounds exist in MINDEX."""
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
    
    # List all compounds
    print("=== All compounds in database ===")
    _, stdout, stderr = ssh.exec_command(
        '''docker exec mindex-postgres psql -U mycosoft -d mindex -c "SELECT id, name, producing_species FROM core.compounds ORDER BY name LIMIT 20;"'''
    )
    print(stdout.read().decode())
    
    # Check if any compounds are linked to Amanita
    print("=== Compounds with Amanita in producing_species ===")
    _, stdout, stderr = ssh.exec_command(
        '''docker exec mindex-postgres psql -U mycosoft -d mindex -c "SELECT id, name, producing_species FROM core.compounds WHERE 'Amanita' = ANY(producing_species) OR name ILIKE '%amanita%';"'''
    )
    print(stdout.read().decode())
    
    ssh.close()

if __name__ == "__main__":
    main()
