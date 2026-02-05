"""
GenBank/NCBI Scraper for MINDEX - Feb 5, 2026

Fetches genetic sequence data from NCBI GenBank.
Uses Entrez E-utilities API with proper rate limiting and authentication.

Enhanced features:
- API key authentication (10 req/sec vs 3 req/sec)
- Exponential backoff for rate limiting
- FASTA file storage via blob manager
- GC content calculation
- Batch processing with pagination
- Multiple gene regions (ITS, LSU, SSU, RPB1, RPB2, TEF1)
"""

import asyncio
import logging
import os
import re
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple

import aiohttp

logger = logging.getLogger(__name__)


class RateLimiter:
    """Rate limiter with exponential backoff."""
    
    def __init__(
        self,
        requests_per_second: float = 3.0,
        max_delay: float = 60.0,
    ):
        self.min_interval = 1.0 / requests_per_second
        self.max_delay = max_delay
        self.last_request_time = 0.0
        self.consecutive_errors = 0
    
    async def wait(self):
        """Wait appropriate time before next request."""
        now = asyncio.get_event_loop().time()
        elapsed = now - self.last_request_time
        
        # Base wait time
        wait_time = max(0, self.min_interval - elapsed)
        
        # Add backoff for errors
        if self.consecutive_errors > 0:
            backoff = min(self.max_delay, 2 ** self.consecutive_errors)
            wait_time = max(wait_time, backoff)
        
        if wait_time > 0:
            await asyncio.sleep(wait_time)
        
        self.last_request_time = asyncio.get_event_loop().time()
    
    def success(self):
        """Record successful request."""
        self.consecutive_errors = 0
    
    def failure(self):
        """Record failed request."""
        self.consecutive_errors += 1


