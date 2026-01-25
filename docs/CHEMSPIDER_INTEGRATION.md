# ChemSpider Integration Documentation

**Version**: 1.0.0  
**Date**: 2026-01-24  
**Author**: Mycosoft Development Team

---

## Overview

ChemSpider integration provides access to 120M+ chemical compounds via the Royal Society of Chemistry (RSC) API. This enables:

- Chemical compound lookup for all fungal species
- Molecular structure data (SMILES, InChI, InChIKey)
- Bioactivity predictions based on structure
- Integration with simulators (Petri Dish, Compound Analyzer)
- Chemistry-aware NLM (Nature Learning Model)

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         ChemSpider API                          │
│                  https://api.rsc.org/compounds/v1               │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    MINDEX ETL Layer                             │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │         mindex_etl/sources/chemspider.py                  │  │
│  │  - ChemSpiderClient class                                 │  │
│  │  - Rate limiting & caching                                │  │
│  │  - Compound mapping                                       │  │
│  └───────────────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │    mindex_etl/jobs/sync_chemspider_compounds.py           │  │
│  │  - Full sync of known fungal compounds                    │  │
│  │  - Incremental enrichment                                 │  │
│  │  - Species-compound linking                               │  │
│  └───────────────────────────────────────────────────────────┘  │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    MINDEX Database                              │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │  bio.compound   │  │bio.taxon_compound│ │bio.compound_    │  │
│  │  - chemspider_id│◄─│  - taxon_id      │ │    property     │  │
│  │  - name, formula│  │  - compound_id   │ └─────────────────┘  │
│  │  - smiles, inchi│  │  - evidence_level│                      │
│  └─────────────────┘  └─────────────────┘                       │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    MINDEX API                                   │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │              /api/compounds endpoints                      │  │
│  │  GET  /compounds              - List compounds             │  │
│  │  GET  /compounds/{id}         - Get compound details       │  │
│  │  GET  /compounds/for-taxon/{id} - Compounds for species    │  │
│  │  POST /compounds/search       - Search compounds           │  │
│  │  POST /compounds/enrich       - Enrich from ChemSpider     │  │
│  │  POST /compounds/chemspider/search - Direct ChemSpider     │  │
│  └───────────────────────────────────────────────────────────┘  │
└───────────────────────────┬─────────────────────────────────────┘
                            │
            ┌───────────────┼───────────────┐
            ▼               ▼               ▼
┌──────────────────┐ ┌──────────────┐ ┌──────────────┐
│  Website         │ │     NLM      │ │    MAS       │
│  ┌────────────┐  │ │ ┌──────────┐ │ │ ┌──────────┐ │
│  │Species Page│  │ │ │Chemistry │ │ │ │ChemSpider│ │
│  │Chemistry   │  │ │ │ Encoder  │ │ │ │  Sync    │ │
│  │   Tab      │  │ │ └──────────┘ │ │ │  Agent   │ │
│  └────────────┘  │ │ ┌──────────┐ │ │ └──────────┘ │
│  ┌────────────┐  │ │ │Knowledge │ │ │ ┌──────────┐ │
│  │Compound    │  │ │ │  Graph   │ │ │ │Compound  │ │
│  │ Analyzer   │  │ │ └──────────┘ │ │ │ Enricher │ │
│  └────────────┘  │ │ ┌──────────┐ │ │ │  Agent   │ │
│  ┌────────────┐  │ │ │Bioactiv. │ │ │ └──────────┘ │
│  │Petri Dish  │  │ │ │Predictor │ │ │              │
│  │ Simulator  │  │ │ └──────────┘ │ │              │
│  └────────────┘  │ └──────────────┘ └──────────────┘
└──────────────────┘
```

---

## Configuration

### Environment Variables

```bash
# Required
CHEMSPIDER_API_KEY=TSif8NaGxFixrCft4O581jGjIz2GnIo4TCQqM01h

# Optional
CHEMSPIDER_API_URL=https://api.rsc.org/compounds/v1
CHEMSPIDER_RATE_LIMIT=0.6  # seconds between requests
CHEMSPIDER_CACHE_TTL=86400  # 24 hours
```

### API Key Security

- **NEVER** commit API keys to git
- Store in environment variables or secrets manager
- Rotate key periodically (RSC dashboard)
- Monitor usage in RSC developer portal

---

## Database Schema

### New Tables (Migration 0007_compounds.sql)

```sql
-- Main compound table
bio.compound (
    id UUID PRIMARY KEY,
    name TEXT NOT NULL,
    formula TEXT,
    molecular_weight DOUBLE PRECISION,
    smiles TEXT,
    inchi TEXT,
    inchikey TEXT UNIQUE,
    chemspider_id INTEGER UNIQUE,
    pubchem_id INTEGER,
    chemical_class TEXT,
    compound_type TEXT,
    source TEXT DEFAULT 'chemspider',
    metadata JSONB
)

