"""Check MINDEX core schema data."""
import paramiko

HOST = "192.168.0.189"
USER = "mycosoft"
PASS = "Mushroom1!Mushroom1!"
DB_PASS = "mycosoft_mindex_2026"

def run(ssh, cmd):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=15)
    return stdout.read().decode().strip(), stderr.read().decode().strip()

def psql(ssh, sql):
    out, err = run(ssh, f'docker exec mindex-postgres psql -U mycosoft -d mindex -c "{sql}" 2>/dev/null')
    return out or err

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PASS, timeout=10)

# Check core schema tables and row counts
core_tables = ["core.taxon", "core.compounds", "core.dna_sequences", "core.research_papers", "core.species_images", "core.blobs", "core.blob_download_queue"]
print("[CORE TABLE ROW COUNTS]")
for t in core_tables:
    out = psql(ssh, f"SELECT COUNT(*) FROM {t};")
    lines = out.strip().split('\n')
    count = lines[2].strip() if len(lines) > 2 else "ERROR"
    print(f"  {t}: {count}")

# Check core.taxon columns
print("\n[core.taxon COLUMNS]")
out = psql(ssh, "SELECT column_name, data_type FROM information_schema.columns WHERE table_schema='core' AND table_name='taxon' ORDER BY ordinal_position;")
print(out)

# Sample taxon data
print("\n[SAMPLE core.taxon (first 5)]")
out = psql(ssh, "SELECT id, scientific_name, common_name, rank, source FROM core.taxon LIMIT 5;")
print(out)

# Check graph nodes
print("\n[GRAPH NODES COUNT]")
out = psql(ssh, "SELECT node_type, COUNT(*) FROM graph.nodes GROUP BY node_type;")
print(out)

# Sample graph nodes  
print("\n[SAMPLE GRAPH NODES]")
out = psql(ssh, "SELECT id, name, node_type FROM graph.nodes LIMIT 10;")
print(out)

# Memory entries count
print("\n[MEMORY ENTRIES]")
out = psql(ssh, "SELECT scope, COUNT(*) FROM memory.entries GROUP BY scope;")
print(out)

ssh.close()
print("\n=== DONE ===")