class GenBankScraper:
    """
    Enhanced scraper for NCBI GenBank fungal sequences.
    
    Fetches:
    - ITS sequences (fungal barcoding - primary)
    - LSU/28S rRNA sequences
    - SSU/18S rRNA sequences
    - Protein-coding genes (RPB1, RPB2, TEF1)
    - Whole genome sequences
    """
    
    ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
    ESUMMARY_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
    EINFO_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/einfo.fcgi"
    
    # Fungi taxonomy ID
    FUNGI_TAXID = 4751
    
    # Gene regions commonly used for fungal identification
    GENE_REGIONS = {
        "ITS": "internal transcribed spacer",
        "ITS1": "internal transcribed spacer 1",
        "ITS2": "internal transcribed spacer 2",
        "LSU": "large subunit ribosomal RNA",
        "28S": "28S ribosomal RNA",
        "SSU": "small subunit ribosomal RNA",
        "18S": "18S ribosomal RNA",
        "RPB1": "RNA polymerase II largest subunit",
        "RPB2": "RNA polymerase II second largest subunit",
        "TEF1": "translation elongation factor 1 alpha",
        "BTUB": "beta-tubulin",
        "CO1": "cytochrome c oxidase subunit 1",
        "COI": "cytochrome c oxidase subunit I",
    }
    
    def __init__(
        self,
        db=None,
        api_key: Optional[str] = None,
        blob_manager=None,
        email: str = "contact@mycosoft.com",
    ):
        """
        Initialize GenBank scraper.
        
        Args:
            db: Database connection
            api_key: NCBI API key (get from https://www.ncbi.nlm.nih.gov/account/settings/)
            blob_manager: BlobManager for storing FASTA files
            email: Email for NCBI API requests (required by their terms)
        """
        self.db = db
        self.api_key = api_key or os.environ.get("NCBI_API_KEY")
        self.blob_manager = blob_manager
        self.email = email
        
        # Rate limit: 10/sec with API key, 3/sec without
        requests_per_second = 10.0 if self.api_key else 3.0
        self.rate_limiter = RateLimiter(requests_per_second=requests_per_second)
        
        self.seen_accessions: Set[str] = set()
    
    def _get_params(self, base_params: Dict) -> Dict:
        """Add common parameters to request."""
        params = {**base_params}
        if self.api_key:
            params["api_key"] = self.api_key
        params["email"] = self.email
        params["tool"] = "mycosoft-mindex"
        return params
    
    async def _make_request(
        self,
        session: aiohttp.ClientSession,
        url: str,
        params: Dict,
        max_retries: int = 3,
    ) -> Optional[str]:
        """Make request with rate limiting and retries."""
        params = self._get_params(params)
        
        for attempt in range(max_retries):
            await self.rate_limiter.wait()
            
            try:
                async with session.get(
                    url,
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=60),
                ) as response:
                    if response.status == 200:
                        self.rate_limiter.success()
                        return await response.text()
                    elif response.status == 429:
                        logger.warning(f"Rate limited by NCBI, backing off...")
                        self.rate_limiter.failure()
                        continue
                    elif response.status >= 500:
                        logger.warning(f"NCBI server error: {response.status}")
                        self.rate_limiter.failure()
                        continue
                    else:
                        logger.error(f"NCBI API error: {response.status}")
                        return None
            except asyncio.TimeoutError:
                logger.warning(f"Timeout on attempt {attempt + 1}")
                self.rate_limiter.failure()
            except aiohttp.ClientError as e:
                logger.error(f"Network error: {e}")
                self.rate_limiter.failure()
        
        return None
    
    async def search_sequences(
        self,
        query: Optional[str] = None,
        gene: str = "ITS",
        organism: str = "Fungi",
        min_length: int = 100,
        max_length: int = 50000,
        limit: int = 1000,
        session: Optional[aiohttp.ClientSession] = None,
    ) -> Tuple[List[str], int]:
        """
        Search for fungal sequences in GenBank.
        
        Returns:
            Tuple of (list of accession IDs, total count)
        """
        close_session = False
        if session is None:
            session = aiohttp.ClientSession()
            close_session = True
        
        try:
            # Build search query
            if not query:
                gene_terms = self.GENE_REGIONS.get(gene, gene)
                query = f'"{organism}"[Organism] AND ("{gene}"[Gene] OR "{gene_terms}"[Title])'
                query += f' AND {min_length}:{max_length}[SLEN]'
            
            accessions = []
            total_count = 0
            retstart = 0
            batch_size = min(limit, 10000)  # NCBI max is 10000
            
            while len(accessions) < limit:
                params = {
                    "db": "nucleotide",
                    "term": query,
                    "retmax": batch_size,
                    "retstart": retstart,
                    "retmode": "json",
                    "sort": "relevance",
                }
                
                response = await self._make_request(session, self.ESEARCH_URL, params)
                if not response:
                    break
                
                try:
                    import json
                    data = json.loads(response)
                    result = data.get("esearchresult", {})
                    
                    ids = result.get("idlist", [])
                    if not ids:
                        break
                    
                    accessions.extend(ids)
                    total_count = int(result.get("count", len(accessions)))
                    
                    if len(ids) < batch_size:
                        break  # No more results
                    
                    retstart += batch_size
                    
                except Exception as e:
                    logger.error(f"Error parsing search response: {e}")
                    break
            
            logger.info(f"Found {len(accessions)} sequences (total: {total_count}) for {gene}")
            return accessions[:limit], total_count
            
        finally:
            if close_session:
                await session.close()
    
    async def fetch_sequences(
        self,
        accessions: List[str],
        batch_size: int = 100,
        session: Optional[aiohttp.ClientSession] = None,
        save_fasta: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Fetch sequence details and FASTA by accession IDs.
        
        Args:
            accessions: List of accession/GI numbers
            batch_size: Batch size for fetching
            session: Optional aiohttp session
            save_fasta: Whether to save FASTA files via blob manager
        """
        close_session = False
        if session is None:
            session = aiohttp.ClientSession()
            close_session = True
        
        try:
            sequences = []
            
            for i in range(0, len(accessions), batch_size):
                batch = accessions[i:i + batch_size]
                
                # Fetch GenBank format for metadata
                gb_params = {
                    "db": "nucleotide",
                    "id": ",".join(batch),
                    "rettype": "gb",
                    "retmode": "xml",
                }
                
                xml_data = await self._make_request(session, self.EFETCH_URL, gb_params)
                if xml_data:
                    parsed = self._parse_genbank_xml(xml_data)
                    
                    # Calculate GC content
                    for seq in parsed:
                        if seq.get("sequence"):
                            seq["gc_content"] = self._calculate_gc_content(seq["sequence"])
                    
                    sequences.extend(parsed)
                
                # Also fetch FASTA format for clean sequences
                if save_fasta and self.blob_manager:
                    fasta_params = {
                        "db": "nucleotide",
                        "id": ",".join(batch),
                        "rettype": "fasta",
                        "retmode": "text",
                    }
                    
                    fasta_data = await self._make_request(session, self.EFETCH_URL, fasta_params)
                    if fasta_data:
                        await self._save_fasta_sequences(fasta_data, sequences)
                
                logger.info(f"Fetched batch {i//batch_size + 1}, total: {len(sequences)} sequences")
            
            return sequences
            
        finally:
            if close_session:
                await session.close()
    
    def _parse_genbank_xml(self, xml_data: str) -> List[Dict[str, Any]]:
        """Parse GenBank XML response with enhanced metadata extraction."""
        sequences = []
        
        try:
            root = ET.fromstring(xml_data)
            
            for seq in root.findall(".//GBSeq"):
                try:
                    accession = seq.findtext("GBSeq_primary-accession")
                    
                    # Skip if already processed
                    if accession in self.seen_accessions:
                        continue
                    self.seen_accessions.add(accession)
                    
                    organism = seq.findtext("GBSeq_organism")
                    definition = seq.findtext("GBSeq_definition")
                    sequence = seq.findtext("GBSeq_sequence") or ""
                    
                    # Get additional metadata
                    gi_number = None
                    for other_id in seq.findall(".//GBSeqid"):
                        if other_id.text and other_id.text.startswith("gi|"):
                            gi_number = other_id.text.split("|")[1]
                            break
                    
                    # Determine gene region from definition
                    gene_region = self._detect_gene_region(definition)
                    
                    # Extract features
                    strain = None
                    country = None
                    collection_date = None
                    specimen_voucher = None
                    pubmed_ids = []
                    
                    for feat in seq.findall(".//GBFeature"):
                        for qual in feat.findall(".//GBQualifier"):
                            name = qual.findtext("GBQualifier_name")
                            value = qual.findtext("GBQualifier_value")
                            
                            if name == "strain" and not strain:
                                strain = value
                            elif name == "isolate" and not strain:
                                strain = value
                            elif name == "country":
                                country = value
                            elif name == "collection_date":
                                collection_date = value
                            elif name == "specimen_voucher":
                                specimen_voucher = value
                    
                    # Extract PubMed IDs from references
                    for ref in seq.findall(".//GBReference"):
                        pmid = ref.findtext(".//GBReference_pubmed")
                        if pmid:
                            pubmed_ids.append(pmid)
                    
                    # Parse creation date
                    create_date = seq.findtext("GBSeq_create-date")
                    update_date = seq.findtext("GBSeq_update-date")
                    
                    record = {
                        "accession": accession,
                        "gi_number": gi_number,
                        "gene_region": gene_region,
                        "sequence": sequence.upper() if sequence else None,
                        "sequence_length": len(sequence) if sequence else 0,
                        "definition": definition,
                        "organism": organism,
                        "scientific_name": self._extract_species_name(organism),
                        "strain": strain,
                        "specimen_voucher": specimen_voucher,
                        "country": country,
                        "collection_date": collection_date,
                        "pubmed_ids": pubmed_ids,
                        "create_date": create_date,
                        "update_date": update_date,
                        "source": "GenBank",
                        "source_url": f"https://www.ncbi.nlm.nih.gov/nuccore/{accession}",
                    }
                    
                    sequences.append(record)
                    
                except Exception as e:
                    logger.debug(f"Error parsing sequence: {e}")
                    
        except ET.ParseError as e:
            logger.error(f"Error parsing GenBank XML: {e}")
        
        return sequences
    
    def _detect_gene_region(self, definition: str) -> Optional[str]:
        """Detect gene region from sequence definition."""
        if not definition:
            return None
        
        def_lower = definition.lower()
        
        # Check for specific gene regions
        for gene, description in self.GENE_REGIONS.items():
            if gene.lower() in def_lower or description.lower() in def_lower:
                return gene
        
        # Additional patterns
        if "its1" in def_lower and "its2" in def_lower:
            return "ITS"
        elif "5.8s" in def_lower:
            return "ITS"
        elif "genome" in def_lower:
            return "genome"
        
        return None
    
    def _extract_species_name(self, organism: str) -> Optional[str]:
        """Extract species binomial from organism field."""
        if not organism:
            return None
        
        # Remove strain/isolate info in parentheses
        name = re.sub(r'\s*\([^)]*\)', '', organism)
        
        # Get first two words (genus + species)
        parts = name.split()
        if len(parts) >= 2:
            return f"{parts[0]} {parts[1]}"
        
        return name.strip()
    
    def _calculate_gc_content(self, sequence: str) -> float:
        """Calculate GC content percentage."""
        if not sequence:
            return 0.0
        
        sequence = sequence.upper()
        gc_count = sequence.count('G') + sequence.count('C')
        total = len(sequence.replace('N', ''))  # Exclude ambiguous bases
        
        if total == 0:
            return 0.0
        
        return round((gc_count / total) * 100, 2)
    
    async def _save_fasta_sequences(
        self,
        fasta_data: str,
        sequences: List[Dict],
    ) -> None:
        """Save FASTA sequences to blob storage."""
        if not self.blob_manager:
            return
        
        # Parse FASTA and match to sequence records
        current_header = None
        current_seq = []
        
        for line in fasta_data.split('\n'):
            line = line.strip()
            if line.startswith('>'):
                # Save previous sequence
                if current_header and current_seq:
                    await self._save_single_fasta(current_header, ''.join(current_seq), sequences)
                
                current_header = line[1:]  # Remove >
                current_seq = []
            elif line:
                current_seq.append(line)
        
        # Save last sequence
        if current_header and current_seq:
            await self._save_single_fasta(current_header, ''.join(current_seq), sequences)
    
    async def _save_single_fasta(
        self,
        header: str,
        sequence: str,
        sequences: List[Dict],
    ) -> None:
        """Save a single FASTA sequence."""
        # Extract accession from header
        accession_match = re.match(r'(\S+)', header)
        if not accession_match:
            return
        
        accession_part = accession_match.group(1)
        
        # Find matching sequence record
        for seq_record in sequences:
            if seq_record.get("accession") in accession_part:
                fasta_content = f">{header}\n"
                # Wrap sequence at 70 characters
                for i in range(0, len(sequence), 70):
                    fasta_content += sequence[i:i+70] + "\n"
                
                result = await self.blob_manager.download_sequence(
                    url_or_content=fasta_content,
                    accession=seq_record["accession"],
                    scientific_name=seq_record.get("scientific_name", "Unknown"),
                    gene_region=seq_record.get("gene_region"),
                    source="GenBank",
                    is_content=True,
                )
                
                if result.get("success"):
                    seq_record["blob_path"] = result.get("file_path")
                
                break
    
    async def fetch_fungal_its(
        self,
        limit: int = 1000,
        session: Optional[aiohttp.ClientSession] = None,
    ) -> List[Dict[str, Any]]:
        """
        Fetch ITS (Internal Transcribed Spacer) sequences for fungi.
        ITS is the primary barcode for fungal identification.
        """
        accessions, _ = await self.search_sequences(
            gene="ITS",
            organism="Fungi",
            min_length=400,
            max_length=1200,
            limit=limit,
            session=session,
        )
        return await self.fetch_sequences(accessions, session=session)
    
    async def fetch_species_sequences(
        self,
        species_name: str,
        gene_regions: Optional[List[str]] = None,
        limit: int = 50,
        session: Optional[aiohttp.ClientSession] = None,
    ) -> List[Dict[str, Any]]:
        """
        Fetch all sequences for a specific species.
        
        Args:
            species_name: Scientific name (e.g., "Amanita muscaria")
            gene_regions: List of gene regions to fetch (default: ITS, LSU, SSU)
            limit: Max sequences per gene region
        """
        if gene_regions is None:
            gene_regions = ["ITS", "LSU", "SSU"]
        
        close_session = False
        if session is None:
            session = aiohttp.ClientSession()
            close_session = True
        
        try:
            all_sequences = []
            
            for gene in gene_regions:
                query = f'"{species_name}"[Organism] AND ({gene}[Gene] OR {self.GENE_REGIONS.get(gene, gene)}[Title])'
                
                accessions, _ = await self.search_sequences(
                    query=query,
                    limit=limit,
                    session=session,
                )
                
                if accessions:
                    sequences = await self.fetch_sequences(accessions, session=session)
                    all_sequences.extend(sequences)
            
            return all_sequences
            
        finally:
            if close_session:
                await session.close()
    
    async def sync(
        self,
        gene_regions: Optional[List[str]] = None,
        limit_per_gene: int = 5000,
    ) -> Dict[str, int]:
        """
        Full sync of fungal sequences from GenBank.
        
        Args:
            gene_regions: Gene regions to fetch (default: ITS, LSU, SSU)
            limit_per_gene: Max sequences per gene region
        """
        if gene_regions is None:
            gene_regions = ["ITS", "LSU", "SSU", "RPB2", "TEF1"]
        
        stats = {
            "total_fetched": 0,
            "total_saved": 0,
            "by_gene": {},
        }
        
        async with aiohttp.ClientSession() as session:
            for gene in gene_regions:
                logger.info(f"Syncing {gene} sequences...")
                
                accessions, total = await self.search_sequences(
                    gene=gene,
                    limit=limit_per_gene,
                    session=session,
                )
                
                sequences = await self.fetch_sequences(
                    accessions,
                    session=session,
                    save_fasta=True,
                )
                
                stats["total_fetched"] += len(sequences)
                stats["by_gene"][gene] = {
                    "fetched": len(sequences),
                    "total_available": total,
                }
                
                # Save to database
                if self.db:
                    saved = 0
                    for seq in sequences:
                        try:
                            await self._save_sequence(seq)
                            saved += 1
                        except Exception as e:
                            logger.error(f"Error saving sequence {seq.get('accession')}: {e}")
                    
                    stats["total_saved"] += saved
                    stats["by_gene"][gene]["saved"] = saved
        
        return stats
    
    async def _save_sequence(self, seq: Dict[str, Any]) -> None:
        """Save sequence to MINDEX database."""
        if not self.db:
            return
        
        query = """
        INSERT INTO core.dna_sequences (
            scientific_name, accession, gi_number, gene_region,
            sequence_length, sequence_text, gc_content, definition,
            organism, strain, specimen_voucher, country, collection_date,
            pubmed_ids, source, source_url, metadata, created_at
        ) VALUES (
            $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, NOW()
        )
        ON CONFLICT (accession) DO UPDATE SET
            sequence_text = COALESCE(EXCLUDED.sequence_text, core.dna_sequences.sequence_text),
            gc_content = EXCLUDED.gc_content,
            metadata = core.dna_sequences.metadata || EXCLUDED.metadata,
            updated_at = NOW()
        """
        
        # Convert collection_date string to date if possible
        collection_date = None
        if seq.get("collection_date"):
            try:
                # Try various date formats
                for fmt in ["%d-%b-%Y", "%Y-%m-%d", "%Y", "%b-%Y"]:
                    try:
                        collection_date = datetime.strptime(seq["collection_date"], fmt).date()
                        break
                    except ValueError:
                        continue
            except Exception:
                pass
        
        await self.db.execute(
            query,
            seq.get("scientific_name"),
            seq.get("accession"),
            seq.get("gi_number"),
            seq.get("gene_region"),
            seq.get("sequence_length"),
            seq.get("sequence"),  # Full sequence text
            seq.get("gc_content"),
            seq.get("definition"),
            seq.get("organism"),
            seq.get("strain"),
            seq.get("specimen_voucher"),
            seq.get("country"),
            collection_date,
            seq.get("pubmed_ids", []),
            "GenBank",
            seq.get("source_url"),
            {
                "create_date": seq.get("create_date"),
                "update_date": seq.get("update_date"),
                "blob_path": seq.get("blob_path"),
            },
        )