-- Species-compound relationships
bio.taxon_compound (
    taxon_id UUID REFERENCES core.taxon,
    compound_id UUID REFERENCES bio.compound,
    relationship_type TEXT,  -- produces, contains
    evidence_level TEXT,     -- verified, reported, predicted
    tissue_location TEXT,    -- fruiting_body, mycelium, spores
    source TEXT,
    doi TEXT
)

-- Compound properties (extensible)
bio.compound_property (
    compound_id UUID REFERENCES bio.compound,
    property_name TEXT,
    property_category TEXT,
    value_text TEXT,
    value_numeric DOUBLE PRECISION,
    value_unit TEXT
)

-- Biological activities
bio.biological_activity (
    name TEXT UNIQUE,
    category TEXT,
    description TEXT
)

bio.compound_activity (
    compound_id UUID REFERENCES bio.compound,
    activity_id UUID REFERENCES bio.biological_activity,
    potency TEXT,
    evidence_level TEXT
)
```

---

## API Endpoints

### Compounds Router (/api/compounds)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | List all compounds with pagination |
| GET | `/{id}` | Get compound by ID with activities |
| POST | `/` | Create new compound |
| POST | `/search` | Advanced compound search |
| GET | `/for-taxon/{id}` | Compounds for a species |
| POST | `/taxon-link` | Link compound to species |
| POST | `/enrich` | Enrich compound from ChemSpider |
| POST | `/chemspider/search` | Direct ChemSpider search |
| GET | `/activities` | List biological activities |

### Example: Get Species Compounds

```bash
curl http://localhost:8000/api/compounds/for-taxon/abc123-uuid

{
  "taxon_id": "abc123-uuid",
  "canonical_name": "Psilocybe cubensis",
  "common_name": "Golden Teacher",
  "compounds": [
    {
      "compound_id": "xyz789",
      "name": "Psilocybin",
      "formula": "C12H17N2O4P",
      "molecular_weight": 284.25,
      "chemspider_id": 10086,
      "relationship_type": "produces",
      "evidence_level": "verified",
      "tissue_location": "fruiting_body"
    }
  ]
}
```

### Example: Search ChemSpider

```bash
curl -X POST http://localhost:8000/api/compounds/chemspider/search \
  -H "Content-Type: application/json" \
  -d '{"query": "psilocybin", "search_type": "name", "max_results": 5}'

{
  "query": "psilocybin",
  "search_type": "name",
  "results": [
    {
      "chemspider_id": 10086,
      "name": "Psilocybin",
      "formula": "C12H17N2O4P",
      "molecular_weight": 284.25,
      "smiles": "CN(C)CCc1c[nH]c2cccc(OP(=O)(O)O)c12",
      "inchikey": "QJJDMQRZQPRMGB-UHFFFAOYSA-N"
    }
  ],
  "total_count": 1
}
```

---

## Website Integration

### Species Page Chemistry Tab

Located in `app/ancestry/species/[id]/page.tsx`:

- Shows compounds associated with species
- Displays molecular formula, weight
- Links to ChemSpider/PubChem
- Evidence level badges
- Bioactivity indicators

### Compound Analyzer

Located in `app/apps/compound-sim/page.tsx`:

- ChemSpider search functionality
- "Enrich Data" button for compound enrichment
- SMILES/InChI/InChIKey display
- External links to ChemSpider, PubChem
- Live MINDEX API integration

### lib/data/compounds.ts

New functions for MINDEX API:

```typescript
// Fetch compounds with filters
fetchCompounds({ search, chemicalClass, limit })

// Get single compound
fetchCompoundById(id)

// Get compounds for species
fetchCompoundsForSpecies(taxonId)

// Search ChemSpider directly
searchChemSpider(query, searchType, maxResults)

