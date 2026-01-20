#!/usr/bin/env python3
"""Check VM status and fix deployment."""
import paramiko

def main():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    print("Connecting to VM 192.168.0.187...")
    client.connect('192.168.0.187', username='mycosoft', password='Mushroom1!Mushroom1!', timeout=30)
    print("Connected!\n")
    
    # Check website directory and docker
    cmds = [
        ('Check home directory', 'ls -la /home/mycosoft/'),
        ('Check docker containers', 'docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Image}}"'),
        ('Check website images', 'docker images | grep -i website || echo "No website images found"'),
        ('Check mycosoft-production dir', 'ls -la /home/mycosoft/mycosoft-production/ 2>/dev/null || echo "Dir not found"'),
        ('Check docker-compose files', 'find /home/mycosoft -name "docker-compose*.yml" 2>/dev/null | head -10'),
        ('Check git repos', 'find /home/mycosoft -name ".git" -type d 2>/dev/null | head -10'),
        ('Check VM media assets (mushroom1)', 'ls -la /opt/mycosoft/media/website/assets/mushroom1 2>/dev/null | head -50 || echo "No /opt/mycosoft/media/website/assets/mushroom1"'),
        ('Find website container name', 'docker ps --format "{{.Names}}" | grep -E "mycosoft-website|website" | head -n 5 || true'),
        ('Website container mounts', 'cid=$(docker ps --format "{{.Names}}" | grep -E "mycosoft-website|website" | head -n 1 || true); if [ -n "$cid" ]; then docker inspect "$cid" --format "{{range .Mounts}}{{println .Source \\"->\\" .Destination}}{{end}}"; else echo "No website container found"; fi'),
        ('Website container public assets (mushroom1)', 'cid=$(docker ps --format "{{.Names}}" | grep -E "mycosoft-website|website" | head -n 1 || true); if [ -n "$cid" ]; then docker exec "$cid" sh -lc "ls -la /app/public/assets/mushroom1 2>/dev/null | head -50 || echo \\"No /app/public/assets/mushroom1\\""; else echo "No website container found"; fi'),
        ('Website container filesystem overview', 'cid=$(docker ps --format "{{.Names}}" | grep -E "mycosoft-website|website" | head -n 1 || true); if [ -n "$cid" ]; then docker exec "$cid" sh -lc "echo \\"== ls /app ==\\"; ls -la /app | head -n 80; echo \\"== find server.js ==\\"; find /app -maxdepth 5 -name server.js -o -name index.js | head -n 40; echo \\"== ls /app/public ==\\"; ls -la /app/public 2>/dev/null | head -n 80 || echo \\"No /app/public\\"; echo \\"== ls /app/.next ==\\"; ls -la /app/.next 2>/dev/null | head -n 80 || echo \\"No /app/.next\\""; else echo "No website container found"; fi'),
        ('Cloudflared config (ingress)', 'sed -n "1,220p" /home/mycosoft/.cloudflared/config.yml 2>/dev/null || echo "No /home/mycosoft/.cloudflared/config.yml"'),
        ('Find other cloudflared configs (service lines only)', 'grep -RIn --include="*.yml" --include="*.yaml" "service:" /home/mycosoft/.cloudflared /etc/cloudflared 2>/dev/null | head -n 60 || true'),
        ('Website container self-test (localhost static)', 'cid=$(docker ps --format "{{.Names}}" | grep -E "mycosoft-website|website" | head -n 1 || true); if [ -n "$cid" ]; then docker exec "$cid" node -e "const http=require(\\\"http\\\"); const urls=[\\\"/placeholder.svg\\\",\\\"/assets/mushroom1/1.jpg\\\",\\\"/assets/mushroom1/Main%20A.jpg\\\"]; let pending=urls.length; for (const u of urls){ http.get({host:\\\"127.0.0.1\\\",port:3000,path:u},res=>{ console.log(u, res.statusCode, res.headers[\\\"content-type\\\"]); res.resume(); if(--pending===0) process.exit(0); }).on(\\\"error\\\",e=>{ console.log(u,\\\"ERROR\\\",e.message); if(--pending===0) process.exit(0); }); }"; else echo "No website container found"; fi'),
        ('Website Next routes-manifest (basePath/assetPrefix)', 'cid=$(docker ps --format "{{.Names}}" | grep -E "mycosoft-website|website" | head -n 1 || true); if [ -n "$cid" ]; then docker exec "$cid" node -e "const fs=require(\\\"fs\\\"); const p=\\\"/app/.next/routes-manifest.json\\\"; const raw=fs.readFileSync(p,\\\"utf8\\\"); const m=JSON.parse(raw); console.log(JSON.stringify({basePath:m.basePath,assetPrefix:m.assetPrefix,i18n:m.i18n},null,2));"; else echo "No website container found"; fi'),
        ('Website server.js (static/public hints)', 'cid=$(docker ps --format "{{.Names}}" | grep -E "mycosoft-website|website" | head -n 1 || true); if [ -n "$cid" ]; then docker exec "$cid" sh -lc "sed -n \\"1,220p\\" /app/server.js | head -n 220"; else echo "No website container found"; fi'),
        ('Website container fs check (public assets exist)', 'cid=$(docker ps --format "{{.Names}}" | grep -E "mycosoft-website|website" | head -n 1 || true); if [ -n "$cid" ]; then docker exec "$cid" node -e "const fs=require(\\\"fs\\\"); const paths=[\\\"/app/public/placeholder.svg\\\",\\\"/app/public/assets\\\",\\\"/app/public/assets/mushroom1/1.jpg\\\"]; for (const p of paths){ try{ const st=fs.statSync(p); console.log(p, st.isDirectory()?\\\"dir\\\":\\\"file\\\", st.size); } catch(e){ console.log(p, \\\"MISSING\\\", e.code); } }"; else echo "No website container found"; fi'),
        ('VM + container smoke test for /assets (test.txt)', 'echo "mycosoft-assets-ok" > /opt/mycosoft/media/website/assets/test.txt && cid=$(docker ps --format "{{.Names}}" | grep -E "mycosoft-website|website" | head -n 1 || true) && if [ -n "$cid" ]; then docker exec "$cid" node -e "const http=require(\\\"http\\\"); http.get({host:\\\"127.0.0.1\\\",port:3000,path:\\\"/assets/test.txt\\\"},res=>{ console.log(\\\"/assets/test.txt\\\", res.statusCode, res.headers[\\\"content-type\\\"]); res.resume(); }).on(\\\"error\\\",e=>console.log(\\\"ERROR\\\",e.message));"; else echo "No website container found"; fi'),
    ]
    
    for name, cmd in cmds:
        print(f"\n{'='*60}")
        print(f">>> {name}")
        print(f">>> {cmd}")
        print('='*60)
        stdin, stdout, stderr = client.exec_command(cmd, timeout=30)
        output = stdout.read().decode()
        errors = stderr.read().decode()
        print(output)
        if errors:
            print(f"STDERR: {errors}")
    
    client.close()
    print("\n\nDone!")

if __name__ == "__main__":
    main()
