"""
Integration layer for taxonomic reconciliation with MINDEX scrapers.

Wraps scrapers to automatically reconcile taxonomic data and apply
best practices for biodiversity data integration.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from .reconciliation import TaxonomicReconciler, TaxonomicMatch, LicenseInfo

logger = logging.getLogger(__name__)


class ReconciledScraper:
    """
    Wrapper that adds taxonomic reconciliation to any scraper.
    
    Automatically:
    - Matches names against GBIF backbone
    - Applies license filtering
    - Deduplicates records
    - Groups by taxon identifier
    """
    
    def __init__(self, scraper, reconciler: Optional[TaxonomicReconciler] = None):
        self.scraper = scraper
        self.reconciler = reconciler or TaxonomicReconciler()
        self.enforce_license = True
    
    async def fetch_and_reconcile(
        self,
        limit: int = 1000,
        **scraper_kwargs
    ) -> Dict[str, Any]:
        """
        Fetch data from scraper and reconcile taxonomy.
        
        Returns reconciled records with enriched metadata.
        """
        # Fetch raw records
        if hasattr(self.scraper, 'fetch_species'):
            raw_records = await self.scraper.fetch_species(limit=limit, **scraper_kwargs)
        elif hasattr(self.scraper, 'fetch_observations'):
            raw_records = await self.scraper.fetch_observations(limit=limit, **scraper_kwargs)
        else:
            raise ValueError(f"Scraper {type(self.scraper)} doesn't have fetch_species or fetch_observations")
        
        # Reconcile each record
        reconciled = await self.reconciler.reconcile_batch(
            raw_records,
            enforce_license=self.enforce_license,
        )
        
        # Filter out exceptions and non-compliant licenses
        valid_records = []
        for result in reconciled:
            if isinstance(result, Exception):
                logger.error(f"Reconciliation error: {result}")
                continue
            
            match, license_info, citation_hash = result
            
            # Skip if license not compliant (when enforcement is on)
            if self.enforce_license and not license_info.is_compliant:
                continue
            
            valid_records.append((match, license_info, citation_hash))
        
        # Group by taxon
        groups = await self.reconciler.group_by_taxon(valid_records)
        
        # Deduplicate each group
        deduplicated_groups = {}
        for group_key, group_records in groups.items():
            deduplicated = await self.reconciler.deduplicate_group(group_records)
            if deduplicated:
                deduplicated_groups[group_key] = deduplicated
        
        # Build result with enriched data
        enriched_records = []
        for group_key, group_records in deduplicated_groups.items():
            for match, license_info, citation_hash in group_records:
                enriched = self._enrich_record(match, license_info, citation_hash)
                enriched_records.append(enriched)
        
        return {
            "records": enriched_records,
            "total_reconciled": len(valid_records),
            "total_deduplicated": len(enriched_records),
            "groups": len(deduplicated_groups),
            "sources": set(r.get("source") for r in enriched_records),
        }
    
    def _enrich_record(
        self,
        match: TaxonomicMatch,
        license_info: LicenseInfo,
        citation_hash: str
    ) -> Dict[str, Any]:
        """Enrich record with reconciliation metadata."""
        return {
            # Original taxonomic fields
            "scientific_name": match.scientific_name,
            "canonical_name": match.canonical_name,
            "author": match.author,
            
            # GBIF reconciliation
            "gbif_id": match.gbif_id,
            "gbif_match_type": match.gbif_match_type,
            "gbif_confidence": match.gbif_confidence,
            "accepted_gbif_id": match.accepted_gbif_id,
            "accepted_name": match.accepted_name,
            
            # Index Fungorum (if available)
            "index_fungorum_lsid": match.index_fungorum_lsid,
            "index_fungorum_name_id": match.index_fungorum_name_id,
            
            # Status and synonyms
            "status": match.status,
            "synonyms": match.synonyms,
            
            # Taxonomy hierarchy
            "kingdom": match.kingdom,
            "phylum": match.phylum,
            "class_name": match.class_name,
            "order_name": match.order_name,
            "family": match.family,
            "genus": match.genus,
            "species_epithet": match.species_epithet,
            
            # License information
            "license": license_info.license_type,
            "license_url": license_info.license_url,
            "rights_holder": license_info.rights_holder,
            "attribution": license_info.attribution,
            "license_compliant": license_info.is_compliant,
            
            # Deduplication
            "citation_hash": citation_hash,
            
            # Source provenance
            "source": match.source,
            "source_record_id": match.source_record_id,
            "reconciliation_timestamp": match.reconciliation_timestamp.isoformat(),
        }


async def reconcile_scraper_output(
    scraper,
    records: List[Dict[str, Any]],
    enforce_license: bool = True,
) -> List[Dict[str, Any]]:
    """
    Reconcile a batch of scraper output records.
    
    This is a convenience function for use with existing scrapers.
    """
    reconciler = TaxonomicReconciler()
    
    try:
        # Reconcile all records
        reconciled = await reconciler.reconcile_batch(records, enforce_license)
        
        # Filter and enrich
        enriched = []
        for result in reconciled:
            if isinstance(result, Exception):
                continue
            
            match, license_info, citation_hash = result
            
            if enforce_license and not license_info.is_compliant:
                continue
            
            # Build enriched record (merge original with reconciliation data)
            enriched_record = records[reconciled.index(result)].copy()
            enriched_record.update({
                "gbif_id": match.gbif_id,
                "gbif_match_type": match.gbif_match_type,
                "gbif_confidence": match.gbif_confidence,
                "accepted_gbif_id": match.accepted_gbif_id,
                "accepted_name": match.accepted_name,
                "canonical_name": match.canonical_name,
                "status": match.status,
                "license_compliant": license_info.is_compliant,
                "citation_hash": citation_hash,
                "reconciliation_timestamp": match.reconciliation_timestamp.isoformat(),
            })
            enriched.append(enriched_record)
        
        return enriched
    
    finally:
        await reconciler.close()


