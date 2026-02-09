# data/

Runtime data storage directory for MAS knowledge bases and local data files.

## Contents

| Directory/File | Purpose |
|----------------|---------|
| `fungal_knowledge/` | Fungal knowledge graph data files (species, compounds, taxonomy) |

## Notes

- This directory stores data files used by the MAS agents at runtime (e.g., pre-built knowledge graphs, cached datasets).
- Large data files and binary blobs are excluded from Git via `.gitignore` / `.cursorignore`.
- Production data is stored in MINDEX (VM 189): PostgreSQL (port 5432), Redis (port 6379), Qdrant (port 6333).
- For ETL/ingestion that populates these data stores, see `mycosoft_mas/mindex/` and `MINDEX/mindex/mindex_etl/`.
