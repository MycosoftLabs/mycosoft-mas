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

def run(cmd):
    _, out, err = client.exec_command(cmd, timeout=30)
    return (out.read() + err.read()).decode().strip()

# Wait for container to be healthy
print("Waiting for container to be ready...")
for i in range(12):
    status = run("docker inspect mycosoft-website --format '{{.State.Health.Status}}' 2>/dev/null")
    print(f"  Health: {status}")
    if status == 'healthy':
        break
    time.sleep(10)

print("\n=== Testing asset URLs on production (port 3000) ===")
tests = [
    ("About page",        "http://localhost:3000/about"),
    ("Morgan photo",      "http://localhost:3000/assets/team/morgan-rockwell.png"),
    ("Garret photo",      "http://localhost:3000/assets/team/garret-baquet.png"),
    ("RJ photo",          "http://localhost:3000/assets/team/rj-ricasata.png"),
    ("Chris photo",       "http://localhost:3000/assets/team/chris-freetage.png"),
    ("Beto photo",        "http://localhost:3000/assets/team/alberto-septien.png"),
    ("MYCA logo square",  "http://localhost:3000/assets/logos/myca-logo-square.png"),
    ("MYCA logo full",    "http://localhost:3000/assets/logos/myca-logo-full.png"),
    ("Commercial video",  "http://localhost:3000/assets/about%20us/Mycosoft%20Commercial%201.mp4"),
    ("BG video",          "http://localhost:3000/assets/about%20us/10343918-hd_1920_1080_24fps.mp4"),
]
for name, url in tests:
    code = run(f"curl -s -o /dev/null -w '%{{http_code}}' '{url}'")
    status = "OK" if code in ("200", "206") else f"FAIL ({code})"
    print(f"  {status:8s}  {name}")

client.close()
