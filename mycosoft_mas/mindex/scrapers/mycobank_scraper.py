"""
MycoBank Scraper for MINDEX

Fetches taxonomic nomenclature data from MycoBank.
https://www.mycobank.org/
"""

import asyncio
import logging
import re
from datetime import datetime
from typing import Dict, Any, List, Optional
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
    """
    
    BASE_URL = "https://www.mycobank.org"
    SEARCH_URL = "https://www.mycobank.org/page/Simple%20names%20search"
    API_URL = "https://www.mycobank.org/Services/Generic/Help.aspx"
    
    def __init__(self, db=None):
        self.db = db
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def fetch_species(
        self,
        search_term: str = None,
        limit: int = 1000,
        start_letter: str = None,
    ) -> List[Dict[str, Any]]:
        """
        Fetch species from MycoBank.
        """
        species = []
        
        # If no search term, iterate through alphabet
        if not search_term and start_letter:
            search_terms = [start_letter]
        elif not search_term:
            search_terms = list("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
        else:
            search_terms = [search_term]
        
        async with aiohttp.ClientSession() as session:
            for term in search_terms:
                if len(species) >= limit:
                    break
                
                try:
                    # Use the simple search endpoint
                    params = {
                        "SearchText": term,
                        "page": 1,
                    }
                    
                    async with session.get(
                        self.SEARCH_URL,
                        params=params,
                    ) as response:
                        if response.status != 200:
                            continue
                        
                        html = await response.text()
                        parsed = self._parse_search_results(html)
                        
                        for s in parsed:
                            if len(species) >= limit:
                                break
                            species.append(s)
                        
                        logger.info(f"Fetched {len(species)} species from MycoBank")
                        await asyncio.sleep(1)  # Be respectful to the server
                        
                except Exception as e:
                    logger.error(f"Error fetching from MycoBank: {e}")
        
        return species
    
    async def fetch_species_details(self, mycobank_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch detailed species information by MycoBank ID.
        """
        async with aiohttp.ClientSession() as session:
            try:
                url = f"{self.BASE_URL}/page/Name%20details%20page/{mycobank_id}"
                
                async with session.get(url) as response:
                    if response.status != 200:
                        return None
                    
                    html = await response.text()
                    return self._parse_details_page(html, mycobank_id)
                    
            except Exception as e:
                logger.error(f"Error fetching MycoBank details: {e}")
                return None
    
    def _parse_search_results(self, html: str) -> List[Dict[str, Any]]:
        """Parse search results page."""
        species = []
        
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Find results table
            results = soup.find_all('div', class_='searchresult')
            
            for result in results:
                try:
                    name_elem = result.find('a', class_='scientificname')
                    author_elem = result.find('span', class_='author')
                    
                    if name_elem:
                        scientific_name = name_elem.get_text(strip=True)
                        author = author_elem.get_text(strip=True) if author_elem else ""
                        
                        # Extract MycoBank ID from link
                        href = name_elem.get('href', '')
                        mb_id = re.search(r'/(\d+)$', href)
                        mycobank_id = mb_id.group(1) if mb_id else None
                        
                        # Parse year from author string
                        year_match = re.search(r'\(?\b(1[789]\d{2}|20[0-2]\d)\b\)?', author)
                        year = int(year_match.group(1)) if year_match else None
                        
                        # Extract genus from name
                        parts = scientific_name.split()
                        genus = parts[0] if parts else None
                        
                        species.append({
                            "scientific_name": scientific_name,
                            "author": author,
                            "year_described": year,
                            "genus": genus,
                            "kingdom": "Fungi",
                            "source": "MycoBank",
                            "external_ids": {"mycobank": mycobank_id} if mycobank_id else {},
                        })
                        
                except Exception as e:
                    logger.debug(f"Error parsing search result: {e}")
                    
        except Exception as e:
            logger.error(f"Error parsing MycoBank HTML: {e}")
        
        return species
    
    def _parse_details_page(self, html: str, mycobank_id: str) -> Optional[Dict[str, Any]]:
        """Parse species details page."""
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            data = {
                "source": "MycoBank",
                "external_ids": {"mycobank": mycobank_id},
            }
            
            # Find scientific name
            name_elem = soup.find('h1', class_='scientificname')
            if name_elem:
                data["scientific_name"] = name_elem.get_text(strip=True)
            
            # Find taxonomy table
            taxonomy_table = soup.find('table', class_='taxonomy')
            if taxonomy_table:
                for row in taxonomy_table.find_all('tr'):
                    cells = row.find_all('td')
                    if len(cells) >= 2:
                        rank = cells[0].get_text(strip=True).lower()
                        value = cells[1].get_text(strip=True)
                        
                        if rank == "kingdom":
                            data["kingdom"] = value
                        elif rank == "phylum":
                            data["phylum"] = value
                        elif rank == "class":
                            data["class_name"] = value
                        elif rank == "order":
                            data["order_name"] = value
                        elif rank == "family":
                            data["family"] = value
                        elif rank == "genus":
                            data["genus"] = value
            
            # Find type specimen
            type_elem = soup.find('span', class_='typespecimen')
            if type_elem:
                data["type_specimen"] = type_elem.get_text(strip=True)
            
            # Find basionym
            basionym_elem = soup.find('span', class_='basionym')
            if basionym_elem:
                data["basionym"] = basionym_elem.get_text(strip=True)
            
            return data if data.get("scientific_name") else None
            
        except Exception as e:
            logger.error(f"Error parsing MycoBank details: {e}")
            return None
    
    async def sync(self, limit: int = 1000) -> Dict[str, int]:
        """
        Full sync from MycoBank.
        """
        stats = {
            "species_fetched": 0,
            "species_inserted": 0,
        }
        
        species = await self.fetch_species(limit=limit)
        stats["species_fetched"] = len(species)
        
        if self.db:
            for s in species:
                try:
                    self.db.insert_species(s)
                    stats["species_inserted"] += 1
                except Exception as e:
                    logger.error(f"Error inserting species: {e}")
        
        return stats

