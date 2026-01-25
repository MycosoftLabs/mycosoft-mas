#!/usr/bin/env python3
"""Create MINDEX schema by piping SQL directly"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import paramiko
import time

VM_IP = "192.168.0.187"
VM_USER = "mycosoft"
VM_PASSWORD = "REDACTED_VM_SSH_PASSWORD"

def run_ssh_cmd(cmd, timeout=120):
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

print("Creating MINDEX schema tables one by one...")

# Execute each table creation separately
tables = [
    ("taxa", """
CREATE TABLE IF NOT EXISTS taxa (
    id SERIAL PRIMARY KEY,
    scientific_name VARCHAR(255) NOT NULL,
    common_name VARCHAR(255),
    kingdom VARCHAR(100) DEFAULT 'Fungi',
    phylum VARCHAR(100),
    class VARCHAR(100),
    ord VARCHAR(100),
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
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'
);
"""),
    ("observations", """
CREATE TABLE IF NOT EXISTS observations (
    id SERIAL PRIMARY KEY,
    taxon_id INTEGER,
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
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'
);
"""),
    ("external_ids", """
CREATE TABLE IF NOT EXISTS external_ids (
    id SERIAL PRIMARY KEY,
    taxon_id INTEGER NOT NULL,
    source VARCHAR(50) NOT NULL,
    external_id VARCHAR(100) NOT NULL,
    url TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);
"""),
    ("synonyms", """
CREATE TABLE IF NOT EXISTS synonyms (
    id SERIAL PRIMARY KEY,
    taxon_id INTEGER NOT NULL,
    synonym_name VARCHAR(255) NOT NULL,
    synonym_type VARCHAR(50),
    source VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW()
);
"""),
    ("traits", """
CREATE TABLE IF NOT EXISTS traits (
    id SERIAL PRIMARY KEY,
    taxon_id INTEGER NOT NULL,
    trait_name VARCHAR(100) NOT NULL,
    trait_value TEXT,
    trait_unit VARCHAR(50),
    source VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'
);
"""),
    ("genomes", """
CREATE TABLE IF NOT EXISTS genomes (
    id SERIAL PRIMARY KEY,
    taxon_id INTEGER NOT NULL,
    sequence_type VARCHAR(50),
    sequence TEXT,
    accession_number VARCHAR(100),
    source VARCHAR(50),
    source_url TEXT,
    length INTEGER,
    created_at TIMESTAMP DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'
);
"""),
    ("compounds", """
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
    created_at TIMESTAMP DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'
);
"""),
    ("etl_runs", """
CREATE TABLE IF NOT EXISTS etl_runs (
    id SERIAL PRIMARY KEY,
    pipeline VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL,
    started_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP,
    records_processed INTEGER DEFAULT 0,
    records_inserted INTEGER DEFAULT 0,
    records_updated INTEGER DEFAULT 0,
    error_message TEXT,
    metadata JSONB DEFAULT '{}'
);
"""),
]

for name, sql in tables:
    # Clean the SQL to make it single line friendly
    clean_sql = sql.replace('\n', ' ').replace("'", "'\\''")
    cmd = f"docker exec mindex-postgres-data psql -U mindex -d mindex -c \"{clean_sql}\" 2>&1"
    out, err = run_ssh_cmd(cmd)
    status = "OK" if out and "CREATE TABLE" in out else "EXISTS" if out and "already exists" in (out or "") else "FAIL"
    print(f"  [{status}] {name}: {(out or err or '')[:50]}")

print("\nCreating indexes...")
indexes = [
    "CREATE INDEX IF NOT EXISTS idx_taxa_scientific_name ON taxa(scientific_name);",
    "CREATE INDEX IF NOT EXISTS idx_taxa_source ON taxa(source);",
    "CREATE INDEX IF NOT EXISTS idx_observations_taxon_id ON observations(taxon_id);",
]
for idx in indexes:
    out, err = run_ssh_cmd(f'docker exec mindex-postgres-data psql -U mindex -d mindex -c "{idx}" 2>&1')
    print(f"  {(out or err)[:60]}")

print("\nVerifying tables...")
out, err = run_ssh_cmd("docker exec mindex-postgres-data psql -U mindex -d mindex -c '\\dt'")
print(out)

print("\nTesting API stats...")
out, err = run_ssh_cmd("curl -s http://localhost:8000/api/mindex/stats 2>&1")
print(out)
