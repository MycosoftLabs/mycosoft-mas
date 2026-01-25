#!/usr/bin/env python3
"""Run simple ETL to populate MINDEX"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import paramiko
import time
import base64

VM_IP = "192.168.0.187"
VM_USER = "mycosoft"
VM_PASSWORD = "REDACTED_VM_SSH_PASSWORD"

ETL_CODE = '''
import requests
import psycopg2
import time
from datetime import datetime

DB = {"host": "host.docker.internal", "port": 5434, "user": "mindex", "password": "mindex", "database": "mindex"}
INAT = "https://api.inaturalist.org/v1"

conn = psycopg2.connect(**DB)
cur = conn.cursor()

print("Fetching fungi from iNaturalist...")
params = {"taxon_id": 47170, "rank": "species", "per_page": 200, "page": 1, "order_by": "observations_count"}
total = 0
inserted = 0

for page in range(1, 6):
    params["page"] = page
    print(f"  Page {page}...")
    r = requests.get(INAT + "/taxa", params=params, timeout=30)
    if r.status_code != 200:
        break
    results = r.json().get("results", [])
    if not results:
        break
    for t in results:
        total += 1
        anc = t.get("ancestors", [])
        kingdom = phylum = cls = order = family = genus = None
        for a in anc:
            if a.get("rank") == "kingdom": kingdom = a.get("name")
            elif a.get("rank") == "phylum": phylum = a.get("name")
            elif a.get("rank") == "class": cls = a.get("name")
            elif a.get("rank") == "order": order = a.get("name")
            elif a.get("rank") == "family": family = a.get("name")
            elif a.get("rank") == "genus": genus = a.get("name")
        photo = t.get("default_photo") or {}
        cur.execute("SELECT 1 FROM taxa WHERE source=%s AND source_id=%s", ("inat", str(t["id"])))
        if not cur.fetchone():
            cur.execute("INSERT INTO taxa (scientific_name, common_name, kingdom, phylum, class, ord, family, genus, rank, source, source_id, image_url, thumbnail_url) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (t.get("name"), t.get("preferred_common_name"), kingdom or "Fungi", phylum, cls, order, family, genus, t.get("rank"), "inat", str(t["id"]), photo.get("medium_url"), photo.get("square_url")))
            inserted += 1
    conn.commit()
    time.sleep(1)

cur.execute("SELECT COUNT(*) FROM taxa")
print(f"Done: {total} processed, {inserted} inserted, {cur.fetchone()[0]} total taxa")
conn.close()
'''

def run_ssh_cmd(cmd, timeout=300):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh.connect(VM_IP, username=VM_USER, password=VM_PASSWORD, timeout=30, banner_timeout=30)
        stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
        out = stdout.read().decode('utf-8', errors='replace')
        err = stderr.read().decode('utf-8', errors='replace')
        ssh.close()
        return out, err
    except Exception as e:
        return None, str(e)

print("=" * 60)
print("  MINDEX ETL - Simple Population")
print("=" * 60)

print("\n[1] Creating ETL container...")
out, err = run_ssh_cmd("docker rm -f mindex-etl 2>/dev/null; docker run -d --name mindex-etl --add-host=host.docker.internal:host-gateway python:3.11-slim sleep 600")
print(out[:50] if out else err)

print("\n[2] Installing dependencies...")
out, err = run_ssh_cmd("docker exec mindex-etl pip install --no-cache-dir requests psycopg2-binary 2>&1 | tail -3")
print(out or err)

print("\n[3] Writing ETL script...")
script_b64 = base64.b64encode(ETL_CODE.encode()).decode()
run_ssh_cmd(f'echo "{script_b64}" | base64 -d > /tmp/etl.py')
run_ssh_cmd("docker cp /tmp/etl.py mindex-etl:/etl.py")
print("Done")

print("\n[4] Running ETL (scraping iNaturalist fungi)...")
out, err = run_ssh_cmd("docker exec mindex-etl python3 /etl.py 2>&1", timeout=300)
print(out or err)

print("\n[5] Cleanup...")
run_ssh_cmd("docker rm -f mindex-etl 2>/dev/null")

print("\n[6] Testing API stats...")
out, err = run_ssh_cmd("curl -s http://localhost:8000/api/mindex/stats")
print(out)

print("\n" + "=" * 60)
