#!/usr/bin/env python3
"""
Transfer Mycosoft codebases to VM using SFTP
"""
import paramiko
import os
import stat
from pathlib import Path

VM_IP = "192.168.0.187"
VM_USER = "mycosoft"
VM_PASS = "Mushroom1!Mushroom1!"

# Local paths
MAS_PATH = Path(r"C:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas")
WEBSITE_PATH = Path(r"C:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website")

# Remote paths
REMOTE_MAS = "/opt/mycosoft/mas"
REMOTE_WEBSITE = "/opt/mycosoft/website"

# Directories/files to skip (save bandwidth)
SKIP_PATTERNS = [
    'node_modules', 'venv', 'venv311', '.git', '__pycache__', 
    '.next', 'dist', 'build', '*.pyc', '.mypy_cache',
    'logs', '*.log', '*.tar', '*.zip'
]

def should_skip(path):
    """Check if path should be skipped"""
    name = path.name
    for pattern in SKIP_PATTERNS:
        if pattern.startswith('*'):
            if name.endswith(pattern[1:]):
                return True
        elif name == pattern:
            return True
    return False

def upload_directory(sftp, local_path, remote_path, depth=0):
    """Recursively upload a directory"""
    local_path = Path(local_path)
    
    if should_skip(local_path):
        return 0
    
    count = 0
    indent = "  " * depth
    
    try:
        sftp.stat(remote_path)
    except FileNotFoundError:
        sftp.mkdir(remote_path)
    
    for item in local_path.iterdir():
        if should_skip(item):
            continue
            
        remote_item = f"{remote_path}/{item.name}"
        
        if item.is_dir():
            count += upload_directory(sftp, item, remote_item, depth + 1)
        else:
            try:
                # Only show every 50th file to reduce output
                if count % 50 == 0:
                    print(f"{indent}Uploading: {item.name}")
                sftp.put(str(item), remote_item)
                count += 1
            except Exception as e:
                print(f"{indent}Error uploading {item.name}: {e}")
    
    return count

def main():
    print("=" * 70)
    print("TRANSFERRING MYCOSOFT CODEBASES TO VM")
    print(f"Target: {VM_IP}")
    print("=" * 70)
    
    # Connect
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(VM_IP, username=VM_USER, password=VM_PASS)
    sftp = ssh.open_sftp()
    print("Connected via SFTP!")
    
    # Transfer MAS repository
    print("\n" + "=" * 50)
    print("Transferring MAS repository...")
    print("=" * 50)
    
    if MAS_PATH.exists():
        count = upload_directory(sftp, MAS_PATH, REMOTE_MAS)
        print(f"Transferred {count} files from MAS")
    else:
        print(f"ERROR: MAS path not found: {MAS_PATH}")
    
    # Transfer Website repository
    print("\n" + "=" * 50)
    print("Transferring Website repository...")
    print("=" * 50)
    
    if WEBSITE_PATH.exists():
        count = upload_directory(sftp, WEBSITE_PATH, REMOTE_WEBSITE)
        print(f"Transferred {count} files from Website")
    else:
        print(f"ERROR: Website path not found: {WEBSITE_PATH}")
    
    sftp.close()
    ssh.close()
    
    print("\n" + "=" * 70)
    print("TRANSFER COMPLETE!")
    print("=" * 70)

if __name__ == "__main__":
    main()
