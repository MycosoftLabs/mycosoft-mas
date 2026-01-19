#!/usr/bin/env python3
"""Check VM CPU and diagnose build issue."""
import paramiko

def run_cmd(client, cmd, name):
    print(f"\n>>> {name}")
    stdin, stdout, stderr = client.exec_command(cmd, timeout=60)
    output = stdout.read().decode()
    errors = stderr.read().decode()
    if output:
        print(output)
    if errors:
        print(f"STDERR: {errors}")
    return output

def main():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    print("Connecting to VM...")
    client.connect('192.168.0.187', username='mycosoft', password='Mushroom1!Mushroom1!', timeout=30)
    print("Connected!")
    
    # Check CPU info
    run_cmd(client, 'cat /proc/cpuinfo | head -30', 'CPU Info')
    run_cmd(client, 'uname -a', 'System Info')
    run_cmd(client, 'free -h', 'Memory')
    
    # Check the scraper files
    run_cmd(client, 'ls -la /opt/mycosoft/website/lib/scrapers/ 2>/dev/null || ls -la /home/mycosoft/mycosoft/website/lib/scrapers/', 'Scraper files')
    
    # Check celestrak-scraper
    run_cmd(client, 'cat /home/mycosoft/mycosoft/website/lib/scrapers/celestrak-scraper.ts | head -50', 'Celestrak scraper code')
    
    client.close()

if __name__ == "__main__":
    main()
