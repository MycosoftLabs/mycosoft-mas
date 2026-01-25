#!/usr/bin/env python3
"""Run initial ETL to populate MINDEX with fungi data from iNaturalist"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import paramiko
import time

VM_IP = "192.168.0.187"
VM_USER = "mycosoft"
VM_PASSWORD = "REDACTED_VM_SSH_PASSWORD"

# Python script to run on VM for ETL
ETL_SCRIPT = '''#!/usr/bin/env python3
"""MINDEX ETL - Scrape fungi from iNaturalist API"""
import requests
import psycopg2
import time
from datetime import datetime

DB_CONFIG = {
    "host": "localhost",
    "port": 5434,
    "user": "mindex",
    "password": "mindex",
    "database": "mindex"
}

INAT_API = "https://api.inaturalist.org/v1"

def get_connection():
    return psycopg2.connect(**DB_CONFIG)

def log_etl_run(conn, pipeline, status, records_processed=0, records_inserted=0, error_message=None):
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO etl_runs (pipeline, status, records_processed, records_inserted, error_message, completed_at)
        VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING id
    """, (pipeline, status, records_processed, records_inserted, error_message, datetime.now() if status != 'running' else None))
    conn.commit()
    return cur.fetchone()[0]

def update_etl_run(conn, run_id, status, records_processed, records_inserted, error_message=None):
    cur = conn.cursor()
    cur.execute("""
        UPDATE etl_runs SET status = %s, records_processed = %s, records_inserted = %s, 
               error_message = %s, completed_at = %s WHERE id = %s
    """, (status, records_processed, records_inserted, error_message, datetime.now(), run_id))
    conn.commit()

