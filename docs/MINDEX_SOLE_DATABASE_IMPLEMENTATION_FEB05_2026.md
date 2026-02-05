# MINDEX Sole Database System Implementation - Feb 5, 2026

## Overview

MINDEX is now the **sole database system** for all Mycosoft applications. This document summarizes the implementation completed to make MINDEX the canonical data layer for species, images, DNA sequences, research papers, and chemical compounds.

## Architecture

`
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚                        MINDEX VM (192.168.0.189)                    â”‚
â”œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¤
â”‚                                                                     â”‚
â”‚  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”                 â”‚
â”‚  â”‚ PostgreSQL  â”‚  â”‚   Redis     â”‚  â”‚   Qdrant    â”‚                 â”‚
â”‚  â”‚  (core.*)   â”‚  â”‚   Cache     â”‚  â”‚  Embeddings â”‚                 â”‚
â”‚  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜                 â”‚
â”‚                                                                     â”‚
â”‚  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”   â”‚
â”‚  â”‚                    MINDEX API (FastAPI)                      â”‚   â”‚
â”‚  â”‚  - /mindex/species/search                                    â”‚   â”‚
â”‚  â”‚  - /mindex/images/for-species/{id}                          â”‚   â”‚
â”‚  â”‚  - /mindex/sequences/search                                  â”‚   â”‚
â”‚  â”‚  - /mindex/research/search                                   â”‚   â”‚
â”‚  â”‚  - /mindex/compounds/search                                  â”‚   â”‚
â”‚  â”‚  - /mindex/unified/search                                    â”‚   â”‚
â”‚  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜   â”‚
â”‚                                                                     â”‚
â”‚  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”   â”‚
â”‚  â”‚                     Data Scrapers/ETL                        â”‚   â”‚
â”‚  â”‚  iNaturalist | GBIF | MycoBank | Index Fungorum              â”‚   â”‚
â”‚  â”‚  GenBank | PubMed | PubChem | ChEMBL                         â”‚   â”‚
â”‚  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜   â”‚
â”‚                                                                     â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
                              â”‚
                              â–¼
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚                    NAS Blob Storage (192.168.0.105)                 â”‚
â”‚   /mnt/nas/mycosoft/mindex/                                        â”‚
â”‚   â”œâ”€â”€ images/species/                                               â”‚
â”‚   â”œâ”€â”€ sequences/fasta/                                              â”‚
â”‚   â”œâ”€â”€ research/pdfs/                                                â”‚
â”‚   â””â”€â”€ compounds/structures/                                         â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
`

## Components Implemented

### 1. Data Scrapers (Phase 1)

| Scraper | File | Data Source | Features |
|---------|------|-------------|----------|
| iNaturalist | inaturalist_scraper.py | api.inaturalist.org | Rate limiting, API token auth, exponential backoff |
| GBIF | gbif_scraper.py | api.gbif.org | Rate limiting, authentication, occurrence data |
| MycoBank | mycobank_scraper.py | mycobank.org | Web scraping fallback, multiple parsing strategies |
| Index Fungorum | index_fungorum_scraper.py | indexfungorum.org | Web scraping, nomenclature data |
| GenBank | genbank_scraper.py | NCBI Entrez API | DNA sequences, FASTA storage, GC content |
| PubMed | pubmed_scraper.py | NCBI Entrez API | Research papers, PDF downloads |
| Chemistry | chemistry_scraper.py | PubChem, ChEMBL | Compounds, bioactivity data |

### 2. Blob Storage (Phase 1)

| Component | File | Purpose |
|-----------|------|---------|
| Migration | migrations/019_mindex_blobs.sql | Database schema for blob references |
| Manager | mindex/blob_manager.py | NAS file management, downloads, checksums |
| Documentation | docs/MINDEX_NAS_BLOB_STORAGE_FEB05_2026.md | Mount configuration |

Tables created:
- core.blobs - Blob metadata and paths
- core.species_images - Species-image relationships
- core.dna_sequences - DNA sequence records
- core.research_papers - Research paper metadata
- core.compounds - Chemical compound data
- core.blob_download_queue - Download queue

### 3. MINDEX API Endpoints (Phase 2)

| Endpoint | Method | Description |
|----------|--------|-------------|
| /mindex/species/search | GET | Search species by name |
| /mindex/species/{id} | GET | Get species by ID |
| /mindex/species/by-name/{name} | GET | Get species by scientific name |
| /mindex/images/for-species/{id} | GET | Get images for species |
| /mindex/images/search | GET | Search images by species name |
| /mindex/sequences/for-species/{id} | GET | Get DNA sequences for species |
| /mindex/sequences/search | GET | Search sequences |
| /mindex/sequences/{accession} | GET | Get sequence by accession |
| /mindex/research/for-species/{id} | GET | Get research papers for species |
| /mindex/research/search | GET | Search research papers |
| /mindex/compounds/for-species/{id} | GET | Get compounds for species |
| /mindex/compounds/search | GET | Search compounds |
| /mindex/unified/search | GET | Unified search across all data types |
| /mindex/stats | GET | Database statistics |

### 4. Website Integration (Phase 3)

