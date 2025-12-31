# MINDEX Taxonomic Reconciliation Implementation

## Overview

MINDEX now includes comprehensive taxonomic reconciliation following best practices for biodiversity data integration. This system reconciles species names across GBIF, iNaturalist, and Index Fungorum using standardized taxonomic backbones and nomenclators.

## Features Implemented

### ✅ GBIF Backbone Taxonomy Matching

- Uses GBIF's `/species/match` endpoint for name matching
- Supports fuzzy matching with confidence scores (0-100)
- Returns stable `gbifID` for each matched taxon
- Handles EXACT, FUZZY, and NONE match types

### ✅ Index Fungorum Integration (Framework)

- Framework in place for Index Fungorum LSID (Life Science Identifier) integration
- Ready for fungal name nomenclatural provenance tracking
- Can be extended with official IF API or LSID resolution

### ✅ Synonym Handling

- Intelligently resolves synonyms to accepted names
- Tracks both original name and accepted name with IDs
- Handles nomenclatural status (ACCEPTED, SYNONYM, DOUBTFUL)

### ✅ License Filtering

- Enforces Creative Commons license compliance
- Accepts: CC0, CC-BY, CC-BY-SA, and public domain
- Tracks license metadata for attribution requirements
- Filters out non-compliant records when enforcement is enabled

### ✅ Deduplication

- Uses SHA-256 citation hashes for record identification
- Groups records by taxon identifier (gbifID or normalized name+author)
- Deduplicates within groups to avoid redundant entries

### ✅ Name Normalization

- Extracts canonical name (genus + specific epithet)
- Separates author strings from scientific names
- Handles various name formats consistently

## Architecture

### Core Modules

1. **`reconciliation.py`** - Core reconciliation engine
   - `TaxonomicReconciler` - Main reconciliation class
   - `TaxonomicMatch` - Match result data structure
   - `LicenseInfo` - License metadata container

2. **`reconciliation_integration.py`** - Scraper integration layer
   - `ReconciledScraper` - Wrapper for automatic reconciliation
   - `reconcile_scraper_output()` - Convenience function

3. **Database Schema Updates**
   - Added reconciliation fields to `species` table:
     - `gbif_id`, `gbif_match_type`, `gbif_confidence`
     - `accepted_gbif_id`, `accepted_name`
     - `index_fungorum_lsid`, `index_fungorum_name_id`
     - `citation_hash`
     - License fields: `license`, `license_url`, `license_compliant`, `rights_holder`

## Usage

### Automatic Reconciliation in Scrapers

The GBIF and iNaturalist scrapers now automatically reconcile taxonomy:

```python
from mycosoft_mas.mindex.manager import MINDEXManager

manager = MINDEXManager(db_path="data/mindex.db")

# Sync will automatically reconcile taxonomy
stats = await manager.sync_source("GBIF", limit=1000)
# stats includes: species_reconciled count
```

### Manual Reconciliation

```python
from mycosoft_mas.mindex.reconciliation import TaxonomicReconciler

reconciler = TaxonomicReconciler()

# Reconcile a single record
match, license_info, citation_hash = await reconciler.reconcile({
    "scientific_name": "Amanita muscaria",
    "source": "iNaturalist",
    "external_id": "inat-12345",
    "license": "CC-BY-4.0"
})

print(f"GBIF ID: {match.gbif_id}")
print(f"Match type: {match.gbif_match_type}")
print(f"License compliant: {license_info.is_compliant}")
```

### Batch Reconciliation

```python
records = [
    {"scientific_name": "Amanita muscaria", "source": "GBIF"},
    {"scientific_name": "Psilocybe cubensis", "source": "iNaturalist"},
]

reconciled = await reconciler.reconcile_batch(records, enforce_license=True)

# Group by taxon
groups = await reconciler.group_by_taxon(reconciled)

# Deduplicate each group
for group_key, group_records in groups.items():
    deduplicated = await reconciler.deduplicate_group(group_records)
```

## Reconciliation Pipeline

The reconciliation process follows this flow:

1. **Ingest Source Records** - Fetch from iNaturalist, GBIF, etc.
2. **Normalize Names** - Extract canonical name and author
3. **Match Against GBIF** - Use `/species/match` endpoint
4. **Query Index Fungorum** - For fungi, get LSID and nomenclatural data
5. **Resolve Synonyms** - Map to accepted names
6. **Filter Licenses** - Enforce Creative Commons compliance
7. **Generate Citation Hash** - For deduplication
8. **Group by Taxon** - Use gbifID or normalized name+author
9. **Deduplicate** - Remove redundant records within groups

## Data Flow

```
Source Record (iNaturalist/GBIF/etc.)
    ↓
Name Normalization
    ↓
GBIF Backbone Match → gbifID + match type
    ↓
Index Fungorum Lookup → LSID (if fungi)
    ↓
Synonym Resolution → Accepted name + ID
    ↓
License Validation → Filter if non-compliant
    ↓
Citation Hash Generation → For deduplication
    ↓
Grouping → By gbifID or name+author
    ↓
Deduplication → Within groups
    ↓
Enriched Record → Ready for storage
```

## Benefits

1. **Reliable IDs** - Stable gbifIDs across all sources
2. **Consistent Taxonomy** - Synonym resolution ensures data quality
3. **License Compliance** - Automatic filtering of non-compliant data
4. **No Duplicates** - Citation hash-based deduplication
5. **Provenance Tracking** - Full metadata on reconciliation process
6. **Standards Compliant** - Follows GBIF and biodiversity data best practices

## Future Enhancements

- [ ] Full Index Fungorum API integration
- [ ] MycoBank integration for additional fungal authority
- [ ] Synonym graph construction
- [ ] Batch reconciliation with caching
- [ ] Reconciliation quality metrics and reporting
- [ ] Support for additional name authorities

## References

- [GBIF Species API Documentation](https://data-blog.gbif.org/post/gbif-species-api/)
- [GBIF Occurrence License Processing](https://data-blog.gbif.org/post/gbif-occurrence-license-processing/)
- [Index Fungorum](https://www.indexfungorum.org/)
- [iNaturalist API Reference](https://www.inaturalist.org/pages/api+reference)

