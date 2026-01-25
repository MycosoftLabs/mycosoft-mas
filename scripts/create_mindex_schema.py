#!/usr/bin/env python3
"""Create MINDEX database schema"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import paramiko

VM_IP = "192.168.0.187"
VM_USER = "mycosoft"
VM_PASSWORD = "Mushroom1!Mushroom1!"

# MINDEX Database Schema
MINDEX_SCHEMA = """
-- MINDEX Database Schema
-- Mycosoft Data Index for Taxonomy, Observations, and Biological Data

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Taxa table (core taxonomy)
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
    source VARCHAR(50) NOT NULL,  -- 'inat', 'gbif', 'index_fungorum', 'manual'
    source_id VARCHAR(100),
    parent_id INTEGER REFERENCES taxa(id),
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

-- Create indexes for taxa
CREATE INDEX IF NOT EXISTS idx_taxa_scientific_name ON taxa(scientific_name);
CREATE INDEX IF NOT EXISTS idx_taxa_common_name ON taxa(common_name);
CREATE INDEX IF NOT EXISTS idx_taxa_source ON taxa(source);
CREATE INDEX IF NOT EXISTS idx_taxa_source_id ON taxa(source, source_id);
CREATE INDEX IF NOT EXISTS idx_taxa_genus ON taxa(genus);
CREATE INDEX IF NOT EXISTS idx_taxa_family ON taxa(family);
CREATE INDEX IF NOT EXISTS idx_taxa_scientific_name_trgm ON taxa USING gin(scientific_name gin_trgm_ops);

-- External IDs (links to other databases)
CREATE TABLE IF NOT EXISTS external_ids (
    id SERIAL PRIMARY KEY,
    taxon_id INTEGER NOT NULL REFERENCES taxa(id) ON DELETE CASCADE,
    source VARCHAR(50) NOT NULL,  -- 'gbif', 'inat', 'ncbi', 'index_fungorum', 'mycobank'
    external_id VARCHAR(100) NOT NULL,
    url TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(taxon_id, source)
);

-- Observations (field sightings)
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

-- Create spatial and other indexes for observations
CREATE INDEX IF NOT EXISTS idx_observations_taxon_id ON observations(taxon_id);
CREATE INDEX IF NOT EXISTS idx_observations_source ON observations(source);
CREATE INDEX IF NOT EXISTS idx_observations_observed_on ON observations(observed_on);
CREATE INDEX IF NOT EXISTS idx_observations_geom ON observations USING gist(geom);
CREATE INDEX IF NOT EXISTS idx_observations_country ON observations(country);

-- Synonyms (alternative names)
CREATE TABLE IF NOT EXISTS synonyms (
    id SERIAL PRIMARY KEY,
    taxon_id INTEGER NOT NULL REFERENCES taxa(id) ON DELETE CASCADE,
    synonym_name VARCHAR(255) NOT NULL,
    synonym_type VARCHAR(50),  -- 'homotypic', 'heterotypic', 'basionym'
    source VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_synonyms_taxon_id ON synonyms(taxon_id);
CREATE INDEX IF NOT EXISTS idx_synonyms_name ON synonyms(synonym_name);

-- Traits (biological characteristics)
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

CREATE INDEX IF NOT EXISTS idx_traits_taxon_id ON traits(taxon_id);
CREATE INDEX IF NOT EXISTS idx_traits_name ON traits(trait_name);

-- Genomes (DNA/sequence data)
CREATE TABLE IF NOT EXISTS genomes (
    id SERIAL PRIMARY KEY,
    taxon_id INTEGER NOT NULL REFERENCES taxa(id) ON DELETE CASCADE,
    sequence_type VARCHAR(50),  -- 'ITS', 'LSU', 'SSU', 'whole_genome'
    sequence TEXT,
    accession_number VARCHAR(100),
    source VARCHAR(50),
    source_url TEXT,
    length INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_genomes_taxon_id ON genomes(taxon_id);
CREATE INDEX IF NOT EXISTS idx_genomes_accession ON genomes(accession_number);

-- Compounds (bioactive chemicals)
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

CREATE INDEX IF NOT EXISTS idx_compounds_name ON compounds(name);
CREATE INDEX IF NOT EXISTS idx_compounds_cas ON compounds(cas_number);

-- Taxa-Compounds junction
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

-- ETL tracking
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

CREATE INDEX IF NOT EXISTS idx_etl_runs_pipeline ON etl_runs(pipeline);
CREATE INDEX IF NOT EXISTS idx_etl_runs_status ON etl_runs(status);

-- Create updated_at trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply trigger to taxa
DROP TRIGGER IF EXISTS update_taxa_updated_at ON taxa;
CREATE TRIGGER update_taxa_updated_at
    BEFORE UPDATE ON taxa
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Apply trigger to observations
DROP TRIGGER IF EXISTS update_observations_updated_at ON observations;
CREATE TRIGGER update_observations_updated_at
    BEFORE UPDATE ON observations
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Grant permissions
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO mindex;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO mindex;

-- Success message
SELECT 'MINDEX schema created successfully' as status;
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
print("  CREATE MINDEX DATABASE SCHEMA")
print("=" * 60)

print("\n[1] Writing schema to file on VM...")
import base64
schema_b64 = base64.b64encode(MINDEX_SCHEMA.encode()).decode()
out, err = run_ssh_cmd(f'echo "{schema_b64}" | base64 -d > /tmp/mindex_schema.sql')
print("Schema file written")

print("\n[2] Executing schema on mindex-postgres-data...")
out, err = run_ssh_cmd('docker exec -i mindex-postgres-data psql -U mindex -d mindex -f /tmp/mindex_schema.sql 2>&1')
print(out or err)

print("\n[3] Verify tables created...")
out, err = run_ssh_cmd("docker exec mindex-postgres-data psql -U mindex -d mindex -c '\\dt'")
print(out)

print("\n[4] Check table counts...")
out, err = run_ssh_cmd("""
docker exec mindex-postgres-data psql -U mindex -d mindex -c "
SELECT 
    (SELECT COUNT(*) FROM taxa) as taxa,
    (SELECT COUNT(*) FROM observations) as observations,
    (SELECT COUNT(*) FROM compounds) as compounds;
"
""")
print(out)

print("\n[5] Test MINDEX API stats again...")
out, err = run_ssh_cmd("curl -s http://localhost:8000/api/mindex/stats")
print(out)

print("\n" + "=" * 60)
print("  SCHEMA CREATED")
print("=" * 60)
