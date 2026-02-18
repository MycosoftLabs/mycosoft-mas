"""Deploy MINDEX unified search fix to VM 189."""
import paramiko
import os

HOST = "192.168.0.189"
USER = "mycosoft"
PASSWORD = "REDACTED_VM_SSH_PASSWORD"

# Read the fixed unified_search.py file
FIXED_FILE = r"c:\Users\admin2\Desktop\MYCOSOFT\CODE\MINDEX\mindex\mindex_api\routers\unified_search.py"

def main():
    print(f"Reading fixed file: {FIXED_FILE}")
    with open(FIXED_FILE, 'r', encoding='utf-8') as f:
        content = f.read()
    
    print(f"Connecting to {HOST}...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(HOST, username=USER, password=PASSWORD, timeout=10)
    print("Connected!")
    
    # Write the file to a temp location using SFTP
    sftp = ssh.open_sftp()
    remote_path = "/tmp/unified_search.py"
    print(f"Uploading to {remote_path}...")
    with sftp.open(remote_path, 'w') as f:
        f.write(content)
    sftp.close()
    print("Uploaded!")
    
    # Copy into the container
    print("\nCopying to mindex-api container...")
    _, stdout, stderr = ssh.exec_command(f"docker cp {remote_path} mindex-api:/app/mindex_api/routers/unified_search.py")
    print(stdout.read().decode())
    print(stderr.read().decode())
    
    # Restart mindex-api
    print("\nRestarting mindex-api container...")
    _, stdout, stderr = ssh.exec_command("docker restart mindex-api")
    print(stdout.read().decode())
    print(stderr.read().decode())
    
    # Wait and test
    print("\nWaiting for restart...")
    _, stdout, _ = ssh.exec_command("sleep 5 && curl -s http://localhost:8000/api/mindex/health")
    print(f"Health: {stdout.read().decode()}")
    
    # Test search
    print("\nTesting search...")
    _, stdout, stderr = ssh.exec_command("curl -s 'http://localhost:8000/api/mindex/unified-search?q=Amanita&limit=3'")
    result = stdout.read().decode()
    print(f"Search result: {result[:500]}...")
    
    ssh.close()
    print("\nDone!")

if __name__ == "__main__":
    main()
