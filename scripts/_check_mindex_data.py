"""Check if MINDEX has data."""
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
        
        queries = [
            ("Taxa count", "SELECT COUNT(*) FROM core.taxon;"),
            ("Taxa sample", "SELECT canonical_name, common_name FROM core.taxon LIMIT 5;"),
            ("Amanita search", "SELECT canonical_name FROM core.taxon WHERE canonical_name ILIKE '%Amanita%' LIMIT 5;"),
            ("Compounds count", "SELECT COUNT(*) FROM bio.compound;"),
            ("Genetics count", "SELECT COUNT(*) FROM bio.genetic_sequence;"),
            ("Observations count", "SELECT COUNT(*) FROM core.observation;"),
        ]
        
        for name, query in queries:
            print(f"=== {name} ===")
            _, stdout, stderr = ssh.exec_command(
                f'docker exec mindex-postgres psql -U mycosoft -d mindex -c "{query}"'
            )
            print(stdout.read().decode())
            err = stderr.read().decode()
            if err and "ERROR" in err:
                print(f"Error: {err}")
        
        ssh.close()
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
