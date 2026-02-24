# Petri Simulation MINDEX Schema

**Date:** Feb 20, 2026  
**Status:** Schema definition for MINDEX persistence of Petri simulation outcomes

## Overview

Schema for durable storage of Petri Dish simulation sessions, time-series metrics, calibration results, and experiment outcomes. Enables retrieval, analytics, and NLM learning workflows.

## Tables

### petri_simulation_sessions

Stores simulation session metadata.

```sql
CREATE TABLE IF NOT EXISTS petri_simulation_sessions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id VARCHAR(64) UNIQUE NOT NULL,
  width INT NOT NULL,
  height INT NOT NULL,
  agar_type VARCHAR(64),
  species_ids TEXT[],
  contaminant_ids TEXT[],
  virtual_hours INT DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  metadata JSONB
);
```

### petri_simulation_metrics

Time-series metrics per session (sample points).

```sql
CREATE TABLE IF NOT EXISTS petri_simulation_metrics (
  id BIGSERIAL PRIMARY KEY,
  session_id VARCHAR(64) NOT NULL REFERENCES petri_simulation_sessions(session_id),
  virtual_hour INT NOT NULL,
  sample_count INT,
  contaminant_count INT,
  total_branches INT,
  avg_nutrient FLOAT,
  compound_means JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_petri_metrics_session ON petri_simulation_metrics(session_id);
```

### petri_calibration_results

Calibration job results for species parameter tuning.

```sql
CREATE TABLE IF NOT EXISTS petri_calibration_results (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  species_name VARCHAR(128) NOT NULL,
  initial_params JSONB,
  calibrated_params JSONB,
  bounds JSONB,
  sample_count INT,
  delta_summary JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### petri_experiment_outcomes

High-level experiment outcomes for analytics and NLM consumption.

```sql
CREATE TABLE IF NOT EXISTS petri_experiment_outcomes (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id VARCHAR(64),
  species_id VARCHAR(64),
  outcome_type VARCHAR(32),
  summary JSONB,
  metrics_snapshot JSONB,
  nlm_consumed BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
```

## NLM Integration

When a simulation completes or a calibration finishes, call:

```python
from mycosoft_mas.nlm.workflow_bridge import trigger_workflow_from_nlm

await trigger_workflow_from_nlm("petri_outcome_ingest", {
    "session_id": session_id,
    "outcome_type": "simulation_complete" | "calibration_complete",
    "summary": {...},
    "metrics": {...},
})
```

Add `petri_outcome` / `simulation_outcome` to `NLM_TO_WORKFLOW_MAP` to route outcomes to learning workflows.

## Migration Path

1. Apply `MINDEX/mindex/migrations/0015_petri_simulation.sql` to MINDEX PostgreSQL when ready.
2. Add MINDEX API endpoints for POST/GET simulation sessions and outcomes (optional).
3. MAS uses file-based persistence (`data/petri_simulations.json`) by default; MINDEX sync when `MINDEX_API_URL` is set and endpoint exists.
