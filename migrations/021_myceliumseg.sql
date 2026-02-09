-- MyceliumSeg dataset and validation schema - Feb 6, 2026
-- Plan: docs/MYCELIUMSEG_INTEGRATION_PLAN_FEB06_2026.md

CREATE TABLE IF NOT EXISTS core.myceliumseg_images (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    external_id TEXT NOT NULL UNIQUE,
    species TEXT NOT NULL CHECK (species IN ('GL', 'GS', 'PO', 'TS')),
    growth_stage TEXT NOT NULL CHECK (growth_stage IN (
        'activation_germination', 'primary_expansion', 'network_building', 'maturation'
    )),
    medium TEXT NOT NULL CHECK (medium IN ('MYG', 'PDA')),
    temperature_c SMALLINT NOT NULL CHECK (temperature_c IN (15, 25)),
    split TEXT NOT NULL,
    blob_id UUID REFERENCES core.blobs(id) ON DELETE SET NULL,
    asset_path TEXT,
    width INTEGER,
    height INTEGER,
    dataset_version TEXT DEFAULT 'myceliumseg-v1.0',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_myceliumseg_images_species_medium_temp ON core.myceliumseg_images(species, medium, temperature_c);
CREATE INDEX IF NOT EXISTS idx_myceliumseg_images_growth_stage ON core.myceliumseg_images(growth_stage);
CREATE INDEX IF NOT EXISTS idx_myceliumseg_images_split ON core.myceliumseg_images(split);
CREATE INDEX IF NOT EXISTS idx_myceliumseg_images_external_id ON core.myceliumseg_images(external_id);

CREATE TABLE IF NOT EXISTS core.myceliumseg_masks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    image_id UUID NOT NULL REFERENCES core.myceliumseg_images(id) ON DELETE CASCADE,
    blob_id UUID REFERENCES core.blobs(id) ON DELETE SET NULL,
    asset_path TEXT,
    mask_version TEXT DEFAULT 'v1',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(image_id, mask_version)
);

CREATE INDEX IF NOT EXISTS idx_myceliumseg_masks_image_id ON core.myceliumseg_masks(image_id);

CREATE TABLE IF NOT EXISTS core.myceliumseg_phenotypes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    image_id UUID NOT NULL REFERENCES core.myceliumseg_images(id) ON DELETE CASCADE,
    density_distribution TEXT CHECK (density_distribution IN ('uniform', 'concentric', 'centripetal', 'peripheral', 'heterogeneous')),
    edge_irregularity BOOLEAN,
    pigmentation BOOLEAN,
    wrinkling BOOLEAN,
    rhizomorph BOOLEAN,
    spiral_stratification BOOLEAN,
    internal_concavity BOOLEAN,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(image_id)
);

CREATE INDEX IF NOT EXISTS idx_myceliumseg_phenotypes_image_id ON core.myceliumseg_phenotypes(image_id);

CREATE TABLE IF NOT EXISTS core.simulator_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    simulator_version TEXT NOT NULL,
    seed BIGINT,
    parameters JSONB,
    environment JSONB,
    output_mask_blob_id UUID REFERENCES core.blobs(id) ON DELETE SET NULL,
    output_mask_path TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_simulator_runs_version ON core.simulator_runs(simulator_version);
CREATE INDEX IF NOT EXISTS idx_simulator_runs_created_at ON core.simulator_runs(created_at);

CREATE TABLE IF NOT EXISTS core.validation_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    status TEXT NOT NULL DEFAULT 'queued' CHECK (status IN ('queued', 'running', 'completed', 'failed')),
    dataset_slice JSONB NOT NULL,
    simulator_run_id UUID REFERENCES core.simulator_runs(id) ON DELETE SET NULL,
    model_ref TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    error_message TEXT
);

CREATE INDEX IF NOT EXISTS idx_validation_jobs_status ON core.validation_jobs(status);
CREATE INDEX IF NOT EXISTS idx_validation_jobs_created_at ON core.validation_jobs(created_at);

CREATE TABLE IF NOT EXISTS core.validation_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    validation_job_id UUID NOT NULL REFERENCES core.validation_jobs(id) ON DELETE CASCADE,
    image_id UUID NOT NULL REFERENCES core.myceliumseg_images(id) ON DELETE CASCADE,
    sample_metrics JSONB NOT NULL,
    overlay_blob_id UUID REFERENCES core.blobs(id) ON DELETE SET NULL,
    overlay_path TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_validation_results_job_id ON core.validation_results(validation_job_id);
CREATE INDEX IF NOT EXISTS idx_validation_results_image_id ON core.validation_results(image_id);
