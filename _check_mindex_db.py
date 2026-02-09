"""Check MINDEX PostgreSQL database content via SSH."""
import paramiko

HOST = "192.168.0.189"
USER = "mycosoft"
PASS = "Mushroom1!Mushroom1!"

def run(ssh, cmd):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=15)
    return stdout.read().decode().strip(), stderr.read().decode().strip()

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PASS, timeout=10)

# Check docker-compose and find postgres credentials
out, _ = run(ssh, "cat /opt/mycosoft/mindex/docker-compose.yml")
print("[DOCKER-COMPOSE.YML]")
print(out)

print("\n[INIT-POSTGRES.SQL]")
out, _ = run(ssh, "cat /opt/mycosoft/mindex/init-postgres.sql")
print(out)

# Try to connect to postgres via docker
print("\n[POSTGRES DATABASES]")
out, err = run(ssh, "docker exec mindex-postgres psql -U mycosoft -d mindex -c '\\l' 2>/dev/null")
if not out:
    out, err = run(ssh, "docker exec mindex-postgres psql -U postgres -c '\\l' 2>/dev/null")
print(out or err)

print("\n[MINDEX TABLES]")
out, err = run(ssh, "docker exec mindex-postgres psql -U mycosoft -d mindex -c \"SELECT schemaname, tablename FROM pg_tables WHERE schemaname NOT IN ('pg_catalog','information_schema') ORDER BY schemaname, tablename;\" 2>/dev/null")
if not out:
    out, err = run(ssh, "docker exec mindex-postgres psql -U postgres -d mindex -c \"SELECT schemaname, tablename FROM pg_tables WHERE schemaname NOT IN ('pg_catalog','information_schema') ORDER BY schemaname, tablename;\" 2>/dev/null")
print(out or err)

print("\n[TABLE ROW COUNTS]")
tables_to_check = ["taxa", "observations", "compounds", "genomes", "traits", "external_ids", "synonyms", "taxa_compounds"]
for t in tables_to_check:
    out, err = run(ssh, f"docker exec mindex-postgres psql -U mycosoft -d mindex -c \"SELECT COUNT(*) FROM {t};\" 2>/dev/null")
    count = "N/A"
    if out:
        lines = out.strip().split('\n')
        if len(lines) >= 3:
            count = lines[2].strip()
    print(f"  {t}: {count}")

print("\n[SAMPLE TAXA (first 5)]")
out, _ = run(ssh, "docker exec mindex-postgres psql -U mycosoft -d mindex -c \"SELECT id, scientific_name, common_name, rank, source, (image_url IS NOT NULL) as has_img, (description IS NOT NULL) as has_desc FROM taxa ORDER BY id LIMIT 5;\" 2>/dev/null")
print(out or "Could not query")

print("\n[TAXA WITH IMAGES]")
out, _ = run(ssh, "docker exec mindex-postgres psql -U mycosoft -d mindex -c \"SELECT COUNT(*) as with_images FROM taxa WHERE image_url IS NOT NULL;\" 2>/dev/null")
print(out or "N/A")

print("\n[TAXA SOURCES]")
out, _ = run(ssh, "docker exec mindex-postgres psql -U mycosoft -d mindex -c \"SELECT source, COUNT(*) FROM taxa GROUP BY source ORDER BY count DESC;\" 2>/dev/null")
print(out or "N/A")

ssh.close()
print("\n=== DONE ===")
