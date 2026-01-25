#!/usr/bin/env python3
"""Run ETL inside Docker container"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import paramiko
import time

VM_IP = "192.168.0.187"
VM_USER = "mycosoft"
VM_PASSWORD = "REDACTED_VM_SSH_PASSWORD"

def run_ssh_cmd(cmd, timeout=600):
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
print("  MINDEX ETL via Docker")
print("=" * 60)

print("\n[1] Creating ETL container...")
out, err = run_ssh_cmd("""
docker run -d --name mindex-etl-runner \
  --add-host=host.docker.internal:host-gateway \
  -e DB_HOST=host.docker.internal \
  -e DB_PORT=5434 \
  python:3.11-slim sleep 3600
""")
print(out or err)

print("\n[2] Installing dependencies in container...")
out, err = run_ssh_cmd("docker exec mindex-etl-runner pip install --no-cache-dir requests psycopg2-binary 2>&1 | tail -5")
print(out or err)

print("\n[3] Running ETL script inside container...")
# We'll execute the scraping inline
out, err = run_ssh_cmd('''docker exec mindex-etl-runner python3 -c "
import requests
import psycopg2
import time
from datetime import datetime

DB_CONFIG = {
    'host': 'host.docker.internal',
    'port': 5434,
    'user': 'mindex',
    'password': 'mindex',
    'database': 'mindex'
}

INAT_API = 'https://api.inaturalist.org/v1'

def get_connection():
    return psycopg2.connect(**DB_CONFIG)

print('Starting iNaturalist fungi scrape...')

conn = get_connection()
cur = conn.cursor()

# Log ETL start
cur.execute('INSERT INTO etl_runs (pipeline, status) VALUES (%s, %s) RETURNING id', ('iNaturalist', 'running'))
run_id = cur.fetchone()[0]
conn.commit()

url = INAT_API + '/taxa'
params = {
    'taxon_id': 47170,
    'rank': 'species,subspecies,variety',
    'per_page': 200,
    'page': 1,
    'order': 'desc',
    'order_by': 'observations_count'
}

total_processed = 0
total_inserted = 0
limit = 1000

try:
    while total_processed < limit:
        print(f'  Fetching page {params[\"page\"]}...')
        response = requests.get(url, params=params, timeout=30)
        
        if response.status_code != 200:
            print(f'  API error: {response.status_code}')
            break
        
        data = response.json()
        results = data.get('results', [])
        
        if not results:
            print('  No more results')
            break
        
        for taxon in results:
            total_processed += 1
            
            scientific_name = taxon.get('name', '')
            common_name = taxon.get('preferred_common_name', '')
            rank = taxon.get('rank', '')
            
            ancestors = taxon.get('ancestors', [])
            kingdom = phylum = cls = order = family = genus = None
            for anc in ancestors:
                anc_rank = anc.get('rank')
                anc_name = anc.get('name')
                if anc_rank == 'kingdom': kingdom = anc_name
                elif anc_rank == 'phylum': phylum = anc_name
                elif anc_rank == 'class': cls = anc_name
                elif anc_rank == 'order': order = anc_name
                elif anc_rank == 'family': family = anc_name
                elif anc_rank == 'genus': genus = anc_name
            
            photo = taxon.get('default_photo', {}) or {}
            image_url = photo.get('medium_url', '')
            thumbnail_url = photo.get('square_url', '')
            
            cur.execute('SELECT id FROM taxa WHERE source = %s AND source_id = %s', ('inat', str(taxon['id'])))
            existing = cur.fetchone()
            
            if not existing:
                cur.execute('''
                    INSERT INTO taxa (scientific_name, common_name, kingdom, phylum, class, ord, family, genus, 
                                      rank, source, source_id, image_url, thumbnail_url)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ''', (scientific_name, common_name, kingdom or 'Fungi', phylum, cls, order, family, genus,
                      rank, 'inat', str(taxon['id']), image_url, thumbnail_url))
                total_inserted += 1
            
            if total_processed >= limit:
                break
        
        conn.commit()
        params['page'] += 1
        time.sleep(1)
    
    cur.execute('UPDATE etl_runs SET status = %s, records_processed = %s, records_inserted = %s, completed_at = %s WHERE id = %s',
                ('completed', total_processed, total_inserted, datetime.now(), run_id))
    conn.commit()
    print(f'Completed: {total_processed} processed, {total_inserted} inserted')

except Exception as e:
    cur.execute('UPDATE etl_runs SET status = %s, error_message = %s, completed_at = %s WHERE id = %s',
                ('error', str(e), datetime.now(), run_id))
    conn.commit()
    print(f'Error: {e}')
    raise

finally:
    cur.execute('SELECT COUNT(*) FROM taxa')
    taxa_count = cur.fetchone()[0]
    print(f'Total taxa in database: {taxa_count}')
    conn.close()
"
''', timeout=600)
print(out or err)

print("\n[4] Cleaning up ETL container...")
run_ssh_cmd("docker rm -f mindex-etl-runner 2>/dev/null")

print("\n[5] Verifying data...")
out, err = run_ssh_cmd("curl -s http://localhost:8000/api/mindex/stats")
print(out)

print("\n" + "=" * 60)
print("  ETL COMPLETE")
print("=" * 60)