Updated pp/api/search/unified/route.ts to:
- Query MINDEX exclusively for all data
- Remove iNaturalist fallback
- Use parallel queries to species, compounds, sequences, research endpoints
- 60-second response caching

### 5. MYCA Integration (Phase 3)

Created mindex/myca_integration.py with:
- MINDEXClient class for async queries
- Helper functions: get_species_summary(), get_compound_info()
- get_mindex_context_for_query() for LLM prompt injection
- Global client instance via get_mindex_client()

### 6. Full ETL Sync Script (Phase 4)

Created mindex/full_sync.py:
- Command-line runner for all scrapers
- Priority genera list (50+ genera)
- Parallel execution support
- Progress logging and result output

## Configuration

### Environment Variables

`ash
# MINDEX Database
MINDEX_DATABASE_URL=postgresql://mindex:password@192.168.0.189:5432/mindex
MINDEX_API_URL=http://192.168.0.189:8001

# API Keys
NCBI_API_KEY=your_ncbi_key  # For GenBank/PubMed (10 req/sec vs 3)
INATURALIST_API_TOKEN=your_inat_token
GBIF_USERNAME=your_username
GBIF_PASSWORD=your_password

# Blob Storage
BLOB_STORAGE_PATH=/mnt/nas/mycosoft/mindex
`

### NAS Mount (MINDEX VM)

`ash
# /etc/fstab entry
//192.168.0.105/mycosoft/mindex /mnt/nas/mycosoft/mindex cifs credentials=/etc/samba/.nascreds,uid=1000,gid=1000,vers=3.0,nofail 0 0
`

## Running the Full Sync

`ash
# Full sync (all sources, ~48 hours)
python -m mycosoft_mas.mindex.full_sync --sources all

# Test with limits
python -m mycosoft_mas.mindex.full_sync --sources inaturalist,gbif --limit 1000

# Specific sources
python -m mycosoft_mas.mindex.full_sync --sources genbank,pubmed
`

## Data Targets

| Data Type | Target Count | Source |
|-----------|--------------|--------|
| Species/Taxa | 575,000+ | iNaturalist, GBIF, MycoBank, Index Fungorum |
| Images | 2,000,000+ | iNaturalist, GBIF |
| DNA Sequences | 500,000+ | GenBank, BOLD |
| Research Papers | 100,000+ | PubMed |
| Compounds | 10,000+ | PubChem, ChEMBL |

## Files Created/Modified

### New Files
- mycosoft_mas/mindex/scrapers/index_fungorum_scraper.py
- mycosoft_mas/mindex/scrapers/pubmed_scraper.py
- mycosoft_mas/mindex/scrapers/chemistry_scraper.py
- mycosoft_mas/mindex/blob_manager.py
- mycosoft_mas/mindex/myca_integration.py
- mycosoft_mas/mindex/full_sync.py
- mycosoft_mas/core/routers/mindex_species_api.py
- migrations/019_mindex_blobs.sql
- docs/MINDEX_NAS_BLOB_STORAGE_FEB05_2026.md

### Modified Files
- mycosoft_mas/mindex/scrapers/inaturalist_scraper.py - Rate limiting, API token
- mycosoft_mas/mindex/scrapers/gbif_scraper.py - Rate limiting, auth, occurrences
- mycosoft_mas/mindex/scrapers/mycobank_scraper.py - Web scraping fallback
- mycosoft_mas/mindex/scrapers/genbank_scraper.py - Enhanced with FASTA storage
- website/app/api/search/unified/route.ts - MINDEX-exclusive search

## Next Steps

1. **Run Initial Sync**: Execute python -m mycosoft_mas.mindex.full_sync --sources all on MINDEX VM
2. **Configure NAS Mount**: Follow MINDEX_NAS_BLOB_STORAGE_FEB05_2026.md
3. **Monitor Progress**: Check sync logs in mindex_sync_*.log
4. **Test API Endpoints**: Verify /mindex/species/search?q=Amanita returns data
5. **Validate Website**: Confirm mycosoft.com search uses MINDEX data

## API Usage Examples

### Search Species
`ash
curl "http://192.168.0.189:8001/mindex/species/search?q=Amanita&limit=5"
`

### Get Species Details
`ash
curl "http://192.168.0.189:8001/mindex/species/48715"
`

### Unified Search
`ash
curl "http://192.168.0.189:8001/mindex/unified/search?q=psilocybin&include_species=true&include_compounds=true"
`

### Check Stats
`ash
curl "http://192.168.0.189:8001/mindex/stats"
`

## Troubleshooting

### Scraper Rate Limiting
All scrapers implement exponential backoff. If rate limited:
- Check API key configuration
- Reduce batch sizes
- Increase request delays

### Database Connection Issues
`ash
# Test PostgreSQL connection
psql -h 192.168.0.189 -U mindex -d mindex -c "SELECT COUNT(*) FROM core.taxon"
`

### NAS Mount Issues
`ash
# Check mount
df -h /mnt/nas/mycosoft/mindex

# Remount if needed
sudo mount -a
`

---
*Document created: Feb 5, 2026*
*Implementation status: Complete*
