#!/usr/bin/env python3
"""
Transfer Mycosoft codebases to VM 103
Transfers: WEBSITE, MINDEX, MAS (excluding node_modules, venv, .git)
"""
import paramiko
import os
import sys
from pathlib import Path

VM_IP = "192.168.0.187"
VM_USER = "mycosoft"
VM_PASS = "Mushroom1!Mushroom1!"

# Source directories
WEBSITE_PATH = Path(r"C:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website")
MINDEX_PATH = Path(r"C:\Users\admin2\Desktop\MYCOSOFT\CODE\MINDEX\mindex")
MAS_PATH = Path(r"C:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas")

# Target directories on VM
VM_BASE = "/opt/mycosoft"

# Directories/files to exclude
EXCLUDES = {
    'node_modules', '.git', '__pycache__', '.next', 'venv', 'venv311',
    '.venv', 'dist', 'build', '.cache', '.turbo', 'coverage',
    '*.pyc', '*.pyo', '.env.local', '.env', 'logs', '.DS_Store',
    'Thumbs.db', '.pytest_cache', '.mypy_cache', 'htmlcov'
}

def should_exclude(path):
    """Check if path should be excluded"""
    name = path.name
    for exc in EXCLUDES:
        if exc.startswith('*'):
            if name.endswith(exc[1:]):
                return True
        elif name == exc:
            return True
    return False

def run_cmd(ssh, cmd, sudo=False, timeout=120):
    """Run command on VM"""
    if sudo:
        cmd = f"echo '{VM_PASS}' | sudo -S {cmd}"
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    return stdout.read().decode(), stderr.read().decode()

def count_files(source_path):
    """Count files to transfer"""
    count = 0
    for root, dirs, files in os.walk(source_path):
        # Filter excluded directories
        dirs[:] = [d for d in dirs if d not in EXCLUDES]
        for f in files:
            if not should_exclude(Path(f)):
                count += 1
    return count

def transfer_directory(sftp, local_path, remote_path, label):
    """Transfer a directory recursively via SFTP"""
    print(f"\n{'='*60}")
    print(f"Transferring {label}")
    print(f"From: {local_path}")
    print(f"To:   {remote_path}")
    print(f"{'='*60}")
    
    if not local_path.exists():
        print(f"  [SKIP] Source directory does not exist")
        return 0
    
    # Count files first
    total_files = count_files(local_path)
    print(f"  Files to transfer: {total_files}")
    
    transferred = 0
    errors = 0
    
    for root, dirs, files in os.walk(local_path):
        # Filter excluded directories
        dirs[:] = [d for d in dirs if d not in EXCLUDES]
        
        # Calculate relative path
        rel_root = Path(root).relative_to(local_path)
        remote_dir = f"{remote_path}/{rel_root}".replace("\\", "/")
        
        # Create remote directory
        try:
            sftp.stat(remote_dir)
        except FileNotFoundError:
            try:
                # Create parent directories
                parts = remote_dir.split("/")
                current = ""
                for part in parts:
                    if part:
                        current = f"{current}/{part}"
                        try:
                            sftp.stat(current)
                        except FileNotFoundError:
                            sftp.mkdir(current)
            except Exception as e:
                pass
        
        # Transfer files
        for filename in files:
            if should_exclude(Path(filename)):
                continue
                
            local_file = Path(root) / filename
            remote_file = f"{remote_dir}/{filename}".replace("\\", "/")
            
            try:
                sftp.put(str(local_file), remote_file)
                transferred += 1
                
                # Progress indicator
                if transferred % 50 == 0:
                    pct = int((transferred / total_files) * 100)
                    print(f"  Progress: {transferred}/{total_files} ({pct}%)")
                    
            except Exception as e:
                errors += 1
                if errors <= 5:
                    print(f"  [ERROR] {remote_file}: {e}")
    
    print(f"  Completed: {transferred} files, {errors} errors")
    return transferred

def main():
    print("=" * 70)
    print("MYCOSOFT CODEBASE TRANSFER")
    print(f"Target VM: {VM_IP}")
    print("=" * 70)
    
    # Connect
    print("\nConnecting to VM...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        ssh.connect(VM_IP, username=VM_USER, password=VM_PASS, timeout=30)
    except Exception as e:
        print(f"[ERROR] Failed to connect: {e}")
        sys.exit(1)
    
    print("Connected!")
    
    # Create directory structure
    print("\nCreating directory structure...")
    dirs_to_create = [
        f"{VM_BASE}/website",
        f"{VM_BASE}/mindex", 
        f"{VM_BASE}/mas",
        f"{VM_BASE}/data/postgres",
        f"{VM_BASE}/data/redis",
        f"{VM_BASE}/data/n8n",
        f"{VM_BASE}/data/qdrant",
        f"{VM_BASE}/data/mindex",
        f"{VM_BASE}/backups",
        f"{VM_BASE}/logs",
        f"{VM_BASE}/config"
    ]
    
    for d in dirs_to_create:
        run_cmd(ssh, f"mkdir -p {d}", sudo=True)
    
    run_cmd(ssh, f"chown -R {VM_USER}:{VM_USER} {VM_BASE}", sudo=True)
    print("  Directory structure ready")
    
    # Open SFTP
    sftp = ssh.open_sftp()
    
    total_transferred = 0
    
    # Transfer codebases
    codebases = [
        (WEBSITE_PATH, f"{VM_BASE}/website", "WEBSITE"),
        (MINDEX_PATH, f"{VM_BASE}/mindex", "MINDEX"),
        (MAS_PATH, f"{VM_BASE}/mas", "MAS"),
    ]
    
    for local_path, remote_path, label in codebases:
        count = transfer_directory(sftp, local_path, remote_path, label)
        total_transferred += count
    
    sftp.close()
    
    # Verify transfer
    print("\n" + "=" * 70)
    print("VERIFYING TRANSFER")
    print("=" * 70)
    
    out, _ = run_cmd(ssh, f"find {VM_BASE}/website -type f | wc -l")
    print(f"  Website files: {out.strip()}")
    
    out, _ = run_cmd(ssh, f"find {VM_BASE}/mindex -type f | wc -l")
    print(f"  MINDEX files:  {out.strip()}")
    
    out, _ = run_cmd(ssh, f"find {VM_BASE}/mas -type f | wc -l")
    print(f"  MAS files:     {out.strip()}")
    
    out, _ = run_cmd(ssh, f"du -sh {VM_BASE}/*")
    print(f"\n  Directory sizes:\n{out}")
    
    ssh.close()
    
    print("\n" + "=" * 70)
    print(f"TRANSFER COMPLETE: {total_transferred} total files")
    print("=" * 70)
    print(f"""
Next steps:
1. SSH into VM: ssh {VM_USER}@{VM_IP}
2. Configure .env files
3. Build and start containers

Or run: python scripts/deploy_containers.py
""")

if __name__ == "__main__":
    main()
