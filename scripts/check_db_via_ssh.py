"""Check voice sessions by SSHing to MINDEX VM and querying directly."""
import paramiko
import sys

# Credentials
VM_IP = "192.168.0.189"
VM_USER = "mycosoft"
VM_PASSWORD = "REDACTED_VM_SSH_PASSWORD"

def main():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        print(f"Connecting to {VM_IP}...")
        client.connect(VM_IP, username=VM_USER, password=VM_PASSWORD, timeout=10)
        print("Connected!")
        
        # Check voice sessions
        print("\n=== Voice Sessions ===")
        sql = 'docker exec -i mindex-postgres psql -U mycosoft -d mindex -c "SELECT session_id, mode, turn_count, created_at FROM memory.voice_sessions ORDER BY created_at DESC LIMIT 5;"'
        stdin, stdout, stderr = client.exec_command(sql)
        print(stdout.read().decode('utf-8', errors='replace'))
        
        # Check ALL voice turns (both user and myca)
        print("\n=== All Voice Turns (last 10) ===")
        sql = 'docker exec -i mindex-postgres psql -U mycosoft -d mindex -c "SELECT speaker, LEFT(text, 60) as text, created_at FROM memory.voice_turns ORDER BY created_at DESC LIMIT 10;"'
        stdin, stdout, stderr = client.exec_command(sql)
        print(stdout.read().decode('utf-8', errors='replace'))
        
        # Count by speaker
        print("\n=== Turn Counts by Speaker ===")
        sql = 'docker exec -i mindex-postgres psql -U mycosoft -d mindex -c "SELECT speaker, COUNT(*) as count FROM memory.voice_turns GROUP BY speaker;"'
        stdin, stdout, stderr = client.exec_command(sql)
        print(stdout.read().decode('utf-8', errors='replace'))
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        client.close()

if __name__ == "__main__":
    main()
