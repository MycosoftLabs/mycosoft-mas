-- MINDEX Blob Storage Schema - Feb 5, 2026
-- Stores references to binary large objects (images, DNA sequences, research PDFs)
-- stored on NAS at /mnt/nas/mycosoft/mindex/

-- Create core schema if not exists
CREATE SCHEMA IF NOT EXISTS core;

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =============================================================================
-- BLOB STORAGE - References to files stored on NAS
-- =============================================================================

CREATE TABLE IF NOT EXISTS core.blobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    blob_type TEXT NOT NULL CHECK (blob_type IN ('image', 'dna_sequence', 'research_pdf', 'video', 'audio', 'document', 'data')),
    source TEXT NOT NULL,              -- 'inaturalist', 'gbif', 'genbank', 'pubmed', 'mycobank', 'local'
    source_id TEXT,                    -- External ID from source
    file_path TEXT NOT NULL,           -- NAS path relative to /mnt/nas/mycosoft/mindex/
    original_url TEXT,                 -- Original download URL
    file_name TEXT,                    -- Original filename
    file_size BIGINT,                  -- Size in bytes
    mime_type TEXT,                    -- MIME type (image/jpeg, application/pdf, etc.)
    checksum TEXT,                     -- SHA256 hash for integrity
    checksum_algorithm TEXT DEFAULT 'sha256',
    width INTEGER,                     -- For images/videos
    height INTEGER,                    -- For images/videos
    duration_seconds FLOAT,            -- For audio/video
    metadata JSONB DEFAULT '{}',       -- Additional metadata
    is_processed BOOLEAN DEFAULT FALSE,-- Has been processed (resized, indexed, etc.)
    processing_status TEXT,            -- 'pending', 'processing', 'completed', 'failed'
    processing_error TEXT,             -- Error message if failed
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(source, source_id, blob_type)
);

CREATE INDEX IF NOT EXISTS idx_blobs_type ON core.blobs(blob_type);
CREATE INDEX IF NOT EXISTS idx_blobs_source ON core.blobs(source);
CREATE INDEX IF NOT EXISTS idx_blobs_source_id ON core.blobs(source_id);
CREATE INDEX IF NOT EXISTS idx_blobs_processing_status ON core.blobs(processing_status);
CREATE INDEX IF NOT EXISTS idx_blobs_created_at ON core.blobs(created_at);

-- =============================================================================
-- SPECIES IMAGES - Link images to species/taxa
-- =============================================================================

CREATE TABLE IF NOT EXISTS core.species_images (
    id SERIAL PRIMARY KEY,
    taxon_id INTEGER,                  -- Reference to core.taxon if exists
    gbif_key INTEGER,                  -- GBIF taxon key
    inat_id INTEGER,                   -- iNaturalist taxon ID
    scientific_name TEXT,              -- Scientific name for fallback matching
    blob_id UUID NOT NULL REFERENCES core.blobs(id) ON DELETE CASCADE,
    is_primary BOOLEAN DEFAULT FALSE,  -- Primary/default image for species
    attribution TEXT,                  -- Photo attribution
    license TEXT,                      -- License code (CC-BY, CC0, etc.)
    license_url TEXT,                  -- License URL
    photographer TEXT,                 -- Photographer name
    observation_id TEXT,               -- Original observation ID
    observation_url TEXT,              -- Link to original observation
    quality_score FLOAT DEFAULT 0.5,   -- Quality score 0-1
    is_training_data BOOLEAN DEFAULT TRUE,  -- Suitable for ML training
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(blob_id)
);

CREATE INDEX IF NOT EXISTS idx_species_images_taxon ON core.species_images(taxon_id);
CREATE INDEX IF NOT EXISTS idx_species_images_gbif ON core.species_images(gbif_key);
CREATE INDEX IF NOT EXISTS idx_species_images_inat ON core.species_images(inat_id);
CREATE INDEX IF NOT EXISTS idx_species_images_name ON core.species_images(scientific_name);
CREATE INDEX IF NOT EXISTS idx_species_images_primary ON core.species_images(is_primary) WHERE is_primary = TRUE;

-- =============================================================================
-- DNA SEQUENCES - Link DNA sequences to species
-- =============================================================================

