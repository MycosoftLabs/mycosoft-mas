"""Quick restart of MINDEX containers on VM 189."""
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
        print("Connected!")
        
        # Get docker status
        print("\nChecking Docker containers...")
        _, stdout, stderr = ssh.exec_command("docker ps --format '{{.Names}} {{.Status}}'")
        print(stdout.read().decode())
        
        # Restart mindex containers
        print("\nRestarting MINDEX containers...")
        _, stdout, stderr = ssh.exec_command("cd /home/mycosoft/mindex && docker compose restart")
        print(stdout.read().decode())
        err = stderr.read().decode()
        if err:
            print(f"Stderr: {err}")
        
        # Wait and check health
        print("\nWaiting 10 seconds for startup...")
        _, stdout, _ = ssh.exec_command("sleep 10 && curl -s http://localhost:8000/api/mindex/health")
        health = stdout.read().decode()
        print(f"Health check: {health}")
        
        ssh.close()
        print("\nDone!")
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