// Enrich compound from ChemSpider
enrichCompoundFromChemSpider(options)
```

---

## NLM Integration

### Chemistry Encoder (`nlm/chemistry/encoder.py`)

Encodes compounds into fixed-size vectors:

- Formula element counts
- Chemical class one-hot
- Bioactivity multi-hot
- Physical properties (MW, etc.)
- SMILES-based fingerprints

```python
from nlm.chemistry import ChemistryEncoder

encoder = ChemistryEncoder(embedding_dim=128)
embedding = encoder.encode({
    "name": "Psilocybin",
    "formula": "C12H17N2O4P",
    "smiles": "CN(C)CCc1c[nH]c2cccc(OP(=O)(O)O)c12",
    "activities": ["psychoactive", "serotonergic"]
})
# Returns: np.ndarray of shape (128,)
```

### Knowledge Graph (`nlm/chemistry/knowledge.py`)

Graph structure for compound relationships:

- Nodes: Compounds, Species, Activities, Targets
- Edges: produces, has_activity, targets, similar_to

```python
from nlm.chemistry import ChemistryKnowledgeGraph

graph = ChemistryKnowledgeGraph()
graph.add_compound("psilocybin", "Psilocybin", formula="C12H17N2O4P")
graph.add_species("psilocybe-cubensis", "Psilocybe cubensis")
graph.link_species_compound("psilocybe-cubensis", "psilocybin")

# Query
compounds = graph.get_compounds_for_species("psilocybe-cubensis")
```

### Bioactivity Predictor (`nlm/chemistry/predictor.py`)

Predicts activities based on compound similarity:

```python
from nlm.chemistry import BioactivityPredictor

predictor = BioactivityPredictor()
# Add known compounds...
predictor.add_compound(known_compound)

# Predict for new compound
predictions = predictor.predict_activities(new_compound)
# Returns: [{"activity_name": "psychoactive", "confidence": 0.85}, ...]
```

---

## MAS Agents

### Chemistry Agents (IDs 216-223)

| Agent | Description |
|-------|-------------|
| `chemspider-sync` | Syncs compound data from ChemSpider |
| `compound-enricher` | Enriches compounds with external data |
| `compound-analyzer` | Analyzes compound properties |
| `sar-analyzer` | Structure-Activity Relationship analysis |
| `protein-folder` | Protein folding predictions (AlphaFold) |
| `peptide-analyzer` | Peptide sequence analysis |
| `chemical-sim` | Chemical simulation engine |
| `bioactivity-predictor` | Predicts biological activity |

---

## ETL Jobs

### sync_chemspider_compounds.py

Full sync of fungal compounds:

```bash
# Full sync
python -m mindex_etl.jobs.sync_chemspider_compounds --full

# Limit to first 10 species
python -m mindex_etl.jobs.sync_chemspider_compounds --full --limit 10

# Incremental sync (species without compounds)
python -m mindex_etl.jobs.sync_chemspider_compounds

# Download only (no DB sync)
python -m mindex_etl.jobs.sync_chemspider_compounds --download-only
```

### Known Species-Compound Mappings

Pre-configured mappings for major medicinal fungi:

- Psilocybe cubensis → psilocybin, psilocin, baeocystin
- Hericium erinaceus → hericenones, erinacines
- Ganoderma lucidum → ganoderic acids, lucidenic acid
- Cordyceps militaris → cordycepin, adenosine
- Trametes versicolor → PSK, PSP
- Amanita muscaria → muscimol, ibotenic acid

---

## Rate Limiting

ChemSpider API limits:
- **100 requests/minute** with API key
- Built-in rate limiting in client (0.6s delay)
- Exponential backoff on 429 errors
- 24-hour cache TTL

---

## Troubleshooting

### "CHEMSPIDER_API_KEY not configured"

Set environment variable:
```bash
export CHEMSPIDER_API_KEY=your_key_here
```

### "Rate limit exceeded"

Wait and retry. The client handles this automatically with backoff.

### Compound not found

1. Check spelling
2. Try alternative names
3. Search by formula or SMILES instead
4. Check ChemSpider website manually

### Database connection errors

Ensure MINDEX database is running:
```bash
docker-compose -f docker-compose.always-on.yml up -d mindex-db
```

---

## Related Documents

- [MINDEX Architecture](./MINDEX_ARCHITECTURE.md)
- [Agent Registry](./AGENT_REGISTRY.md)
- [NLM Implementation Plan](./NLM_IMPLEMENTATION_PLAN.md)
- [System Architecture](./SYSTEM_ARCHITECTURE_OVERVIEW_JAN2026.md)

---

*Last Updated: 2026-01-24*
