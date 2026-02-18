"""Check species_images table structure."""
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
    
    # Check species_images columns
    print("=== species_images columns ===")
    _, stdout, stderr = ssh.exec_command(
        '''docker exec mindex-postgres psql -U mycosoft -d mindex -c "SELECT column_name, data_type FROM information_schema.columns WHERE table_schema = 'core' AND table_name = 'species_images';"'''
    )
    print(stdout.read().decode())
    
    # Check sample data
    print("=== species_images sample ===")
    _, stdout, stderr = ssh.exec_command(
        '''docker exec mindex-postgres psql -U mycosoft -d mindex -c "SELECT species_name, url FROM core.species_images LIMIT 5;"'''
    )
    print(stdout.read().decode())
    err = stderr.read().decode()
    if err:
        print(f"Error: {err}")
    
    # Test the exact query
    print("=== Test taxa query ===")
    _, stdout, stderr = ssh.exec_command(
        '''docker exec mindex-postgres psql -U mycosoft -d mindex -c "SELECT t.id, t.canonical_name, t.common_name FROM core.taxon t WHERE canonical_name ILIKE '%Amanita%' LIMIT 3;"'''
    )
    print(stdout.read().decode())
    err = stderr.read().decode()
    if err:
        print(f"Error: {err}")
    
    ssh.close()

if __name__ == "__main__":
    main()
