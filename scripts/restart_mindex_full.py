#!/usr/bin/env python3
"""Full MINDEX restart with schema creation"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import paramiko
import time
import base64

VM_IP = "192.168.0.187"
VM_USER = "mycosoft"
VM_PASSWORD = "Mushroom1!Mushroom1!"

# MINDEX Database Schema
MINDEX_SCHEMA = """
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE TABLE IF NOT EXISTS taxa (
    id SERIAL PRIMARY KEY,
    scientific_name VARCHAR(255) NOT NULL,
    common_name VARCHAR(255),
    kingdom VARCHAR(100) DEFAULT 'Fungi',
    phylum VARCHAR(100),
    class VARCHAR(100),
    "order" VARCHAR(100),
    family VARCHAR(100),
    genus VARCHAR(100),
    species VARCHAR(100),
    rank VARCHAR(50),
    source VARCHAR(50) NOT NULL,
    source_id VARCHAR(100),
    parent_id INTEGER,
    image_url TEXT,
    thumbnail_url TEXT,
    description TEXT,
    edibility VARCHAR(50),
    toxicity VARCHAR(50),
    habitat TEXT,
    distribution TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_taxa_scientific_name ON taxa(scientific_name);
CREATE INDEX IF NOT EXISTS idx_taxa_source ON taxa(source);
CREATE INDEX IF NOT EXISTS idx_taxa_genus ON taxa(genus);

CREATE TABLE IF NOT EXISTS external_ids (
    id SERIAL PRIMARY KEY,
    taxon_id INTEGER NOT NULL REFERENCES taxa(id) ON DELETE CASCADE,
    source VARCHAR(50) NOT NULL,
    external_id VARCHAR(100) NOT NULL,
    url TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(taxon_id, source)
);

CREATE TABLE IF NOT EXISTS observations (
    id SERIAL PRIMARY KEY,
    taxon_id INTEGER REFERENCES taxa(id),
    source VARCHAR(50) NOT NULL,
    source_id VARCHAR(100),
    observer_name VARCHAR(255),
    observed_on DATE,
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    location_accuracy_m DOUBLE PRECISION,
    place_name TEXT,
    country VARCHAR(100),
    state_province VARCHAR(100),
    image_urls TEXT[],
    description TEXT,
    quality_grade VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB DEFAULT '{}',
    geom geometry(Point, 4326)
);

CREATE INDEX IF NOT EXISTS idx_observations_taxon_id ON observations(taxon_id);
CREATE INDEX IF NOT EXISTS idx_observations_geom ON observations USING gist(geom);

CREATE TABLE IF NOT EXISTS synonyms (
    id SERIAL PRIMARY KEY,
    taxon_id INTEGER NOT NULL REFERENCES taxa(id) ON DELETE CASCADE,
    synonym_name VARCHAR(255) NOT NULL,
    synonym_type VARCHAR(50),
    source VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS traits (
    id SERIAL PRIMARY KEY,
    taxon_id INTEGER NOT NULL REFERENCES taxa(id) ON DELETE CASCADE,
    trait_name VARCHAR(100) NOT NULL,
    trait_value TEXT,
    trait_unit VARCHAR(50),
    source VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS genomes (
    id SERIAL PRIMARY KEY,
    taxon_id INTEGER NOT NULL REFERENCES taxa(id) ON DELETE CASCADE,
    sequence_type VARCHAR(50),
    sequence TEXT,
    accession_number VARCHAR(100),
    source VARCHAR(50),
    source_url TEXT,
    length INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS compounds (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    cas_number VARCHAR(50),
    formula VARCHAR(100),
    molecular_weight DOUBLE PRECISION,
    smiles TEXT,
    inchi TEXT,
    description TEXT,
    bioactivity TEXT,
    source VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS taxa_compounds (
    id SERIAL PRIMARY KEY,
    taxon_id INTEGER NOT NULL REFERENCES taxa(id) ON DELETE CASCADE,
    compound_id INTEGER NOT NULL REFERENCES compounds(id) ON DELETE CASCADE,
    concentration TEXT,
    tissue VARCHAR(100),
    source VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(taxon_id, compound_id)
);

CREATE TABLE IF NOT EXISTS etl_runs (
    id SERIAL PRIMARY KEY,
    pipeline VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL,
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    records_processed INTEGER DEFAULT 0,
    records_inserted INTEGER DEFAULT 0,
    records_updated INTEGER DEFAULT 0,
    error_message TEXT,
    metadata JSONB DEFAULT '{}'
);

GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO mindex;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO mindex;
"""

def run_ssh_cmd(cmd, timeout=120):
    """Run command via SSH"""
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
print("  FULL MINDEX RESTART")
print("=" * 60)

print("\n[1] Stop all mindex containers...")
out, err = run_ssh_cmd("docker stop mindex-api mindex-postgres mindex-postgres-data 2>/dev/null; docker rm mindex-api mindex-postgres 2>/dev/null")
print("Stopped")

print("\n[2] Start mindex-postgres-data...")
out, err = run_ssh_cmd("docker start mindex-postgres-data 2>&1")
print(out or err)

print("\n[3] Wait 15s for postgres...")
time.sleep(15)

print("\n[4] Write schema to VM...")
schema_b64 = base64.b64encode(MINDEX_SCHEMA.encode()).decode()
run_ssh_cmd(f'echo "{schema_b64}" | base64 -d > /tmp/mindex_schema.sql')
print("Done")

print("\n[5] Execute schema...")
out, err = run_ssh_cmd('docker exec mindex-postgres-data psql -U mindex -d mindex -f /tmp/mindex_schema.sql 2>&1')
# Print only important lines
for line in (out or "").split('\n'):
    if 'CREATE' in line or 'ERROR' in line or 'GRANT' in line:
        print(f"  {line}")
if err:
    print(f"  ERR: {err[:200]}")

print("\n[6] Verify tables...")
out, err = run_ssh_cmd("docker exec mindex-postgres-data psql -U mindex -d mindex -c '\\dt'")
print(out)

print("\n[7] Start mindex-api...")
out, err = run_ssh_cmd("""
docker run -d --name mindex-api \
  --add-host=host.docker.internal:host-gateway \
  --restart unless-stopped \
  -p 8000:8000 \
  -e MINDEX_DB_HOST=host.docker.internal \
  -e MINDEX_DB_PORT=5434 \
  -e MINDEX_DB_USER=mindex \
  -e MINDEX_DB_PASSWORD=mindex \
  -e MINDEX_DB_NAME=mindex \
  -e API_PREFIX=/api/mindex \
  -e 'API_KEYS=["local-dev-key", "sandbox-key"]' \
  mindex-services-mindex-api:latest 2>&1
""")
print(out or err)

print("\n[8] Wait 15s for API...")
time.sleep(15)

print("\n[9] Test API health...")
out, err = run_ssh_cmd("curl -s http://localhost:8000/api/mindex/health")
print(f"  Health: {out}")

print("\n[10] Test API stats...")
out, err = run_ssh_cmd("curl -s http://localhost:8000/api/mindex/stats")
print(f"  Stats: {out}")

print("\n[11] Check container status...")
out, err = run_ssh_cmd("docker ps --filter name=mindex --format '{{.Names}} {{.Status}}'")
print(out)

print("\n" + "=" * 60)
print("  MINDEX READY")
print("=" * 60)
