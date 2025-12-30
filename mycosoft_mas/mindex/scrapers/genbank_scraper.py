"""
GenBank/NCBI Scraper for MINDEX

Fetches genetic sequence data from NCBI GenBank.
Uses Entrez E-utilities API.
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
import aiohttp
import xml.etree.ElementTree as ET

logger = logging.getLogger(__name__)


class GenBankScraper:
    """
    Scraper for NCBI GenBank fungal sequences.
    
    Fetches:
    - ITS sequences (fungal barcoding)
    - LSU/SSU rRNA sequences
    - Genome sequences
    """
    
    ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
    ESUMMARY_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
    
    # Fungi taxonomy ID
    FUNGI_TAXID = 4751
    
    def __init__(self, db=None, api_key: str = None):
        self.db = db
        self.api_key = api_key  # Increases rate limit to 10/sec
    
    async def search_sequences(
        self,
        query: str = None,
        gene: str = "ITS",
        limit: int = 1000,
    ) -> List[str]:
        """
        Search for fungal sequences in GenBank.
        Returns list of accession IDs.
        """
        if not query:
            query = f"Fungi[Organism] AND {gene}[Gene]"
        
        accessions = []
        
        async with aiohttp.ClientSession() as session:
            try:
                params = {
                    "db": "nucleotide",
                    "term": query,
                    "retmax": min(limit, 10000),
                    "retmode": "json",
                    "usehistory": "y",
                }
                
                if self.api_key:
                    params["api_key"] = self.api_key
                
                async with session.get(self.ESEARCH_URL, params=params) as response:
                    if response.status != 200:
                        logger.error(f"GenBank search error: {response.status}")
                        return accessions
                    
                    data = await response.json()
                    accessions = data.get("esearchresult", {}).get("idlist", [])
                    
                    logger.info(f"Found {len(accessions)} sequences in GenBank")
                    
            except Exception as e:
                logger.error(f"Error searching GenBank: {e}")
        
        return accessions[:limit]
    
    async def fetch_sequences(
        self,
        accessions: List[str],
        batch_size: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Fetch sequence details by accession IDs.
        """
        sequences = []
        
        async with aiohttp.ClientSession() as session:
            for i in range(0, len(accessions), batch_size):
                batch = accessions[i:i + batch_size]
                
                try:
                    params = {
                        "db": "nucleotide",
                        "id": ",".join(batch),
                        "rettype": "gb",
                        "retmode": "xml",
                    }
                    
                    if self.api_key:
                        params["api_key"] = self.api_key
                    
                    async with session.get(self.EFETCH_URL, params=params) as response:
                        if response.status != 200:
                            continue
                        
                        xml_data = await response.text()
                        parsed = self._parse_genbank_xml(xml_data)
                        sequences.extend(parsed)
                        
                    await asyncio.sleep(0.4)  # Rate limiting (3/sec without API key)
                    
                except Exception as e:
                    logger.error(f"Error fetching sequences: {e}")
        
        logger.info(f"Fetched {len(sequences)} sequence records from GenBank")
        return sequences
    
    async def fetch_fungal_its(self, limit: int = 1000) -> List[Dict[str, Any]]:
        """
        Fetch ITS (Internal Transcribed Spacer) sequences for fungi.
        ITS is the primary barcode for fungal identification.
        """
        query = "Fungi[Organism] AND (ITS1 OR ITS2 OR internal transcribed spacer)[Title]"
        accessions = await self.search_sequences(query=query, limit=limit)
        return await self.fetch_sequences(accessions)
    
    async def fetch_fungal_lsu(self, limit: int = 500) -> List[Dict[str, Any]]:
        """
        Fetch LSU (Large Subunit) rRNA sequences.
        """
        query = "Fungi[Organism] AND (28S OR LSU)[Title]"
        accessions = await self.search_sequences(query=query, limit=limit)
        return await self.fetch_sequences(accessions)
    
    def _parse_genbank_xml(self, xml_data: str) -> List[Dict[str, Any]]:
        """Parse GenBank XML response."""
        sequences = []
        
        try:
            root = ET.fromstring(xml_data)
            
            for seq in root.findall(".//GBSeq"):
                try:
                    accession = seq.findtext("GBSeq_primary-accession")
                    organism = seq.findtext("GBSeq_organism")
                    definition = seq.findtext("GBSeq_definition")
                    sequence = seq.findtext("GBSeq_sequence")
                    
                    # Determine sequence type from definition
                    seq_type = "unknown"
                    gene_region = None
                    
                    def_lower = (definition or "").lower()
                    if "its" in def_lower:
                        seq_type = "ITS"
                        gene_region = "ITS"
                    elif "28s" in def_lower or "lsu" in def_lower:
                        seq_type = "rRNA"
                        gene_region = "28S LSU"
                    elif "18s" in def_lower or "ssu" in def_lower:
                        seq_type = "rRNA"
                        gene_region = "18S SSU"
                    elif "genome" in def_lower:
                        seq_type = "genome"
                    
                    # Extract strain/isolate from features
                    strain = None
                    country = None
                    collection_date = None
                    
                    for feat in seq.findall(".//GBFeature"):
                        for qual in feat.findall(".//GBQualifier"):
                            name = qual.findtext("GBQualifier_name")
                            value = qual.findtext("GBQualifier_value")
                            
                            if name == "strain":
                                strain = value
                            elif name == "country":
                                country = value
                            elif name == "collection_date":
                                collection_date = value
                    
                    sequences.append({
                        "accession": accession,
                        "sequence_type": seq_type,
                        "gene_region": gene_region,
                        "sequence": sequence,
                        "sequence_length": len(sequence) if sequence else 0,
                        "organism_name": organism,
                        "strain": strain,
                        "country": country,
                        "collection_date": collection_date,
                        "source": "GenBank",
                        "source_id": accession,
                    })
                    
                except Exception as e:
                    logger.debug(f"Error parsing sequence: {e}")
                    
        except Exception as e:
            logger.error(f"Error parsing GenBank XML: {e}")
        
        return sequences
    
    async def sync(self, limit: int = 1000) -> Dict[str, int]:
        """
        Full sync of fungal sequences from GenBank.
        """
        stats = {
            "sequences_fetched": 0,
            "sequences_inserted": 0,
        }
        
        # Fetch ITS sequences (most important for fungi)
        its_sequences = await self.fetch_fungal_its(limit=limit // 2)
        stats["sequences_fetched"] += len(its_sequences)
        
        # Fetch LSU sequences
        lsu_sequences = await self.fetch_fungal_lsu(limit=limit // 2)
        stats["sequences_fetched"] += len(lsu_sequences)
        
        all_sequences = its_sequences + lsu_sequences
        
        if self.db:
            for seq in all_sequences:
                try:
                    self.db.insert_genetic_record(seq)
                    stats["sequences_inserted"] += 1
                except Exception as e:
                    logger.error(f"Error inserting sequence: {e}")
        
        return stats

