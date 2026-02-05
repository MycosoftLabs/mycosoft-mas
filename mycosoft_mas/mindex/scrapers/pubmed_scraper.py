"""
PubMed Scraper for MINDEX - Feb 5, 2026

Fetches fungal research papers from NCBI PubMed.
Uses Entrez E-utilities API with proper rate limiting.

Features:
- Search by species, compound, or research topic
- Extract abstracts, authors, MeSH terms
- Download open access PDFs via PubMed Central
- Link papers to species/compounds in MINDEX
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
    
    def __init__(self, requests_per_second: float = 3.0, max_delay: float = 60.0):
        self.min_interval = 1.0 / requests_per_second
        self.max_delay = max_delay
        self.last_request_time = 0.0
        self.consecutive_errors = 0
    
    async def wait(self):
        now = asyncio.get_event_loop().time()
        elapsed = now - self.last_request_time
        wait_time = max(0, self.min_interval - elapsed)
        
        if self.consecutive_errors > 0:
            backoff = min(self.max_delay, 2 ** self.consecutive_errors)
            wait_time = max(wait_time, backoff)
        
        if wait_time > 0:
            await asyncio.sleep(wait_time)
        
        self.last_request_time = asyncio.get_event_loop().time()
    
    def success(self):
        self.consecutive_errors = 0
    
    def failure(self):
        self.consecutive_errors += 1


class PubMedScraper:
    """
    Scraper for PubMed fungal research literature.
    
    Fetches:
    - Research papers on fungal species
    - Mycological studies
    - Compound/metabolite research
    - Medicinal mushroom papers
    """
    
    ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
    ELINK_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/elink.fcgi"
    PMC_URL = "https://www.ncbi.nlm.nih.gov/pmc/articles"
    
    # Common fungal research topics
    RESEARCH_TOPICS = {
        "taxonomy": "taxonomy[MeSH] OR classification[MeSH]",
        "medicinal": "therapeutic use[MeSH] OR pharmacology[MeSH]",
        "ecology": "ecology[MeSH] OR environment[MeSH]",
        "genomics": "genome[MeSH] OR genomics[MeSH]",
        "metabolites": "secondary metabolites OR natural products",
        "cultivation": "cultivation OR culture techniques",
        "pathogenicity": "pathogenicity[MeSH] OR virulence[MeSH]",
        "symbiosis": "mycorrhiza OR symbiosis[MeSH]",
    }
    
    def __init__(
        self,
        db=None,
        api_key: Optional[str] = None,
        blob_manager=None,
        email: str = "contact@mycosoft.com",
    ):
        self.db = db
        self.api_key = api_key or os.environ.get("NCBI_API_KEY")
        self.blob_manager = blob_manager
        self.email = email
        
        requests_per_second = 10.0 if self.api_key else 3.0
        self.rate_limiter = RateLimiter(requests_per_second=requests_per_second)
        
        self.seen_pmids: Set[str] = set()
    
    def _get_params(self, base_params: Dict) -> Dict:
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
                        logger.warning("Rate limited by NCBI, backing off...")
                        self.rate_limiter.failure()
                        continue
                    elif response.status >= 500:
                        logger.warning(f"NCBI server error: {response.status}")
                        self.rate_limiter.failure()
                        continue
                    else:
                        logger.error(f"PubMed API error: {response.status}")
                        return None
            except asyncio.TimeoutError:
                logger.warning(f"Timeout on attempt {attempt + 1}")
                self.rate_limiter.failure()
            except aiohttp.ClientError as e:
                logger.error(f"Network error: {e}")
                self.rate_limiter.failure()
        
        return None
    
    async def search_papers(
        self,
        query: str,
        limit: int = 100,
        min_date: Optional[str] = None,
        max_date: Optional[str] = None,
        session: Optional[aiohttp.ClientSession] = None,
    ) -> Tuple[List[str], int]:
        """
        Search PubMed for papers.
        
        Returns:
            Tuple of (list of PMIDs, total count)
        """
        close_session = False
        if session is None:
            session = aiohttp.ClientSession()
            close_session = True
        
        try:
            pmids = []
            total_count = 0
            retstart = 0
            batch_size = min(limit, 10000)
            
            while len(pmids) < limit:
                params = {
                    "db": "pubmed",
                    "term": query,
                    "retmax": batch_size,
                    "retstart": retstart,
                    "retmode": "json",
                    "sort": "relevance",
                }
                
                if min_date:
                    params["mindate"] = min_date
                if max_date:
                    params["maxdate"] = max_date
                if min_date or max_date:
                    params["datetype"] = "pdat"  # Publication date
                
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
                    
                    pmids.extend(ids)
                    total_count = int(result.get("count", len(pmids)))
                    
                    if len(ids) < batch_size:
                        break
                    
                    retstart += batch_size
                    
                except Exception as e:
                    logger.error(f"Error parsing search response: {e}")
                    break
            
            logger.info(f"Found {len(pmids)} papers (total: {total_count})")
            return pmids[:limit], total_count
            
        finally:
            if close_session:
                await session.close()
    
    async def fetch_papers(
        self,
        pmids: List[str],
        batch_size: int = 100,
        session: Optional[aiohttp.ClientSession] = None,
        download_pdfs: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Fetch paper details by PMIDs.
        """
        close_session = False
        if session is None:
            session = aiohttp.ClientSession()
            close_session = True
        
        try:
            papers = []
            
            for i in range(0, len(pmids), batch_size):
                batch = pmids[i:i + batch_size]
                
                params = {
                    "db": "pubmed",
                    "id": ",".join(batch),
                    "rettype": "xml",
                    "retmode": "xml",
                }
                
                xml_data = await self._make_request(session, self.EFETCH_URL, params)
                if xml_data:
                    parsed = self._parse_pubmed_xml(xml_data)
                    papers.extend(parsed)
                
                logger.info(f"Fetched batch {i//batch_size + 1}, total: {len(papers)} papers")
            
            # Check for open access PDFs
            if download_pdfs and self.blob_manager:
                pmc_ids = await self._get_pmc_ids(pmids, session)
                await self._download_pdfs(papers, pmc_ids, session)
            
            return papers
            
        finally:
            if close_session:
                await session.close()
    
    def _parse_pubmed_xml(self, xml_data: str) -> List[Dict[str, Any]]:
        """Parse PubMed XML response."""
        papers = []
        
        try:
            root = ET.fromstring(xml_data)
            
            for article in root.findall(".//PubmedArticle"):
                try:
                    medline = article.find("MedlineCitation")
                    if medline is None:
                        continue
                    
                    pmid = medline.findtext("PMID")
                    if pmid in self.seen_pmids:
                        continue
                    self.seen_pmids.add(pmid)
                    
                    article_data = medline.find("Article")
                    if article_data is None:
                        continue
                    
                    # Title
                    title = article_data.findtext("ArticleTitle") or ""
                    
                    # Abstract
                    abstract_parts = []
                    for abs_text in article_data.findall(".//AbstractText"):
                        label = abs_text.get("Label", "")
                        text = "".join(abs_text.itertext())
                        if label:
                            abstract_parts.append(f"{label}: {text}")
                        else:
                            abstract_parts.append(text)
                    abstract = " ".join(abstract_parts)
                    
                    # Authors
                    authors = []
                    for author in article_data.findall(".//Author"):
                        last_name = author.findtext("LastName") or ""
                        fore_name = author.findtext("ForeName") or ""
                        affiliation = author.findtext(".//Affiliation") or ""
                        identifier = author.findtext(".//Identifier") or None
                        
                        if last_name or fore_name:
                            authors.append({
                                "name": f"{fore_name} {last_name}".strip(),
                                "affiliation": affiliation,
                                "orcid": identifier if identifier and "orcid" in str(identifier).lower() else None,
                            })
                    
                    # Journal info
                    journal = article_data.find("Journal")
                    journal_title = journal.findtext("Title") if journal else None
                    journal_abbrev = journal.findtext("ISOAbbreviation") if journal else None
                    
                    # Volume, issue, pages
                    volume = journal.findtext(".//Volume") if journal else None
                    issue = journal.findtext(".//Issue") if journal else None
                    pages = article_data.findtext(".//MedlinePgn")
                    
                    # Publication date
                    pub_date = journal.find(".//PubDate") if journal else None
                    year = int(pub_date.findtext("Year")) if pub_date and pub_date.findtext("Year") else None
                    month = pub_date.findtext("Month") if pub_date else None
                    day = pub_date.findtext("Day") if pub_date else None
                    
                    publication_date = None
                    if year:
                        try:
                            if month and day:
                                # Convert month name to number if needed
                                month_num = self._month_to_num(month)
                                publication_date = f"{year}-{month_num:02d}-{int(day):02d}"
                            elif month:
                                month_num = self._month_to_num(month)
                                publication_date = f"{year}-{month_num:02d}-01"
                            else:
                                publication_date = f"{year}-01-01"
                        except (ValueError, TypeError):
                            pass
                    
                    # DOI and PMC ID
                    doi = None
                    pmc_id = None
                    for article_id in article.findall(".//ArticleId"):
                        id_type = article_id.get("IdType")
                        if id_type == "doi":
                            doi = article_id.text
                        elif id_type == "pmc":
                            pmc_id = article_id.text
                    
                    # MeSH terms
                    mesh_terms = []
                    for mesh in medline.findall(".//MeshHeading"):
                        descriptor = mesh.findtext("DescriptorName")
                        if descriptor:
                            mesh_terms.append(descriptor)
                    
                    # Keywords
                    keywords = []
                    for keyword in medline.findall(".//Keyword"):
                        if keyword.text:
                            keywords.append(keyword.text)
                    
                    # Extract related species from title/abstract
                    related_species = self._extract_species_names(title + " " + abstract)
                    
                    paper = {
                        "pmid": pmid,
                        "pmc_id": pmc_id,
                        "doi": doi,
                        "title": title,
                        "abstract": abstract,
                        "authors": authors,
                        "journal": journal_title,
                        "journal_abbrev": journal_abbrev,
                        "volume": volume,
                        "issue": issue,
                        "pages": pages,
                        "year": year,
                        "publication_date": publication_date,
                        "mesh_terms": mesh_terms,
                        "keywords": keywords,
                        "related_species": related_species,
                        "is_open_access": pmc_id is not None,
                        "source": "PubMed",
                        "source_url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                    }
                    
                    papers.append(paper)
                    
                except Exception as e:
                    logger.debug(f"Error parsing article: {e}")
                    
        except ET.ParseError as e:
            logger.error(f"Error parsing PubMed XML: {e}")
        
        return papers
    
    def _month_to_num(self, month: str) -> int:
        """Convert month name or number string to integer."""
        if month.isdigit():
            return int(month)
        
        months = {
            "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
            "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
        }
        return months.get(month[:3].lower(), 1)
    
    def _extract_species_names(self, text: str) -> List[str]:
        """Extract fungal species names from text."""
        species = []
        
        # Pattern for genus species (capitalized genus, lowercase species)
        pattern = r'\b([A-Z][a-z]+)\s+([a-z]{2,})\b'
        
        for match in re.finditer(pattern, text):
            genus, species_name = match.groups()
            
            # Filter out common false positives
            if genus.lower() in {"the", "this", "that", "with", "from", "were", "been", "have"}:
                continue
            
            full_name = f"{genus} {species_name}"
            if full_name not in species:
                species.append(full_name)
        
        return species
    
    async def _get_pmc_ids(
        self,
        pmids: List[str],
        session: aiohttp.ClientSession,
    ) -> Dict[str, str]:
        """Get PMC IDs for PMIDs (for open access papers)."""
        pmc_map = {}
        
        for i in range(0, len(pmids), 100):
            batch = pmids[i:i + 100]
            
            params = {
                "dbfrom": "pubmed",
                "db": "pmc",
                "id": ",".join(batch),
                "retmode": "json",
            }
            
            response = await self._make_request(session, self.ELINK_URL, params)
            if response:
                try:
                    import json
                    data = json.loads(response)
                    
                    for linkset in data.get("linksets", []):
                        pmid = str(linkset.get("ids", [None])[0])
                        for link in linkset.get("linksetdbs", []):
                            if link.get("dbto") == "pmc":
                                pmc_ids = link.get("links", [])
                                if pmc_ids:
                                    pmc_map[pmid] = f"PMC{pmc_ids[0]}"
                except Exception as e:
                    logger.debug(f"Error parsing PMC link response: {e}")
        
        return pmc_map
    
    async def _download_pdfs(
        self,
        papers: List[Dict],
        pmc_map: Dict[str, str],
        session: aiohttp.ClientSession,
    ) -> None:
        """Download open access PDFs from PMC."""
        if not self.blob_manager:
            return
        
        for paper in papers:
            pmid = paper.get("pmid")
            pmc_id = pmc_map.get(pmid) or paper.get("pmc_id")
            
            if not pmc_id:
                continue
            
            # Try to get PDF URL from PMC
            pdf_url = f"https://www.ncbi.nlm.nih.gov/pmc/articles/{pmc_id}/pdf/"
            
            try:
                result = await self.blob_manager.download_paper(
                    url=pdf_url,
                    pmid=pmid,
                    doi=paper.get("doi"),
                    title=paper.get("title"),
                )
                
                if result.get("success"):
                    paper["pdf_path"] = result.get("file_path")
                    paper["pdf_blob_id"] = result.get("blob_id")
                    logger.info(f"Downloaded PDF for PMID {pmid}")
            except Exception as e:
                logger.debug(f"Could not download PDF for {pmc_id}: {e}")
    
    async def search_fungal_papers(
        self,
        species_name: Optional[str] = None,
        topic: Optional[str] = None,
        years: int = 10,
        limit: int = 100,
        session: Optional[aiohttp.ClientSession] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search for fungal research papers.
        
        Args:
            species_name: Specific species to search for
            topic: Research topic (see RESEARCH_TOPICS)
            years: How many years back to search
            limit: Max papers to return
        """
        # Build query
        query_parts = ["Fungi[MeSH]"]
        
        if species_name:
            query_parts.append(f'"{species_name}"[Title/Abstract]')
        
        if topic and topic in self.RESEARCH_TOPICS:
            query_parts.append(f"({self.RESEARCH_TOPICS[topic]})")
        elif topic:
            query_parts.append(f"({topic})")
        
        query = " AND ".join(query_parts)
        
        # Date range
        max_date = datetime.now().strftime("%Y/%m/%d")
        min_year = datetime.now().year - years
        min_date = f"{min_year}/01/01"
        
        pmids, _ = await self.search_papers(
            query=query,
            limit=limit,
            min_date=min_date,
            max_date=max_date,
            session=session,
        )
        
        return await self.fetch_papers(pmids, session=session)
    
    async def sync(
        self,
        species_list: Optional[List[str]] = None,
        topics: Optional[List[str]] = None,
        papers_per_species: int = 50,
        papers_per_topic: int = 200,
        years: int = 5,
    ) -> Dict[str, int]:
        """
        Sync fungal research papers to MINDEX.
        
        Args:
            species_list: List of species to search for
            topics: List of research topics
            papers_per_species: Max papers per species
            papers_per_topic: Max papers per topic
            years: Years back to search
        """
        if species_list is None:
            species_list = [
                "Amanita muscaria", "Psilocybe cubensis", "Ganoderma lucidum",
                "Hericium erinaceus", "Cordyceps militaris", "Trametes versicolor",
            ]
        
        if topics is None:
            topics = ["medicinal", "taxonomy", "metabolites", "genomics"]
        
        stats = {
            "total_fetched": 0,
            "total_saved": 0,
            "by_species": {},
            "by_topic": {},
        }
        
        async with aiohttp.ClientSession() as session:
            # Fetch papers for each species
            for species in species_list:
                logger.info(f"Fetching papers for {species}...")
                
                papers = await self.search_fungal_papers(
                    species_name=species,
                    years=years,
                    limit=papers_per_species,
                    session=session,
                )
                
                stats["total_fetched"] += len(papers)
                stats["by_species"][species] = len(papers)
                
                if self.db:
                    for paper in papers:
                        try:
                            await self._save_paper(paper)
                            stats["total_saved"] += 1
                        except Exception as e:
                            logger.error(f"Error saving paper: {e}")
            
            # Fetch papers for each topic
            for topic in topics:
                logger.info(f"Fetching papers for topic: {topic}...")
                
                papers = await self.search_fungal_papers(
                    topic=topic,
                    years=years,
                    limit=papers_per_topic,
                    session=session,
                )
                
                stats["total_fetched"] += len(papers)
                stats["by_topic"][topic] = len(papers)
                
                if self.db:
                    for paper in papers:
                        try:
                            await self._save_paper(paper)
                            stats["total_saved"] += 1
                        except Exception as e:
                            logger.error(f"Error saving paper: {e}")
        
        return stats
    
    async def _save_paper(self, paper: Dict[str, Any]) -> None:
        """Save paper to MINDEX database."""
        if not self.db:
            return
        
        query = """
        INSERT INTO core.research_papers (
            pmid, pmc_id, doi, title, authors, journal, journal_abbrev,
            volume, issue, pages, year, publication_date, abstract,
            keywords, mesh_terms, related_species, is_open_access,
            source, source_url, metadata, created_at
        ) VALUES (
            $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12,
            $13, $14, $15, $16, $17, $18, $19, $20, NOW()
        )
        ON CONFLICT (doi) DO UPDATE SET
            pmid = COALESCE(EXCLUDED.pmid, core.research_papers.pmid),
            pmc_id = COALESCE(EXCLUDED.pmc_id, core.research_papers.pmc_id),
            citation_count = GREATEST(core.research_papers.citation_count, 0),
            updated_at = NOW()
        WHERE EXCLUDED.doi IS NOT NULL
        """
        
        import json
        
        # Parse publication date
        pub_date = None
        if paper.get("publication_date"):
            try:
                pub_date = datetime.strptime(paper["publication_date"], "%Y-%m-%d").date()
            except (ValueError, TypeError):
                pass
        
        await self.db.execute(
            query,
            paper.get("pmid"),
            paper.get("pmc_id"),
            paper.get("doi"),
            paper.get("title"),
            json.dumps(paper.get("authors", [])),  # JSONB
            paper.get("journal"),
            paper.get("journal_abbrev"),
            paper.get("volume"),
            paper.get("issue"),
            paper.get("pages"),
            paper.get("year"),
            pub_date,
            paper.get("abstract"),
            paper.get("keywords", []),
            paper.get("mesh_terms", []),
            paper.get("related_species", []),
            paper.get("is_open_access", False),
            "PubMed",
            paper.get("source_url"),
            {
                "pdf_path": paper.get("pdf_path"),
                "pdf_blob_id": paper.get("pdf_blob_id"),
            },
        )
