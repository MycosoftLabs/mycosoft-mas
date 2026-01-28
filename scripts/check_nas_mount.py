#!/usr/bin/env python3
"""Check NAS mount on Sandbox VM."""

import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

print("Connecting to Sandbox VM...")
client.connect('192.168.0.187', username='mycosoft', password='Mushroom1!Mushroom1!', timeout=10)
print("Connected!")

# Check NAS mount
print("\n" + "=" * 60)
print("Checking NAS mounts...")
print("=" * 60)
stdin, stdout, stderr = client.exec_command('mount | grep -E "192.168.0.105|mycosoft|media"')
mounts = stdout.read().decode().strip()
print(mounts if mounts else "No NAS mounts found in fstab")

# Check Docker volume mounts for website
print("\n" + "=" * 60)
print("Checking website container mounts...")
print("=" * 60)
stdin, stdout, stderr = client.exec_command('docker inspect mycosoft-website --format "{{range .Mounts}}{{.Source}} -> {{.Destination}}\n{{end}}"')
docker_mounts = stdout.read().decode().strip()
print(docker_mounts if docker_mounts else "No mounts found")

# Check if media directory exists
print("\n" + "=" * 60)
print("Checking media directory...")
print("=" * 60)
stdin, stdout, stderr = client.exec_command('ls -la /opt/mycosoft/media/website/assets/ 2>/dev/null | head -10')
media_dir = stdout.read().decode().strip()
print(media_dir if media_dir else "Media directory not found")

# Check device videos specifically
print("\n" + "=" * 60)
print("Checking device video directories...")
print("=" * 60)
stdin, stdout, stderr = client.exec_command('ls -la /opt/mycosoft/media/website/assets/devices/ 2>/dev/null')
devices = stdout.read().decode().strip()
print(devices if devices else "Devices directory not found")

# Check mushroom1 videos
print("\n" + "=" * 60)
print("Checking mushroom1 videos...")
print("=" * 60)
stdin, stdout, stderr = client.exec_command('ls -la /opt/mycosoft/media/website/assets/devices/mushroom1/ 2>/dev/null | head -15')
mushroom1 = stdout.read().decode().strip()
print(mushroom1 if mushroom1 else "Mushroom1 directory not found")

client.close()