CREATE TABLE IF NOT EXISTS core.dna_sequences (
    id SERIAL PRIMARY KEY,
    taxon_id INTEGER,                  -- Reference to core.taxon if exists
    gbif_key INTEGER,                  -- GBIF taxon key
    scientific_name TEXT,              -- Scientific name for matching
    blob_id UUID REFERENCES core.blobs(id) ON DELETE SET NULL,  -- FASTA file blob
    accession TEXT NOT NULL,           -- GenBank/NCBI accession number
    gi_number TEXT,                    -- GenBank GI number (deprecated but useful)
    gene_region TEXT,                  -- 'ITS', 'ITS1', 'ITS2', '18S', '28S', 'LSU', 'SSU', 'RPB1', 'RPB2', 'TEF1', 'CO1', etc.
    sequence_length INTEGER,           -- Length in base pairs
    sequence_text TEXT,                -- Actual sequence (for small sequences)
    gc_content FLOAT,                  -- GC content percentage
    definition TEXT,                   -- Sequence definition/description
    organism TEXT,                     -- Organism name from GenBank
    strain TEXT,                       -- Strain/isolate name
    specimen_voucher TEXT,             -- Specimen voucher
    country TEXT,                      -- Collection country
    collection_date DATE,              -- Collection date
    pubmed_ids TEXT[],                 -- Related PubMed IDs
    source TEXT DEFAULT 'genbank',     -- 'genbank', 'bold', 'unite', 'local'
    source_url TEXT,                   -- Link to source
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(accession)
);

CREATE INDEX IF NOT EXISTS idx_dna_sequences_taxon ON core.dna_sequences(taxon_id);
CREATE INDEX IF NOT EXISTS idx_dna_sequences_gbif ON core.dna_sequences(gbif_key);
CREATE INDEX IF NOT EXISTS idx_dna_sequences_name ON core.dna_sequences(scientific_name);
CREATE INDEX IF NOT EXISTS idx_dna_sequences_gene ON core.dna_sequences(gene_region);
CREATE INDEX IF NOT EXISTS idx_dna_sequences_accession ON core.dna_sequences(accession);

-- =============================================================================
-- RESEARCH PAPERS - Fungal research documents
-- =============================================================================

