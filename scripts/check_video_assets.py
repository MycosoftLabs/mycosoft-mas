#!/usr/bin/env python3
"""Check NAS mount and video assets accessibility on VM."""
import paramiko
import sys

def main():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    print("="*70)
    print("VIDEO ASSETS DIAGNOSTIC - Checking NAS Mount & Video Files")
    print("="*70)
    
    try:
        print("\n[1] Connecting to VM 192.168.0.187...")
        client.connect('192.168.0.187', username='mycosoft', password='Mushroom1!Mushroom1!', timeout=30)
        print("    [OK] Connected!\n")
    except Exception as e:
        print(f"    [ERROR] Failed: {e}")
        sys.exit(1)
    
    checks = [
        # NAS mount check
        ('NAS Mount Status', 'mount | grep -E "192\\.168\\.0\\.105|/mnt/mycosoft-nas|/opt/mycosoft/media/website/assets"'),
        
        # Check if NAS mount point exists and has content
        ('NAS Mount Point (mushroom1)', 'ls -lh /mnt/mycosoft-nas/website/assets/mushroom1 2>/dev/null | head -10 || echo "[ERROR] NAS mount not accessible"'),
        
        # Check VM host path
        ('VM Host Assets Path', 'ls -lh /opt/mycosoft/media/website/assets/mushroom1 2>/dev/null | head -10 || echo "[ERROR] VM host path not accessible"'),
        
        # Find website container
        ('Website Container Name', 'docker ps --format "{{.Names}}" | grep -E "mycosoft-website|website" | head -n 1 || echo "[ERROR] No container found"'),
        
        # Check container mounts
        ('Container Mounts', '''cid=$(docker ps --format "{{.Names}}" | grep -E "mycosoft-website|website" | head -n 1); if [ -n "$cid" ]; then docker inspect "$cid" --format '{{range .Mounts}}{{printf "%s -> %s (%s)\\n" .Source .Destination .Type}}{{end}}' | grep -i assets || echo "No assets mount found"; else echo "No container"; fi'''),
        
        # Check files inside container
        ('Container Assets List (first 15 files)', '''cid=$(docker ps --format "{{.Names}}" | grep -E "mycosoft-website|website" | head -n 1); if [ -n "$cid" ]; then docker exec "$cid" sh -c "ls -lh /app/public/assets/mushroom1 2>/dev/null | head -15 || echo '[ERROR] /app/public/assets/mushroom1 not found in container'"; else echo "No container"; fi'''),
        
        # Check specific video files
        ('Check Video Files Exist (key videos)', '''cid=$(docker ps --format "{{.Names}}" | grep -E "mycosoft-website|website" | head -n 1); if [ -n "$cid" ]; then 
  docker exec "$cid" sh -c 'for v in "/app/public/assets/mushroom1/PXL_20250404_210633484.VB-02.MAIN.mp4" "/app/public/assets/mushroom1/waterfall 1.mp4" "/app/public/assets/mushroom1/mushroom 1 walking.mp4" "/app/public/assets/mushroom1/a.mp4"; do if [ -f "$v" ]; then ls -lh "$v" | awk "{print \\$9, \\$5}"; else echo "$v [MISSING]"; fi; done'
else echo "No container"; fi'''),
        
        # Test HTTP accessibility from inside container
        ('HTTP Test: Video Files (from container)', '''cid=$(docker ps --format "{{.Names}}" | grep -E "mycosoft-website|website" | head -n 1); if [ -n "$cid" ]; then 
  docker exec "$cid" node -e "
    const http = require('http');
    const videos = [
      '/assets/mushroom1/PXL_20250404_210633484.VB-02.MAIN.mp4',
      '/assets/mushroom1/waterfall%201.mp4',
      '/assets/mushroom1/mushroom%201%20walking.mp4',
      '/assets/mushroom1/a.mp4'
    ];
    let pending = videos.length;
    videos.forEach(url => {
      http.get({ host: '127.0.0.1', port: 3000, path: url }, res => {
        console.log(url + ' -> HTTP ' + res.statusCode + ' (' + (res.headers['content-type'] || 'no-type') + ')');
        res.resume();
        if (--pending === 0) process.exit(0);
      }).on('error', e => {
        console.log(url + ' -> ERROR: ' + e.message);
        if (--pending === 0) process.exit(0);
      });
    });
  "
else echo "No container"; fi'''),
    ]
    
    for name, cmd in checks:
        print(f"\n{'-'*70}")
        print(f"[CHECK] {name}")
        print(f"{'-'*70}")
        try:
            stdin, stdout, stderr = client.exec_command(cmd, timeout=30)
            output = stdout.read().decode().strip()
            errors = stderr.read().decode().strip()
            
            if output:
                print(output)
            if errors and 'WARNING' not in errors.upper():
                print(f"⚠️  STDERR: {errors}")
                
        except Exception as e:
            print(f"[ERROR] Command failed: {e}")
    
    print(f"\n{'='*70}")
    print("[OK] DIAGNOSTIC COMPLETE")
    print("="*70)
    print("\n[NEXT STEPS]")
    print("  1. If NAS mount missing → Run: sudo bash /home/mycosoft/setup_nas_website_assets.sh")
    print("  2. If container mount missing → Check docker-compose.always-on.yml volumes section")
    print("  3. If files missing in container → Container may need restart after mount")
    print("  4. If HTTP 404 but files exist → Container restart required: docker restart <container>")
    print("  5. If HTTP 200 → Purge Cloudflare cache\n")
    
    client.close()

if __name__ == "__main__":
    main()
