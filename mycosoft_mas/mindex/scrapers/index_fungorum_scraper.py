"""
Index Fungorum Scraper - Feb 5, 2026
Scrapes fungal nomenclature data from Index Fungorum.

Index Fungorum API: http://www.indexfungorum.org/ixfwebservice/fungus.asmx
Provides authoritative taxonomic and nomenclatural data for fungi.
"""

import asyncio
import logging
import re
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Any, Dict, List, Optional

import aiohttp
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class IndexFungorumScraper:
    """Scrapes fungal nomenclature data from Index Fungorum."""
    
    # Index Fungorum web service endpoints
    BASE_URL = "http://www.indexfungorum.org/ixfwebservice/fungus.asmx"
    SEARCH_URL = "http://www.indexfungorum.org/Names/Names.asp"
    
    # SOAP endpoints
    SOAP_ENDPOINTS = {
        "name_search": "/NameSearch",
        "name_by_key": "/NameByKey",
        "author_search": "/AuthorSearch",
        "epithet_search": "/EpithetSearch",
    }
    
    def __init__(self, db=None, request_delay: float = 1.0):
        """
        Initialize Index Fungorum scraper.
        
        Args:
            db: Database connection for storing results
            request_delay: Delay between requests in seconds
        """
        self.db = db
        self.request_delay = request_delay
        self.last_request_time = 0.0
    
    def _get_headers(self) -> Dict[str, str]:
        """Get headers for requests."""
        return {
            "User-Agent": "Mycosoft-MINDEX/1.0 (https://mycosoft.com; contact@mycosoft.com)",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }
    
    async def _rate_limit(self):
        """Enforce rate limiting."""
        now = asyncio.get_event_loop().time()
        elapsed = now - self.last_request_time
        if elapsed < self.request_delay:
            await asyncio.sleep(self.request_delay - elapsed)
        self.last_request_time = asyncio.get_event_loop().time()
    
    async def _fetch_page(
        self,
        session: aiohttp.ClientSession,
        url: str,
        params: Optional[Dict] = None,
        method: str = "GET",
    ) -> Optional[str]:
        """Fetch a page with rate limiting and retries."""
        await self._rate_limit()
        
        for attempt in range(3):
            try:
                if method == "GET":
                    async with session.get(
                        url,
                        params=params,
                        headers=self._get_headers(),
                        timeout=aiohttp.ClientTimeout(total=30),
                    ) as response:
                        if response.status == 200:
                            return await response.text()
                        elif response.status == 429:
                            wait_time = (2 ** attempt) * 5
                            logger.warning(f"Rate limited, waiting {wait_time}s")
                            await asyncio.sleep(wait_time)
                        else:
                            logger.warning(f"HTTP {response.status} from Index Fungorum")
                            return None
                else:
                    async with session.post(
                        url,
                        data=params,
                        headers=self._get_headers(),
                        timeout=aiohttp.ClientTimeout(total=30),
                    ) as response:
                        if response.status == 200:
                            return await response.text()
                        else:
                            logger.warning(f"HTTP {response.status} from Index Fungorum")
                            return None
            except asyncio.TimeoutError:
                logger.warning(f"Timeout on attempt {attempt + 1}")
                await asyncio.sleep(2 ** attempt)
            except aiohttp.ClientError as e:
                logger.warning(f"Client error: {e}")
                await asyncio.sleep(2 ** attempt)
        
        return None
    
    async def search_names(
        self,
        search_term: str,
        session: Optional[aiohttp.ClientSession] = None,
        max_results: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Search for fungal names.
        
        Args:
            search_term: Search term (genus, species, etc.)
            session: Optional aiohttp session
            max_results: Maximum results to return
        """
        close_session = False
        if session is None:
            session = aiohttp.ClientSession()
            close_session = True
        
        try:
            # Try web search (more reliable than SOAP)
            params = {
                "SearchTerm": search_term,
                "MaxNumber": str(max_results),
                "SearchType": "1",  # 1 = NameSearchWildcard
            }
            
            html = await self._fetch_page(session, self.SEARCH_URL, params)
            if not html:
                return []
            
            return self._parse_search_results(html)
            
        finally:
            if close_session:
                await session.close()
    
    def _parse_search_results(self, html: str) -> List[Dict[str, Any]]:
        """Parse search results from Index Fungorum HTML."""
        results = []
        
        try:
            soup = BeautifulSoup(html, "html.parser")
            
            # Find result table
            table = soup.find("table", class_=re.compile(r"results?|data|list", re.I))
            if not table:
                # Try finding by structure
                tables = soup.find_all("table")
                for t in tables:
                    if t.find("td") and len(t.find_all("tr")) > 2:
                        table = t
                        break
            
            if not table:
                logger.debug("No result table found in Index Fungorum response")
                return results
            
            rows = table.find_all("tr")[1:]  # Skip header
            
            for row in rows:
                cells = row.find_all("td")
                if len(cells) < 2:
                    continue
                
                parsed = self._parse_result_row(cells)
                if parsed:
                    results.append(parsed)
            
            # Alternative: look for links with record IDs
            if not results:
                for link in soup.find_all("a", href=re.compile(r"Names.*RecordID=\d+", re.I)):
                    match = re.search(r"RecordID=(\d+)", link.get("href", ""))
                    if match:
                        name = link.get_text(strip=True)
                        if name and self._looks_like_scientific_name(name):
                            results.append({
                                "scientific_name": name,
                                "record_id": match.group(1),
                                "source": "IndexFungorum",
                                "kingdom": "Fungi",
                            })
            
        except Exception as e:
            logger.error(f"Error parsing Index Fungorum results: {e}")
        
        return results
    
    def _parse_result_row(self, cells: List) -> Optional[Dict[str, Any]]:
        """Parse a single result row."""
        try:
            # Try to extract name (usually in italics)
            name_cell = cells[0]
            em = name_cell.find("em") or name_cell.find("i")
            if em:
                name = em.get_text(strip=True)
            else:
                name = name_cell.get_text(strip=True)
            
            if not name or not self._looks_like_scientific_name(name):
                return None
            
            # Extract record ID from link
            record_id = None
            link = name_cell.find("a", href=True)
            if link:
                match = re.search(r"RecordID=(\d+)", link.get("href", ""))
                if match:
                    record_id = match.group(1)
            
            result = {
                "scientific_name": name,
                "record_id": record_id,
                "source": "IndexFungorum",
                "kingdom": "Fungi",
            }
            
            # Try to extract author if present
            if len(cells) > 1:
                author_text = cells[1].get_text(strip=True)
                if author_text and not author_text.isdigit():
                    result["author"] = author_text
            
            # Try to extract year if present
            if len(cells) > 2:
                year_text = cells[2].get_text(strip=True)
                if year_text and year_text.isdigit() and 1700 <= int(year_text) <= 2030:
                    result["year"] = int(year_text)
            
            return result
            
        except Exception as e:
            logger.debug(f"Error parsing row: {e}")
            return None
    
    def _looks_like_scientific_name(self, text: str) -> bool:
        """Check if text looks like a scientific name."""
        if not text or len(text) < 3:
            return False
        # Should start with capital letter
        if not text[0].isupper():
            return False
        # Should contain letters
        if not any(c.isalpha() for c in text):
            return False
        # Should not be all caps
        if text.isupper():
            return False
        # Should not contain too many numbers
        if sum(c.isdigit() for c in text) > len(text) // 3:
            return False
        return True
    
    async def fetch_species_details(
        self,
        record_id: str,
        session: Optional[aiohttp.ClientSession] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch detailed information for a specific record.
        
        Args:
            record_id: Index Fungorum record ID
            session: Optional aiohttp session
        """
        close_session = False
        if session is None:
            session = aiohttp.ClientSession()
            close_session = True
        
        try:
            url = f"http://www.indexfungorum.org/names/NamesRecord.asp?RecordID={record_id}"
            html = await self._fetch_page(session, url)
            if not html:
                return None
            
            return self._parse_details_page(html, record_id)
            
        finally:
            if close_session:
                await session.close()
    
    def _parse_details_page(self, html: str, record_id: str) -> Optional[Dict[str, Any]]:
        """Parse species details page."""
        try:
            soup = BeautifulSoup(html, "html.parser")
            
            result = {
                "record_id": record_id,
                "source": "IndexFungorum",
                "kingdom": "Fungi",
            }
            
            # Extract name (usually in title or h1/h2)
            title = soup.find("title")
            if title:
                name_match = re.search(r"^([A-Z][a-z]+(?:\s+[a-z]+)*)", title.get_text(strip=True))
                if name_match:
                    result["scientific_name"] = name_match.group(1)
            
            # Look for labeled fields
            for row in soup.find_all(["tr", "div"]):
                text = row.get_text(" ", strip=True).lower()
                
                if "current name" in text:
                    val = self._extract_value(row, "Current Name")
                    if val:
                        result["current_name"] = val
                
                if "basionym" in text:
                    val = self._extract_value(row, "Basionym")
                    if val:
                        result["basionym"] = val
                
                if "author" in text:
                    val = self._extract_value(row, "Author")
                    if val:
                        result["author"] = val
                
                if "year" in text:
                    val = self._extract_value(row, "Year")
                    if val and val.isdigit():
                        result["year"] = int(val)
                
                if "rank" in text or "status" in text:
                    val = self._extract_value(row, "Rank") or self._extract_value(row, "Status")
                    if val:
                        result["rank"] = val.lower()
                
                if "family" in text:
                    val = self._extract_value(row, "Family")
                    if val:
                        result["family"] = val
                
                if "order" in text:
                    val = self._extract_value(row, "Order")
                    if val:
                        result["order"] = val
                
                if "class" in text:
                    val = self._extract_value(row, "Class")
                    if val:
                        result["class_name"] = val
                
                if "phylum" in text or "division" in text:
                    val = self._extract_value(row, "Phylum") or self._extract_value(row, "Division")
                    if val:
                        result["phylum"] = val
                
                if "publication" in text:
                    val = self._extract_value(row, "Publication")
                    if val:
                        result["publication"] = val
                
                if "typification" in text:
                    val = self._extract_value(row, "Typification")
                    if val:
                        result["type_info"] = val
            
            return result if "scientific_name" in result else None
            
        except Exception as e:
            logger.error(f"Error parsing details page: {e}")
            return None
    
    def _extract_value(self, element, label: str) -> Optional[str]:
        """Extract value after a label in an element."""
        text = element.get_text(" ", strip=True)
        pattern = rf"{label}\s*:?\s*([^:]+?)(?:\s*[A-Z][a-z]+:|$)"
        match = re.search(pattern, text, re.I)
        if match:
            return match.group(1).strip()
        return None
    
    async def fetch_genus(
        self,
        genus: str,
        session: Optional[aiohttp.ClientSession] = None,
    ) -> List[Dict[str, Any]]:
        """
        Fetch all species in a genus.
        
        Args:
            genus: Genus name
            session: Optional aiohttp session
        """
        close_session = False
        if session is None:
            session = aiohttp.ClientSession()
            close_session = True
        
        try:
            # Search for genus with wildcard
            all_species = []
            
            # First, search for exact genus matches
            results = await self.search_names(f"{genus} *", session, max_results=500)
            
            for r in results:
                name = r.get("scientific_name", "")
                if name.startswith(genus):
                    all_species.append(r)
            
            logger.info(f"Found {len(all_species)} species in genus {genus}")
            return all_species
            
        finally:
            if close_session:
                await session.close()
    
    async def sync(
        self,
        genera: Optional[List[str]] = None,
        limit: Optional[int] = None,
    ) -> Dict[str, int]:
        """
        Sync data from Index Fungorum to MINDEX.
        
        Args:
            genera: List of genera to sync (if None, sync priority genera)
            limit: Maximum species to sync
        """
        if genera is None:
            # Priority genera for mycology
            genera = [
                "Amanita", "Agaricus", "Boletus", "Cantharellus", "Cortinarius",
                "Ganoderma", "Hericium", "Lactarius", "Morchella", "Pleurotus",
                "Psilocybe", "Russula", "Trametes", "Tricholoma", "Tuber",
            ]
        
        stats = {"species_found": 0, "species_saved": 0, "errors": 0}
        
        async with aiohttp.ClientSession() as session:
            for genus in genera:
                try:
                    logger.info(f"Syncing genus: {genus}")
                    species = await self.fetch_genus(genus, session)
                    stats["species_found"] += len(species)
                    
                    for sp in species:
                        if limit and stats["species_saved"] >= limit:
                            logger.info(f"Reached limit of {limit} species")
                            return stats
                        
                        # Get details if we have a record ID
                        if sp.get("record_id"):
                            details = await self.fetch_species_details(sp["record_id"], session)
                            if details:
                                sp.update(details)
                        
                        # Save to database
                        if self.db:
                            try:
                                await self._save_species(sp)
                                stats["species_saved"] += 1
                            except Exception as e:
                                logger.error(f"Failed to save species {sp.get('scientific_name')}: {e}")
                                stats["errors"] += 1
                        else:
                            stats["species_saved"] += 1
                    
                except Exception as e:
                    logger.error(f"Error syncing genus {genus}: {e}")
                    stats["errors"] += 1
        
        return stats
    
    async def _save_species(self, species: Dict[str, Any]) -> None:
        """Save species to MINDEX database."""
        if not self.db:
            return
        
        query = """
        INSERT INTO core.taxon (
            scientific_name, kingdom, phylum, class, "order", family,
            rank, author, year, source, source_id, metadata, created_at
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, NOW())
        ON CONFLICT (source, source_id) DO UPDATE SET
            scientific_name = EXCLUDED.scientific_name,
            author = EXCLUDED.author,
            metadata = core.taxon.metadata || EXCLUDED.metadata,
            updated_at = NOW()
        """
        
        await self.db.execute(
            query,
            species.get("scientific_name"),
            species.get("kingdom", "Fungi"),
            species.get("phylum"),
            species.get("class_name"),
            species.get("order"),
            species.get("family"),
            species.get("rank", "species"),
            species.get("author"),
            species.get("year"),
            "IndexFungorum",
            species.get("record_id"),
            {
                "current_name": species.get("current_name"),
                "basionym": species.get("basionym"),
                "publication": species.get("publication"),
                "type_info": species.get("type_info"),
            },
        )
