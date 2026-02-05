"""
MycoBank Scraper for MINDEX - Feb 5, 2026

Fetches taxonomic nomenclature data from MycoBank.
https://www.mycobank.org/

Features:
- Web scraping fallback (API often returns empty)
- Multiple page parsing strategies
- Rate limiting with exponential backoff
- Bulk data dump support
"""

import asyncio
import logging
import os
import re
import json
from datetime import datetime
from typing import Dict, Any, List, Optional, Set
import aiohttp
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class MycoBankScraper:
    """
    Scraper for MycoBank fungal nomenclature data.
    
    Fetches:
    - Species names with authors
    - Type specimens
    - Basionyms and synonyms
    - Nomenclatural status
    - Full taxonomy
    
    Uses web scraping as primary method since API often returns empty responses.
    """
    
    BASE_URL = "https://www.mycobank.org"
    SEARCH_URL = "https://www.mycobank.org/page/Simple%20names%20search"
    NAME_DETAILS_URL = "https://www.mycobank.org/page/Name%20details%20page"
    
    # Alternative API endpoints to try
    API_ENDPOINTS = [
        "https://www.mycobank.org/Services/Generic/SearchService.aspx",
        "https://www.mycobank.org/Services/Generic/Help.aspx",
        "https://www.mycobank.org/BioloMICS.aspx",
    ]
    
    def __init__(self, db=None, cache_dir: Optional[str] = None):
        self.db = db
        self.session: Optional[aiohttp.ClientSession] = None
        self.cache_dir = cache_dir or os.environ.get("MYCOBANK_CACHE_DIR")
        self.seen_ids: Set[str] = set()
        self.request_delay = 1.5  # Seconds between requests
        self.max_retries = 3
    
    def _get_headers(self) -> Dict[str, str]:
        """Get request headers to mimic browser."""
        return {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(headers=self._get_headers())
        return self
    
    async def __aexit__(self, *args):
        if self.session:
            await self.session.close()
    
    async def _fetch_with_retry(
        self,
        session: aiohttp.ClientSession,
        url: str,
        params: Optional[Dict] = None,
    ) -> Optional[str]:
        """Fetch URL with retry logic."""
        for attempt in range(self.max_retries):
            try:
                await asyncio.sleep(self.request_delay)
                
                async with session.get(
                    url,
                    params=params,
                    headers=self._get_headers(),
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                        return await response.text()
                    elif response.status == 429:
                        # Rate limited - back off
                        wait_time = (2 ** attempt) * 5
                        logger.warning(f"Rate limited, waiting {wait_time}s")
                        await asyncio.sleep(wait_time)
                    elif response.status >= 500:
                        # Server error - retry
                        await asyncio.sleep(2 ** attempt)
                    else:
                        logger.warning(f"MycoBank returned status {response.status}")
                        return None
                        
            except asyncio.TimeoutError:
                logger.warning(f"Timeout on attempt {attempt + 1}")
            except aiohttp.ClientError as e:
                logger.warning(f"Client error: {e}")
        
        return None
    
    async def fetch_species(
        self,
        search_term: str = None,
        limit: int = 10000,
        start_letter: str = None,
        genus_list: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Fetch species from MycoBank using web scraping.
        
        Args:
            search_term: Specific search term
            limit: Maximum species to fetch
            start_letter: Starting letter for alphabetic scraping
            genus_list: Optional list of genera to scrape
        """
        species = []
        
        # Determine search strategy
        if genus_list:
            search_terms = genus_list
        elif search_term:
            search_terms = [search_term]
        elif start_letter:
            search_terms = [start_letter]
        else:
            # Common fungal genera to start with
            search_terms = [
                "Amanita", "Boletus", "Cantharellus", "Russula", "Lactarius",
                "Agaricus", "Pleurotus", "Coprinus", "Mycena", "Cortinarius",
                "Trametes", "Ganoderma", "Psilocybe", "Morchella", "Tuber",
                "Tricholoma", "Hygrophorus", "Clitocybe", "Armillaria", "Marasmius",
                "Inocybe", "Entoloma", "Lepiota", "Suillus", "Leccinum",
                "Hericium", "Hydnum", "Craterellus", "Gomphus", "Ramaria",
                "Clavaria", "Auricularia", "Tremella", "Phallus", "Clathrus",
            ]
        
        async with aiohttp.ClientSession() as session:
            for term in search_terms:
                if len(species) >= limit:
                    break
                
                logger.info(f"Scraping MycoBank for: {term}")
                
                try:
                    # Try multiple pages per search term
                    page = 1
                    term_species = []
                    
                    while len(term_species) < 500 and page <= 10:  # Max 10 pages per term
                        html = await self._fetch_search_page(session, term, page)
                        
                        if not html:
                            break
                        
                        parsed = self._parse_search_results(html)
                        
                        if not parsed:
                            break
                        
                        # Filter duplicates
                        for s in parsed:
                            mb_id = s.get("external_ids", {}).get("mycobank")
                            if mb_id and mb_id not in self.seen_ids:
                                self.seen_ids.add(mb_id)
                                term_species.append(s)
                                species.append(s)
                                
                                if len(species) >= limit:
                                    break
                        
                        if len(parsed) < 20:  # Less than full page = no more results
                            break
                        
                        page += 1
                    
                    logger.info(f"Found {len(term_species)} species for '{term}' (total: {len(species)})")
                    
                except Exception as e:
                    logger.error(f"Error fetching MycoBank for '{term}': {e}")
                    continue
        
        return species
    
    async def _fetch_search_page(
        self,
        session: aiohttp.ClientSession,
        search_term: str,
        page: int = 1,
    ) -> Optional[str]:
        """Fetch a search results page."""
        # Try the BioloMICS search interface
        url = f"{self.BASE_URL}/BioloMICS.aspx"
        params = {
            "Table": "Mycobank",
            "Name": search_term,
            "ExactName": "T",
            "Page": page,
        }
        
        html = await self._fetch_with_retry(session, url, params)
        
        if html and "No results found" not in html:
            return html
        
        # Fallback to simple search
        params = {
            "SearchText": search_term,
            "page": page,
        }
        
        return await self._fetch_with_retry(session, self.SEARCH_URL, params)
    
    async def fetch_species_details(
        self,
        mycobank_id: str,
        session: Optional[aiohttp.ClientSession] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch detailed species information by MycoBank ID.
        """
        own_session = session is None
        if own_session:
            session = aiohttp.ClientSession()
        
        try:
            url = f"{self.NAME_DETAILS_URL}/{mycobank_id}"
            html = await self._fetch_with_retry(session, url)
            
            if html:
                return self._parse_details_page(html, mycobank_id)
            return None
            
        finally:
            if own_session:
                await session.close()
    
    def _parse_search_results(self, html: str) -> List[Dict[str, Any]]:
        """Parse search results page with multiple strategies."""
        species = []
        
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Strategy 1: Look for result table rows
            for row in soup.find_all('tr', class_=re.compile(r'(searchresult|record|data)')):
                parsed = self._parse_result_row(row)
                if parsed:
                    species.append(parsed)
            
            # Strategy 2: Look for linked scientific names
            if not species:
                for link in soup.find_all('a', href=re.compile(r'/page/Name.*details.*page/\d+')):
                    parsed = self._parse_name_link(link)
                    if parsed:
                        species.append(parsed)
            
            # Strategy 3: Look for italicized names (scientific names)
            if not species:
                for em in soup.find_all(['em', 'i']):
                    text = em.get_text(strip=True)
                    if self._looks_like_species_name(text):
                        # Try to find associated link
                        parent = em.find_parent('a') or em.find_parent('td')
                        if parent:
                            mb_link = parent.find('a', href=re.compile(r'\d+'))
                            mb_id = None
                            if mb_link:
                                match = re.search(r'(\d+)', mb_link.get('href', ''))
                                mb_id = match.group(1) if match else None
                            
                            species.append({
                                "scientific_name": text,
                                "kingdom": "Fungi",
                                "source": "MycoBank",
                                "external_ids": {"mycobank": mb_id} if mb_id else {},
                            })
                    
        except Exception as e:
            logger.error(f"Error parsing MycoBank HTML: {e}")
        
        return species
    
    def _parse_result_row(self, row) -> Optional[Dict[str, Any]]:
        """Parse a single result row."""
        try:
            cells = row.find_all('td')
            if not cells:
                return None
            
            # Look for scientific name in first few cells
            for cell in cells[:3]:
                name_elem = cell.find(['em', 'i', 'a'])
                if name_elem:
                    name = name_elem.get_text(strip=True)
                    if self._looks_like_species_name(name):
                        # Find MycoBank ID
                        link = cell.find('a', href=re.compile(r'\d+'))
                        mb_id = None
                        if link:
                            match = re.search(r'(\d+)', link.get('href', ''))
                            mb_id = match.group(1) if match else None
                        
                        # Look for author in adjacent cell or text
                        author = ""
                        for sibling in cells:
                            text = sibling.get_text(strip=True)
                            if re.match(r'^[A-Z][a-z]+\.?\s', text):
                                author = text
                                break
                        
                        # Parse genus from name
                        parts = name.split()
                        genus = parts[0] if parts else None
                        
                        return {
                            "scientific_name": name,
                            "author": author,
                            "genus": genus,
                            "kingdom": "Fungi",
                            "source": "MycoBank",
                            "external_ids": {"mycobank": mb_id} if mb_id else {},
                        }
            
            return None
            
        except Exception as e:
            logger.debug(f"Error parsing row: {e}")
            return None
    
    def _parse_name_link(self, link) -> Optional[Dict[str, Any]]:
        """Parse a name link element."""
        try:
            name = link.get_text(strip=True)
            href = link.get('href', '')
            
            if not self._looks_like_species_name(name):
                return None
            
            match = re.search(r'(\d+)', href)
            mb_id = match.group(1) if match else None
            
            parts = name.split()
            
            return {
                "scientific_name": name,
                "genus": parts[0] if parts else None,
                "kingdom": "Fungi",
                "source": "MycoBank",
                "external_ids": {"mycobank": mb_id} if mb_id else {},
            }
            
        except Exception as e:
            logger.debug(f"Error parsing link: {e}")
            return None
    
    def _looks_like_species_name(self, text: str) -> bool:
        """Check if text looks like a valid species name."""
        if not text or len(text) < 5:
            return False
        
        # Should start with capital letter
        if not text[0].isupper():
            return False
        
        # Should have at least genus + epithet
        parts = text.split()
        if len(parts) < 2:
            return False
        
        # Genus should be capitalized, epithet lowercase
        if not parts[0][0].isupper():
            return False
        
        # Avoid common non-name patterns
        skip_patterns = ['Search', 'Results', 'Page', 'Click', 'View', 'Details']
        if any(p in text for p in skip_patterns):
            return False
        
        return True
    
    def _parse_details_page(self, html: str, mycobank_id: str) -> Optional[Dict[str, Any]]:
        """Parse species details page."""
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            data = {
                "source": "MycoBank",
                "external_ids": {"mycobank": mycobank_id},
                "kingdom": "Fungi",
            }
            
            # Find scientific name (usually in h1 or prominent element)
            for selector in ['h1', '.scientificname', '.name', 'title']:
                elem = soup.find(selector)
                if elem:
                    name = elem.get_text(strip=True)
                    if self._looks_like_species_name(name):
                        data["scientific_name"] = name
                        break
            
            # Parse taxonomy from any table
            for table in soup.find_all('table'):
                for row in table.find_all('tr'):
                    cells = row.find_all(['td', 'th'])
                    if len(cells) >= 2:
                        label = cells[0].get_text(strip=True).lower()
                        value = cells[1].get_text(strip=True)
                        
                        if "kingdom" in label:
                            data["kingdom"] = value
                        elif "phylum" in label or "division" in label:
                            data["phylum"] = value
                        elif "class" in label:
                            data["class_name"] = value
                        elif "order" in label:
                            data["order_name"] = value
                        elif "family" in label:
                            data["family"] = value
                        elif "genus" in label:
                            data["genus"] = value
                        elif "author" in label:
                            data["author"] = value
                        elif "basionym" in label:
                            data["basionym"] = value
                        elif "type" in label and "specimen" in label:
                            data["type_specimen"] = value
                        elif "status" in label:
                            data["nomenclatural_status"] = value
            
            return data if data.get("scientific_name") else None
            
        except Exception as e:
            logger.error(f"Error parsing MycoBank details: {e}")
            return None
    
    async def load_from_dump(self, dump_path: str) -> List[Dict[str, Any]]:
        """
        Load species from a MycoBank data dump file.
        
        Args:
            dump_path: Path to JSON or CSV dump file
        """
        species = []
        
        try:
            if dump_path.endswith('.json'):
                with open(dump_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        species = data
                    elif isinstance(data, dict) and 'species' in data:
                        species = data['species']
            
            elif dump_path.endswith('.csv'):
                import csv
                with open(dump_path, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        species.append({
                            "scientific_name": row.get('name') or row.get('scientific_name'),
                            "author": row.get('author'),
                            "kingdom": "Fungi",
                            "source": "MycoBank",
                            "external_ids": {"mycobank": row.get('id') or row.get('mycobank_id')},
                        })
            
            logger.info(f"Loaded {len(species)} species from dump: {dump_path}")
            
        except Exception as e:
            logger.error(f"Error loading dump file: {e}")
        
        return species
    
    async def sync(
        self,
        limit: int = 10000,
        dump_path: Optional[str] = None,
        genera: Optional[List[str]] = None,
    ) -> Dict[str, int]:
        """
        Full sync from MycoBank.
        
        Args:
            limit: Maximum species to fetch
            dump_path: Optional path to data dump file
            genera: Optional list of genera to scrape
        """
        stats = {
            "species_fetched": 0,
            "species_inserted": 0,
            "errors": 0,
        }
        
        # Try dump file first if provided
        if dump_path and os.path.exists(dump_path):
            species = await self.load_from_dump(dump_path)
            stats["species_fetched"] = len(species)
        else:
            # Fall back to web scraping
            species = await self.fetch_species(limit=limit, genus_list=genera)
            stats["species_fetched"] = len(species)
        
        if self.db:
            for s in species:
                try:
                    self.db.insert_species(s)
                    stats["species_inserted"] += 1
                except Exception as e:
                    logger.error(f"Error inserting species: {e}")
                    stats["errors"] += 1
        
        logger.info(f"MycoBank sync complete: {stats}")
        return stats


# CLI entry point
if __name__ == "__main__":
    import sys
    
    async def main():
        scraper = MycoBankScraper()
        
        if len(sys.argv) > 1:
            search_term = sys.argv[1]
            species = await scraper.fetch_species(search_term=search_term, limit=20)
        else:
            species = await scraper.fetch_species(limit=50)
        
        print(f"Found {len(species)} species")
        for s in species[:10]:
            print(f"  - {s['scientific_name']} (MB: {s.get('external_ids', {}).get('mycobank', 'N/A')})")
    
    asyncio.run(main())
