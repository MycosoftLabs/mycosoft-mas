#!/usr/bin/env python3
"""SSH Helper for GPU Node Management"""
import paramiko
import sys
import io

# Fix Windows encoding issues
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

HOST = '192.168.0.190'
USER = 'mycosoft'
PASS = 'REDACTED_VM_SSH_PASSWORD'
# Escaped password for use in bash commands (escape ! for bash history expansion)
PASS_ESCAPED = PASS.replace('!', '\\!')

def connect():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(HOST, username=USER, password=PASS, timeout=15)
    return ssh

def run_cmd(ssh, cmd, sudo=False):
    if sudo:
        # Use single quotes to prevent bash history expansion of ! in password
        pass_safe = PASS.replace("'", "'\"'\"'")
        cmd = f"echo '{pass_safe}' | sudo -S {cmd}"
    stdin, stdout, stderr = ssh.exec_command(cmd)
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    # Filter out sudo password prompt from stderr
    err = '\n'.join(line for line in err.split('\n') if not line.startswith('[sudo]'))
    return out, err.strip()

def main():
    action = sys.argv[1] if len(sys.argv) > 1 else 'status'
    
    ssh = connect()
    
    if action == 'status':
        print('=== GPU (lspci) ===')
        out, _ = run_cmd(ssh, 'lspci | grep -i nvidia')
        print(out or 'No NVIDIA GPU found in lspci')
        
        print('=== nvidia-smi ===')
        out, err = run_cmd(ssh, 'nvidia-smi 2>&1 || echo "Driver not installed yet"')
        print(out)
        
        print('=== Disk Layout ===')
        out, _ = run_cmd(ssh, 'lsblk')
        print(out)
        
        print('=== Memory ===')
        out, _ = run_cmd(ssh, 'free -h')
        print(out)
        
        print('=== Docker ===')
        out, _ = run_cmd(ssh, 'docker --version 2>&1 || echo "Docker not installed yet"')
        print(out)
        
    elif action == 'bootstrap':
        # Transfer and run bootstrap script
        print('Transferring bootstrap script...')
        
        # Read script and convert Windows line endings to Unix
        script_path = r'c:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas\scripts\gpu-node\mycosoft-gpu-node-bootstrap.sh'
        with open(script_path, 'r', encoding='utf-8') as f:
            script_content = f.read()
        
        # Convert CRLF to LF
        script_content = script_content.replace('\r\n', '\n')
        
        # Write to remote via SFTP
        sftp = ssh.open_sftp()
        with sftp.file('/tmp/mycosoft-gpu-node-bootstrap.sh', 'w') as remote_file:
            remote_file.write(script_content)
        sftp.close()
        print('Bootstrap script transferred (with Unix line endings).')
        
        print('Making executable...')
        run_cmd(ssh, 'chmod +x /tmp/mycosoft-gpu-node-bootstrap.sh')
        
        print('Running bootstrap (this will take several minutes)...')
        print('=' * 60)
        
        import time
        
        # Use interactive shell for better sudo handling
        shell = ssh.invoke_shell(width=120, height=50)
        time.sleep(1)
        
        # Clear initial output
        while shell.recv_ready():
            shell.recv(4096)
        
        # Run with nohup so it survives connection issues, log to file
        shell.send('sudo -S nohup bash /tmp/mycosoft-gpu-node-bootstrap.sh -y > /tmp/bootstrap.log 2>&1 &\n')
        time.sleep(0.5)
        
        # Send password
        shell.send(PASS + '\n')
        time.sleep(2)
        
        # Clear output
        while shell.recv_ready():
            shell.recv(4096)
        
        print('Bootstrap started in background. Monitoring progress...')
        print('Log file: /tmp/bootstrap.log')
        print('=' * 60)
        
        # Monitor by tailing the log
        last_line_count = 0
        stable_count = 0
        max_stable = 30  # 30 iterations of no change (with 10s sleep = 5 min of no change)
        
        while stable_count < max_stable:
            time.sleep(10)
            
            # Check if process is still running
            stdin, stdout, stderr = ssh.exec_command('pgrep -f "mycosoft-gpu-node-bootstrap" | head -1')
            pid = stdout.read().decode().strip()
            
            # Get latest log content
            stdin, stdout, stderr = ssh.exec_command('tail -50 /tmp/bootstrap.log 2>/dev/null')
            log_tail = stdout.read().decode('utf-8', errors='replace')
            
            if log_tail:
                lines = log_tail.strip().split('\n')
                # Print new lines
                print(log_tail, end='', flush=True)
                
                if len(lines) == last_line_count:
                    stable_count += 1
                else:
                    stable_count = 0
                    last_line_count = len(lines)
            
            if not pid:
                print('\n\nBootstrap process finished.')
                break
        
        # Show final status
        print('\n' + '=' * 60)
        stdin, stdout, stderr = ssh.exec_command('tail -20 /tmp/bootstrap.log')
        print('Final log lines:')
        print(stdout.read().decode('utf-8', errors='replace'))
        
    elif action == 'cmd':
        # Run arbitrary command
        cmd = ' '.join(sys.argv[2:])
        out, err = run_cmd(ssh, cmd)
        print(out)
        if err:
            print('STDERR:', err)
            
    elif action == 'sudo':
        # Run arbitrary command with sudo
        cmd = ' '.join(sys.argv[2:])
        out, err = run_cmd(ssh, cmd, sudo=True)
        print(out)
        if err:
            print('STDERR:', err)
    
    elif action == 'clean_apt':
        # Clean up apt locks and stuck processes
        print('Cleaning up apt locks...')
        import time
        
        # Use interactive shell
        shell = ssh.invoke_shell()
        time.sleep(0.5)
        
        # Send sudo command
        shell.send('sudo -S pkill -9 apt; sudo pkill -9 dpkg; sleep 1; sudo rm -f /var/lib/dpkg/lock-frontend /var/lib/dpkg/lock /var/cache/apt/archives/lock /var/lib/apt/lists/lock; sudo dpkg --configure -a; echo CLEANUP_DONE\n')
        time.sleep(0.5)
        
        # Send password when prompted
        shell.send(PASS + '\n')
        
        # Wait and collect output
        time.sleep(5)
        output = ''
        while shell.recv_ready():
            output += shell.recv(4096).decode('utf-8', errors='replace')
        
        print(output)
        
        if 'CLEANUP_DONE' in output:
            print('\nCleanup completed successfully.')
        else:
            print('\nCleanup may not have completed - check output above.')
    
    elif action == 'kill_bootstrap':
        # Kill stuck bootstrap processes
        print('Killing stuck bootstrap processes...')
        import time
        shell = ssh.invoke_shell()
        time.sleep(0.5)
        shell.send('sudo -S pkill -9 -f "mycosoft-gpu-node-bootstrap"; echo KILLED\n')
        time.sleep(0.5)
        shell.send(PASS + '\n')
        time.sleep(3)
        output = ''
        while shell.recv_ready():
            output += shell.recv(4096).decode('utf-8', errors='replace')
        print(output)
        if 'KILLED' in output:
            print('\nKilled successfully.')
    
    elif action == 'run_bootstrap_fg':
        # Run bootstrap in foreground with proper output capture
        print('Transferring bootstrap script...')
        
        # Read script and convert Windows line endings to Unix
        script_path = r'c:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas\scripts\gpu-node\mycosoft-gpu-node-bootstrap.sh'
        with open(script_path, 'r', encoding='utf-8') as f:
            script_content = f.read()
        
        # Convert CRLF to LF
        script_content = script_content.replace('\r\n', '\n')
        
        # Write to remote via SFTP
        sftp = ssh.open_sftp()
        with sftp.file('/tmp/mycosoft-gpu-node-bootstrap.sh', 'w') as remote_file:
            remote_file.write(script_content)
        sftp.close()
        print('Bootstrap script transferred.')
        
        print('Making executable...')
        run_cmd(ssh, 'chmod +x /tmp/mycosoft-gpu-node-bootstrap.sh')
        
        print('Running bootstrap (this will take several minutes)...')
        print('=' * 60)
        sys.stdout.flush()
        
        import time
        
        # Use interactive shell for proper TTY handling
        shell = ssh.invoke_shell(width=120, height=50)
        time.sleep(1)
        
        # Clear initial output
        while shell.recv_ready():
            shell.recv(4096)
        
        # Start the bootstrap with sudo and script output to tty
        shell.send('sudo -S bash /tmp/mycosoft-gpu-node-bootstrap.sh -y 2>&1\n')
        time.sleep(0.5)
        shell.send(PASS + '\n')
        
        # Stream output in real-time
        shell.settimeout(600)  # 10 minute timeout
        buffer = ''
        last_output_time = time.time()
        
        while True:
            try:
                if shell.recv_ready():
                    chunk = shell.recv(4096).decode('utf-8', errors='replace')
                    print(chunk, end='', flush=True)
                    buffer += chunk
                    last_output_time = time.time()
                    
                    # Check for completion markers
                    if 'Bootstrap script completed' in buffer or 'exited with code' in buffer:
                        break
                else:
                    time.sleep(0.5)
                    # Check for stall (no output for 5 minutes)
                    if time.time() - last_output_time > 300:
                        print('\n\n=== STALLED: No output for 5 minutes ===')
                        break
            except Exception as e:
                print(f'\nError: {e}')
                break
        
        print('\n' + '=' * 60)
        print('Bootstrap completed or stalled. Check output above.')
    
    elif action == 'harden_ssh':
        # Harden SSH by disabling password authentication
        print('Hardening SSH configuration...')
        import time
        
        shell = ssh.invoke_shell()
        time.sleep(0.5)
        
        # Clear initial output
        while shell.recv_ready():
            shell.recv(4096)
        
        # Create hardening config using heredoc
        shell.send('sudo -S tee /etc/ssh/sshd_config.d/99-hardening.conf << "SSHEOF"\n')
        time.sleep(0.5)
        shell.send(PASS + '\n')
        time.sleep(1)
        
        ssh_config = """# SSH Hardening - mycosoft-gpu01
PasswordAuthentication no
ChallengeResponseAuthentication no
UsePAM yes
PermitRootLogin no
PubkeyAuthentication yes
"""
        shell.send(ssh_config)
        shell.send('SSHEOF\n')
        time.sleep(2)
        
        # Clear output
        while shell.recv_ready():
            shell.recv(4096)
        
        # Restart SSH
        print('Restarting SSH service...')
        shell.send('sudo systemctl restart ssh\n')
        time.sleep(3)
        
        # Verify
        shell.send('cat /etc/ssh/sshd_config.d/99-hardening.conf\n')
        time.sleep(2)
        
        output = ''
        while shell.recv_ready():
            output += shell.recv(4096).decode('utf-8', errors='replace')
        
        if 'PasswordAuthentication no' in output:
            print('SSH hardening config written successfully:')
            for line in output.split('\n'):
                if 'Authentication' in line or 'PermitRoot' in line or 'Pubkey' in line or 'UsePAM' in line:
                    print(f'  {line.strip()}')
            print('\nSSH hardening complete!')
            print('WARNING: Password authentication is now disabled.')
            print('Make sure you can connect with your SSH key before closing this session!')
        else:
            print('WARNING: SSH hardening may have failed. Output:')
            print(output)
        
        shell.close()
    
    ssh.close()

if __name__ == '__main__':
    main()
