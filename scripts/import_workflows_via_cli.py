#!/usr/bin/env python3
"""Import n8n workflows using the n8n CLI (bypasses API key requirement)"""
import paramiko
import json
from pathlib import Path

def main():
    # Read all workflow files locally
    workflows_dir = Path(__file__).parent.parent / "n8n" / "workflows"
    
    if not workflows_dir.exists():
        print(f"Workflows directory not found: {workflows_dir}")
        return
    
    workflow_files = list(workflows_dir.glob("*.json"))
    print(f"Found {len(workflow_files)} workflow files")
    
    # Connect to SSH
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect('192.168.0.188', username='mycosoft', password='REDACTED_VM_SSH_PASSWORD')
    sftp = ssh.open_sftp()
    
    # Create temp directory for workflows
    print("Creating temp directory on VM...")
    stdin, stdout, stderr = ssh.exec_command('mkdir -p /tmp/n8n_workflows')
    stdout.channel.recv_exit_status()
    
    # Upload workflow files
    print("Uploading workflow files...")
    for wf_file in workflow_files:
        remote_path = f"/tmp/n8n_workflows/{wf_file.name}"
        try:
            sftp.put(str(wf_file), remote_path)
            print(f"  Uploaded: {wf_file.name}")
        except Exception as e:
            print(f"  Error uploading {wf_file.name}: {e}")
    
    # Import using n8n import:workflow command
    print("\nImporting workflows via n8n CLI...")
    
    # First, list what's in the temp dir
    stdin, stdout, stderr = ssh.exec_command('ls /tmp/n8n_workflows/*.json 2>/dev/null | wc -l')
    count = stdout.read().decode().strip()
    print(f"Files in temp dir: {count}")
    
    # Import all workflows at once
    import_cmd = '''
    for f in /tmp/n8n_workflows/*.json; do
        echo "Importing: $f"
        docker exec -i myca-n8n n8n import:workflow --input=/dev/stdin < "$f" 2>&1 || echo "Failed: $f"
    done
    '''
    print("\nRunning import command...")
    stdin, stdout, stderr = ssh.exec_command(import_cmd)
    exit_status = stdout.channel.recv_exit_status()
    output = stdout.read().decode()
    errors = stderr.read().decode()
    
    print(output)
    if errors:
        print("STDERR:", errors)
    
    # Check imported workflows
    print("\n=== Checking imported workflows ===")
    stdin, stdout, stderr = ssh.exec_command('docker exec myca-n8n n8n list:workflow 2>&1 | head -50')
    print(stdout.read().decode())
    
    # Cleanup
    stdin, stdout, stderr = ssh.exec_command('rm -rf /tmp/n8n_workflows')
    
    sftp.close()
    ssh.close()
    print("\nDone!")

if __name__ == "__main__":
    main()
