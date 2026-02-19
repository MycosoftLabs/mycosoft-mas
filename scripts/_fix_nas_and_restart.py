import paramiko, os, time

def load_creds():
    path = os.path.join(os.path.dirname(__file__), '..', '.credentials.local')
    for line in open(path).read().splitlines():
        if '=' in line and not line.startswith('#'):
            k, v = line.split('=', 1)
            os.environ[k.strip()] = v.strip()

load_creds()
password = os.environ.get('VM_SSH_PASSWORD') or os.environ.get('VM_PASSWORD')

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('192.168.0.187', username='mycosoft', password=password, timeout=20)

def run(cmd, show=True):
    _, out, err = client.exec_command(cmd, timeout=60)
    result = (out.read() + err.read()).decode().strip()
    if show and result:
        print(f"  {result}")
    return result

NAS = "/mnt/mycosoft-nas/website/assets"
SRC = f"{NAS}/about us/public/assets"

print("=== Step 1: Create correct NAS folders ===")
run(f"mkdir -p '{NAS}/team' '{NAS}/logos'")

print("\n=== Step 2: Copy team photos to NAS root ===")
run(f"cp '{SRC}/team/'*.png '{NAS}/team/'")
run(f"ls '{NAS}/team/'")

print("\n=== Step 3: Copy logos to NAS root ===")
run(f"cp '{SRC}/logos/'*.png '{NAS}/logos/'")
run(f"ls '{NAS}/logos/'")

print("\n=== Step 4: Verify about us videos ===")
run(f"ls '{NAS}/about us/'")

print("\n=== Step 5: Check current container ===")
container_info = run("docker ps --format '{{.Names}}\t{{.Image}}\t{{.Status}}' | grep -i website")
print(f"  Container: {container_info}")

# Get the image name from the running container
image = run("docker inspect mycosoft-website --format '{{.Config.Image}}' 2>/dev/null").strip()
if not image:
    image = "mycosoft-always-on-mycosoft-website:latest"
print(f"  Image: {image}")

print("\n=== Step 6: Stop old container ===")
run("docker stop mycosoft-website 2>/dev/null; docker rm mycosoft-website 2>/dev/null")
time.sleep(3)

print("\n=== Step 7: Start container with NAS mount ===")
cmd = (
    f"docker run -d --name mycosoft-website -p 3000:3000 "
    f"-v '{NAS}:/app/public/assets:ro' "
    f"--restart unless-stopped {image}"
)
print(f"  Running: {cmd}")
run(cmd)
time.sleep(5)

print("\n=== Step 8: Verify container running ===")
run("docker ps | grep mycosoft-website")

print("\n=== Step 9: Test a team image is accessible ===")
run("curl -s -o /dev/null -w '%{http_code}' 'http://localhost:3000/assets/team/morgan-rockwell.png'")
run("curl -s -o /dev/null -w '%{http_code}' 'http://localhost:3000/assets/logos/myca-logo-square.png'")
run("curl -s -o /dev/null -w '%{http_code}' 'http://localhost:3000/assets/about%20us/Mycosoft%20Commercial%201.mp4'")

print("\n=== Done ===")
client.close()
