#!/usr/bin/env python3
"""Check mushroom1 videos on Sandbox VM."""

import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

print("Connecting to Sandbox VM...")
client.connect('192.168.0.187', username='mycosoft', password='REDACTED_VM_SSH_PASSWORD', timeout=10)

# Check mushroom1 videos directly
print("\n" + "=" * 60)
print("Checking /opt/mycosoft/media/website/assets/mushroom1/")
print("=" * 60)
stdin, stdout, stderr = client.exec_command('ls -la /opt/mycosoft/media/website/assets/mushroom1/')
output = stdout.read().decode().strip()
print(output if output else "Empty or not found")

# Check all asset directories
print("\n" + "=" * 60)
print("All asset directories:")
print("=" * 60)
stdin, stdout, stderr = client.exec_command('find /opt/mycosoft/media/website/assets -type f -name "*.mp4" 2>/dev/null | head -20')
videos = stdout.read().decode().strip()
print(videos if videos else "No MP4 files found")

# Also check container's view
print("\n" + "=" * 60)
print("Container's view of /app/public/assets:")
print("=" * 60)
stdin, stdout, stderr = client.exec_command('docker exec mycosoft-website ls -la /app/public/assets/ 2>/dev/null | head -10')
container_view = stdout.read().decode().strip()
print(container_view if container_view else "Could not check container")

print("\n" + "=" * 60)
print("Container's mushroom1 folder:")
print("=" * 60)
stdin, stdout, stderr = client.exec_command('docker exec mycosoft-website ls -la /app/public/assets/mushroom1/ 2>/dev/null')
container_m1 = stdout.read().decode().strip()
print(container_m1 if container_m1 else "Not found or empty")

client.close()