def scrape_inat_fungi(limit=500):
    """Scrape fungi taxa from iNaturalist"""
    conn = get_connection()
    run_id = log_etl_run(conn, 'iNaturalist', 'running')
    
    try:
        print(f"Starting iNaturalist fungi scrape (limit: {limit})...")
        
        # Fetch fungi taxa
        url = f"{INAT_API}/taxa"
        params = {
            "taxon_id": 47170,  # Fungi kingdom
            "rank": "species,subspecies,variety",
            "per_page": 200,
            "page": 1,
            "order": "desc",
            "order_by": "observations_count"
        }
        
        total_processed = 0
        total_inserted = 0
        cur = conn.cursor()
        
        while total_processed < limit:
            print(f"  Fetching page {params['page']}...")
            response = requests.get(url, params=params, timeout=30)
            
            if response.status_code != 200:
                print(f"  API error: {response.status_code}")
                break
            
            data = response.json()
            results = data.get('results', [])
            
            if not results:
                print("  No more results")
                break
            
            for taxon in results:
                total_processed += 1
                
                # Extract data
                scientific_name = taxon.get('name', '')
                common_name = taxon.get('preferred_common_name', '')
                rank = taxon.get('rank', '')
                
                # Parse ancestry
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
                
                # Get image
                photo = taxon.get('default_photo', {}) or {}
                image_url = photo.get('medium_url', '')
                thumbnail_url = photo.get('square_url', '')
                
                # Check if exists
                cur.execute("SELECT id FROM taxa WHERE source = %s AND source_id = %s", ('inat', str(taxon['id'])))
                existing = cur.fetchone()
                
                if not existing:
                    cur.execute("""
                        INSERT INTO taxa (scientific_name, common_name, kingdom, phylum, class, ord, family, genus, 
                                          rank, source, source_id, image_url, thumbnail_url)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (scientific_name, common_name, kingdom or 'Fungi', phylum, cls, order, family, genus,
                          rank, 'inat', str(taxon['id']), image_url, thumbnail_url))
                    total_inserted += 1
                
                if total_processed >= limit:
                    break
            
            conn.commit()
            params['page'] += 1
            time.sleep(1)  # Rate limiting
        
        update_etl_run(conn, run_id, 'completed', total_processed, total_inserted)
        print(f"Completed: {total_processed} processed, {total_inserted} inserted")
        
    except Exception as e:
        update_etl_run(conn, run_id, 'error', total_processed, total_inserted, str(e))
        print(f"Error: {e}")
        raise
    finally:
        conn.close()

def scrape_inat_observations(limit=500):
    """Scrape fungi observations from iNaturalist"""
    conn = get_connection()
    run_id = log_etl_run(conn, 'iNaturalist-observations', 'running')
    
    try:
        print(f"Starting iNaturalist observations scrape (limit: {limit})...")
        
        url = f"{INAT_API}/observations"
        params = {
            "iconic_taxa": "Fungi",
            "quality_grade": "research",
            "per_page": 200,
            "page": 1,
            "order": "desc",
            "order_by": "created_at"
        }
        
        total_processed = 0
        total_inserted = 0
        cur = conn.cursor()
        
        while total_processed < limit:
            print(f"  Fetching page {params['page']}...")
            response = requests.get(url, params=params, timeout=30)
            
            if response.status_code != 200:
                print(f"  API error: {response.status_code}")
                break
            
            data = response.json()
            results = data.get('results', [])
            
            if not results:
                print("  No more results")
                break
            
            for obs in results:
                total_processed += 1
                
                # Get taxon
                taxon = obs.get('taxon', {}) or {}
                taxon_id = taxon.get('id')
                
                # Look up taxon in our DB
                cur.execute("SELECT id FROM taxa WHERE source = %s AND source_id = %s", ('inat', str(taxon_id)))
                local_taxon = cur.fetchone()
                local_taxon_id = local_taxon[0] if local_taxon else None
                
                # Extract observation data
                observed_on = obs.get('observed_on')
                lat = obs.get('geojson', {}).get('coordinates', [None, None])[1] if obs.get('geojson') else None
                lng = obs.get('geojson', {}).get('coordinates', [None, None])[0] if obs.get('geojson') else None
                place_name = obs.get('place_guess', '')
                observer = obs.get('user', {}).get('login', '')
                quality = obs.get('quality_grade', '')
                
                # Check if exists
                cur.execute("SELECT id FROM observations WHERE source = %s AND source_id = %s", ('inat', str(obs['id'])))
                existing = cur.fetchone()
                
                if not existing and (lat or lng or place_name):
                    cur.execute("""
                        INSERT INTO observations (taxon_id, source, source_id, observer_name, observed_on,
                                                  latitude, longitude, place_name, quality_grade)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (local_taxon_id, 'inat', str(obs['id']), observer, observed_on, lat, lng, place_name, quality))
                    total_inserted += 1
                
                if total_processed >= limit:
                    break
            
            conn.commit()
            params['page'] += 1
            time.sleep(1)
        
        update_etl_run(conn, run_id, 'completed', total_processed, total_inserted)
        print(f"Completed: {total_processed} processed, {total_inserted} inserted")
        
    except Exception as e:
        update_etl_run(conn, run_id, 'error', total_processed, total_inserted, str(e))
        print(f"Error: {e}")
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    print("=" * 50)
    print("  MINDEX ETL - Initial Data Population")
    print("=" * 50)
    
    # Scrape taxa first
    scrape_inat_fungi(limit=1000)
    
    # Then observations
    scrape_inat_observations(limit=500)
    
    # Show stats
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM taxa")
    taxa_count = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM observations")
    obs_count = cur.fetchone()[0]
    conn.close()
    
    print(f"\\nFinal counts:")
    print(f"  Taxa: {taxa_count}")
    print(f"  Observations: {obs_count}")
'''

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
print("  MINDEX ETL - Initial Population")
print("=" * 60)

print("\n[1] Installing required Python packages on VM...")
out, err = run_ssh_cmd("pip3 install --user requests psycopg2-binary 2>&1 | tail -3")
print(out or "Done")

print("\n[2] Writing ETL script to VM...")
import base64
script_b64 = base64.b64encode(ETL_SCRIPT.encode()).decode()
run_ssh_cmd(f'echo "{script_b64}" | base64 -d > /home/mycosoft/mindex_etl.py && chmod +x /home/mycosoft/mindex_etl.py')
print("ETL script written")

print("\n[3] Running ETL script (this may take a few minutes)...")
print("    Scraping fungi taxa and observations from iNaturalist...\n")
out, err = run_ssh_cmd("cd /home/mycosoft && python3 mindex_etl.py 2>&1", timeout=600)
print(out or err)

print("\n[4] Verifying data...")
out, err = run_ssh_cmd("curl -s http://localhost:8000/api/mindex/stats")
print(f"Stats: {out}")

print("\n" + "=" * 60)
print("  ETL COMPLETE")
print("=" * 60)