CREATE TABLE IF NOT EXISTS core.research_papers (
    id SERIAL PRIMARY KEY,
    doi TEXT UNIQUE,                   -- Digital Object Identifier
    pmid TEXT,                         -- PubMed ID
    pmc_id TEXT,                       -- PubMed Central ID
    title TEXT NOT NULL,
    authors JSONB,                     -- [{name, affiliation, orcid}]
    journal TEXT,
    journal_abbrev TEXT,
    volume TEXT,
    issue TEXT,
    pages TEXT,
    year INTEGER,
    publication_date DATE,
    abstract TEXT,
    keywords TEXT[],
    mesh_terms TEXT[],                 -- MeSH terms
    blob_id UUID REFERENCES core.blobs(id) ON DELETE SET NULL,  -- PDF blob
    pdf_url TEXT,                      -- Direct PDF URL if available
    source_url TEXT,                   -- PubMed/journal URL
    related_taxa INTEGER[],            -- Array of taxon IDs
    related_species TEXT[],            -- Array of scientific names
    related_compounds TEXT[],          -- Array of compound names
    citation_count INTEGER DEFAULT 0,
    is_open_access BOOLEAN DEFAULT FALSE,
    license TEXT,
    language TEXT DEFAULT 'en',
    source TEXT DEFAULT 'pubmed',      -- 'pubmed', 'mycobank', 'scopus', 'local'
    metadata JSONB DEFAULT '{}',
    full_text TEXT,                    -- Full text if available
    full_text_indexed TSVECTOR,        -- Full text search index
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_research_papers_pmid ON core.research_papers(pmid);
CREATE INDEX IF NOT EXISTS idx_research_papers_year ON core.research_papers(year);
CREATE INDEX IF NOT EXISTS idx_research_papers_journal ON core.research_papers(journal);
CREATE INDEX IF NOT EXISTS idx_research_papers_species ON core.research_papers USING GIN(related_species);
CREATE INDEX IF NOT EXISTS idx_research_papers_compounds ON core.research_papers USING GIN(related_compounds);
CREATE INDEX IF NOT EXISTS idx_research_papers_fulltext ON core.research_papers USING GIN(full_text_indexed);

-- Trigger to update full text search index
CREATE OR REPLACE FUNCTION update_paper_fulltext()
RETURNS TRIGGER AS $$
BEGIN
    NEW.full_text_indexed := to_tsvector('english', 
        COALESCE(NEW.title, '') || ' ' || 
        COALESCE(NEW.abstract, '') || ' ' || 
        COALESCE(NEW.full_text, '') || ' ' ||
        COALESCE(array_to_string(NEW.keywords, ' '), '')
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_research_papers_fulltext ON core.research_papers;
CREATE TRIGGER trg_research_papers_fulltext
    BEFORE INSERT OR UPDATE OF title, abstract, full_text, keywords
    ON core.research_papers
    FOR EACH ROW
    EXECUTE FUNCTION update_paper_fulltext();

-- =============================================================================
-- CHEMICAL COMPOUNDS - Fungal metabolites and compounds
-- =============================================================================

CREATE TABLE IF NOT EXISTS core.compounds (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,                -- Common/preferred name
    iupac_name TEXT,                   -- IUPAC systematic name
    cas_number TEXT UNIQUE,            -- CAS Registry Number
    pubchem_cid INTEGER,               -- PubChem Compound ID
    chembl_id TEXT,                    -- ChEMBL ID
    inchi TEXT,                        -- InChI string
    inchi_key TEXT,                    -- InChI Key
    smiles TEXT,                       -- SMILES notation
    molecular_formula TEXT,
    molecular_weight FLOAT,
    exact_mass FLOAT,
    xlogp FLOAT,                       -- Partition coefficient
    compound_class TEXT,               -- 'alkaloid', 'terpene', 'polyketide', 'peptide', etc.
    bioactivity JSONB,                 -- [{activity, target, value, unit}]
    toxicity_class TEXT,               -- 'non-toxic', 'low', 'moderate', 'high', 'lethal'
    producing_species TEXT[],          -- Array of scientific names
    producing_taxa INTEGER[],          -- Array of taxon IDs
    structure_blob_id UUID REFERENCES core.blobs(id),  -- 2D/3D structure image
    source TEXT DEFAULT 'pubchem',     -- 'pubchem', 'chembl', 'local'
    source_url TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_compounds_name ON core.compounds(name);
CREATE INDEX IF NOT EXISTS idx_compounds_cas ON core.compounds(cas_number);
CREATE INDEX IF NOT EXISTS idx_compounds_pubchem ON core.compounds(pubchem_cid);
CREATE INDEX IF NOT EXISTS idx_compounds_class ON core.compounds(compound_class);
CREATE INDEX IF NOT EXISTS idx_compounds_species ON core.compounds USING GIN(producing_species);

-- =============================================================================
-- BLOB DOWNLOAD QUEUE - Track pending downloads
-- =============================================================================

CREATE TABLE IF NOT EXISTS core.blob_download_queue (
    id SERIAL PRIMARY KEY,
    url TEXT NOT NULL,
    target_path TEXT NOT NULL,
    blob_type TEXT NOT NULL,
    source TEXT NOT NULL,
    source_id TEXT,
    priority INTEGER DEFAULT 0,        -- Higher = more urgent
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'downloading', 'completed', 'failed', 'cancelled')),
    attempts INTEGER DEFAULT 0,
    max_attempts INTEGER DEFAULT 3,
    last_error TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    metadata JSONB DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_blob_queue_status ON core.blob_download_queue(status);
CREATE INDEX IF NOT EXISTS idx_blob_queue_priority ON core.blob_download_queue(priority DESC, created_at);

-- =============================================================================
-- HELPER VIEWS
-- =============================================================================

-- View: Species with their primary images
CREATE OR REPLACE VIEW core.species_with_images AS
SELECT DISTINCT ON (si.scientific_name)
    si.scientific_name,
    si.taxon_id,
    si.gbif_key,
    si.inat_id,
    b.file_path AS image_path,
    b.original_url AS image_url,
    si.attribution,
    si.license,
    si.quality_score
FROM core.species_images si
JOIN core.blobs b ON si.blob_id = b.id
ORDER BY si.scientific_name, si.is_primary DESC, si.quality_score DESC;

-- View: Species with DNA sequences
CREATE OR REPLACE VIEW core.species_with_sequences AS
SELECT 
    ds.scientific_name,
    ds.taxon_id,
    ds.gbif_key,
    COUNT(*) AS sequence_count,
    array_agg(DISTINCT ds.gene_region) FILTER (WHERE ds.gene_region IS NOT NULL) AS gene_regions,
    array_agg(ds.accession) AS accessions
FROM core.dna_sequences ds
GROUP BY ds.scientific_name, ds.taxon_id, ds.gbif_key;

-- View: Species with research papers
CREATE OR REPLACE VIEW core.species_with_research AS
SELECT 
    species_name,
    COUNT(*) AS paper_count,
    array_agg(rp.id) AS paper_ids,
    array_agg(rp.title) AS paper_titles
FROM core.research_papers rp,
     unnest(rp.related_species) AS species_name
GROUP BY species_name;

-- =============================================================================
-- GRANTS
-- =============================================================================

-- Grant access to application role if exists
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'mycosoft_app') THEN
        GRANT USAGE ON SCHEMA core TO mycosoft_app;
        GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA core TO mycosoft_app;
        GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA core TO mycosoft_app;
    END IF;
END
$$;

-- Comments
COMMENT ON TABLE core.blobs IS 'References to binary large objects stored on NAS';
COMMENT ON TABLE core.species_images IS 'Images linked to fungal species/taxa';
COMMENT ON TABLE core.dna_sequences IS 'DNA/RNA sequences from GenBank and other sources';
COMMENT ON TABLE core.research_papers IS 'Research papers and publications about fungi';
COMMENT ON TABLE core.compounds IS 'Chemical compounds and metabolites from fungi';
COMMENT ON TABLE core.blob_download_queue IS 'Queue for pending blob downloads';
