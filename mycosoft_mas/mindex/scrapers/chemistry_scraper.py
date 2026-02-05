"""
Chemistry Scraper for MINDEX - Feb 5, 2026

Fetches fungal compound/metabolite data from PubChem and ChEMBL.
Includes bioactivity, toxicity, and structural information.

Data sources:
- PubChem: Chemical structures, properties, bioassays
- ChEMBL: Drug-like compounds, bioactivity data
"""

import asyncio
import logging
import os
import re
from typing import Any, Dict, List, Optional, Set, Tuple

import aiohttp

logger = logging.getLogger(__name__)


class RateLimiter:
    """Rate limiter with exponential backoff."""
    
    def __init__(self, requests_per_second: float = 5.0, max_delay: float = 60.0):
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


class ChemistryScraper:
    """
    Scraper for fungal compound/metabolite data.
    
    Fetches:
    - Compound structures (SMILES, InChI)
    - Physical/chemical properties
    - Bioactivity data
    - Toxicity information
    - Producing organisms
    """
    
    # PubChem REST API
    PUBCHEM_BASE = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"
    PUBCHEM_VIEW = "https://pubchem.ncbi.nlm.nih.gov/rest/pug_view"
    
    # ChEMBL REST API
    CHEMBL_BASE = "https://www.ebi.ac.uk/chembl/api/data"
    
    # Common fungal compound classes
    COMPOUND_CLASSES = [
        "alkaloid", "terpene", "sesquiterpene", "diterpene", "triterpene",
        "polyketide", "peptide", "cyclopeptide", "indole", "psilocin",
        "psilocybin", "muscarine", "amatoxin", "phallotoxin", "ergot",
        "beta-glucan", "polysaccharide", "sterol", "anthraquinone",
    ]
    
    # Priority fungal compounds to fetch
    PRIORITY_COMPOUNDS = [
        "psilocybin", "psilocin", "muscimol", "ibotenic acid",
        "amatoxin", "phalloidin", "coprine", "orellanine",
        "ergotamine", "lysergic acid", "muscarine",
        "ganodermic acid", "hericenone", "erinacine",
        "cordycepin", "ergosterol", "lentinan",
    ]
    
    def __init__(self, db=None, blob_manager=None):
        self.db = db
        self.blob_manager = blob_manager
        self.pubchem_limiter = RateLimiter(requests_per_second=5.0)
        self.chembl_limiter = RateLimiter(requests_per_second=3.0)
        self.seen_cids: Set[int] = set()
        self.seen_chembl_ids: Set[str] = set()
    
    async def _make_pubchem_request(
        self,
        session: aiohttp.ClientSession,
        endpoint: str,
        max_retries: int = 3,
    ) -> Optional[Dict]:
        """Make request to PubChem API."""
        url = f"{self.PUBCHEM_BASE}/{endpoint}"
        
        for attempt in range(max_retries):
            await self.pubchem_limiter.wait()
            
            try:
                async with session.get(
                    url,
                    timeout=aiohttp.ClientTimeout(total=30),
                ) as response:
                    if response.status == 200:
                        self.pubchem_limiter.success()
                        return await response.json()
                    elif response.status == 404:
                        return None  # Not found is not an error
                    elif response.status == 429 or response.status == 503:
                        logger.warning(f"PubChem rate limited, backing off...")
                        self.pubchem_limiter.failure()
                        continue
                    else:
                        logger.warning(f"PubChem error: {response.status}")
                        return None
            except asyncio.TimeoutError:
                logger.warning(f"Timeout on attempt {attempt + 1}")
                self.pubchem_limiter.failure()
            except aiohttp.ClientError as e:
                logger.error(f"Network error: {e}")
                self.pubchem_limiter.failure()
        
        return None
    
    async def _make_chembl_request(
        self,
        session: aiohttp.ClientSession,
        endpoint: str,
        params: Optional[Dict] = None,
        max_retries: int = 3,
    ) -> Optional[Dict]:
        """Make request to ChEMBL API."""
        url = f"{self.CHEMBL_BASE}/{endpoint}"
        headers = {"Accept": "application/json"}
        
        for attempt in range(max_retries):
            await self.chembl_limiter.wait()
            
            try:
                async with session.get(
                    url,
                    params=params,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=30),
                ) as response:
                    if response.status == 200:
                        self.chembl_limiter.success()
                        return await response.json()
                    elif response.status == 404:
                        return None
                    elif response.status == 429 or response.status == 503:
                        logger.warning(f"ChEMBL rate limited, backing off...")
                        self.chembl_limiter.failure()
                        continue
                    else:
                        logger.warning(f"ChEMBL error: {response.status}")
                        return None
            except asyncio.TimeoutError:
                logger.warning(f"Timeout on attempt {attempt + 1}")
                self.chembl_limiter.failure()
            except aiohttp.ClientError as e:
                logger.error(f"Network error: {e}")
                self.chembl_limiter.failure()
        
        return None
    
    async def search_pubchem(
        self,
        query: str,
        limit: int = 100,
        session: Optional[aiohttp.ClientSession] = None,
    ) -> List[int]:
        """
        Search PubChem for compounds.
        
        Returns list of CIDs (Compound IDs).
        """
        close_session = False
        if session is None:
            session = aiohttp.ClientSession()
            close_session = True
        
        try:
            # Use autocomplete/name search
            endpoint = f"compound/name/{query}/cids/JSON"
            data = await self._make_pubchem_request(session, endpoint)
            
            if data and "IdentifierList" in data:
                cids = data["IdentifierList"].get("CID", [])
                return cids[:limit]
            
            return []
            
        finally:
            if close_session:
                await session.close()
    
    async def fetch_pubchem_compound(
        self,
        cid: int,
        session: Optional[aiohttp.ClientSession] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch compound details from PubChem.
        """
        if cid in self.seen_cids:
            return None
        self.seen_cids.add(cid)
        
        close_session = False
        if session is None:
            session = aiohttp.ClientSession()
            close_session = True
        
        try:
            # Get compound properties
            props = [
                "MolecularFormula", "MolecularWeight", "CanonicalSMILES",
                "IsomericSMILES", "InChI", "InChIKey", "IUPACName",
                "XLogP", "ExactMass", "MonoisotopicMass", "TPSA",
                "Complexity", "Charge", "HBondDonorCount", "HBondAcceptorCount",
                "RotatableBondCount", "HeavyAtomCount", "CovalentUnitCount",
            ]
            
            endpoint = f"compound/cid/{cid}/property/{','.join(props)}/JSON"
            data = await self._make_pubchem_request(session, endpoint)
            
            if not data or "PropertyTable" not in data:
                return None
            
            properties = data["PropertyTable"]["Properties"][0]
            
            compound = {
                "pubchem_cid": cid,
                "molecular_formula": properties.get("MolecularFormula"),
                "molecular_weight": properties.get("MolecularWeight"),
                "smiles": properties.get("CanonicalSMILES"),
                "isomeric_smiles": properties.get("IsomericSMILES"),
                "inchi": properties.get("InChI"),
                "inchi_key": properties.get("InChIKey"),
                "iupac_name": properties.get("IUPACName"),
                "xlogp": properties.get("XLogP"),
                "exact_mass": properties.get("ExactMass"),
                "source": "PubChem",
                "source_url": f"https://pubchem.ncbi.nlm.nih.gov/compound/{cid}",
            }
            
            # Get synonyms (common names)
            syn_endpoint = f"compound/cid/{cid}/synonyms/JSON"
            syn_data = await self._make_pubchem_request(session, syn_endpoint)
            
            if syn_data and "InformationList" in syn_data:
                info = syn_data["InformationList"]["Information"][0]
                synonyms = info.get("Synonym", [])
                if synonyms:
                    compound["name"] = synonyms[0]  # First synonym as primary name
                    compound["synonyms"] = synonyms[:10]  # Keep top 10
            
            # Try to get biological source info
            await self._fetch_pubchem_source(session, cid, compound)
            
            return compound
            
        finally:
            if close_session:
                await session.close()
    
    async def _fetch_pubchem_source(
        self,
        session: aiohttp.ClientSession,
        cid: int,
        compound: Dict,
    ) -> None:
        """Fetch biological source information from PubChem."""
        try:
            # Get annotations about source organisms
            view_url = f"{self.PUBCHEM_VIEW}/data/compound/{cid}/JSON"
            
            await self.pubchem_limiter.wait()
            
            async with session.get(
                view_url,
                params={"heading": "Taxonomy"},
                timeout=aiohttp.ClientTimeout(total=30),
            ) as response:
                if response.status != 200:
                    return
                
                data = await response.json()
                
                # Extract organism info from sections
                if "Record" in data:
                    sections = data["Record"].get("Section", [])
                    organisms = []
                    
                    for section in sections:
                        if section.get("TOCHeading") == "Taxonomy":
                            for subsec in section.get("Section", []):
                                for info in subsec.get("Information", []):
                                    val = info.get("Value", {})
                                    if "StringWithMarkup" in val:
                                        for item in val["StringWithMarkup"]:
                                            org = item.get("String", "")
                                            if org and "fungi" in org.lower():
                                                organisms.append(org)
                    
                    if organisms:
                        compound["producing_species"] = organisms[:5]
                        
        except Exception as e:
            logger.debug(f"Error fetching PubChem source: {e}")
    
    async def search_chembl(
        self,
        query: str,
        limit: int = 100,
        session: Optional[aiohttp.ClientSession] = None,
    ) -> List[str]:
        """
        Search ChEMBL for compounds.
        
        Returns list of ChEMBL IDs.
        """
        close_session = False
        if session is None:
            session = aiohttp.ClientSession()
            close_session = True
        
        try:
            params = {
                "pref_name__icontains": query,
                "limit": limit,
                "format": "json",
            }
            
            data = await self._make_chembl_request(session, "molecule.json", params)
            
            if data and "molecules" in data:
                return [m["molecule_chembl_id"] for m in data["molecules"]]
            
            return []
            
        finally:
            if close_session:
                await session.close()
    
    async def fetch_chembl_compound(
        self,
        chembl_id: str,
        session: Optional[aiohttp.ClientSession] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch compound details from ChEMBL.
        """
        if chembl_id in self.seen_chembl_ids:
            return None
        self.seen_chembl_ids.add(chembl_id)
        
        close_session = False
        if session is None:
            session = aiohttp.ClientSession()
            close_session = True
        
        try:
            data = await self._make_chembl_request(session, f"molecule/{chembl_id}.json")
            
            if not data:
                return None
            
            mol_props = data.get("molecule_properties", {}) or {}
            mol_structs = data.get("molecule_structures", {}) or {}
            
            compound = {
                "chembl_id": chembl_id,
                "name": data.get("pref_name"),
                "molecular_formula": mol_props.get("full_molformula"),
                "molecular_weight": mol_props.get("full_mwt"),
                "smiles": mol_structs.get("canonical_smiles"),
                "inchi": mol_structs.get("standard_inchi"),
                "inchi_key": mol_structs.get("standard_inchi_key"),
                "xlogp": mol_props.get("alogp"),
                "max_phase": data.get("max_phase"),  # Clinical phase
                "molecule_type": data.get("molecule_type"),
                "therapeutic_flag": data.get("therapeutic_flag"),
                "natural_product": data.get("natural_product"),
                "oral": data.get("oral"),
                "source": "ChEMBL",
                "source_url": f"https://www.ebi.ac.uk/chembl/compound_report_card/{chembl_id}",
            }
            
            # Get bioactivity data
            bioactivities = await self._fetch_chembl_bioactivity(session, chembl_id)
            if bioactivities:
                compound["bioactivity"] = bioactivities
            
            return compound
            
        finally:
            if close_session:
                await session.close()
    
    async def _fetch_chembl_bioactivity(
        self,
        session: aiohttp.ClientSession,
        chembl_id: str,
        limit: int = 20,
    ) -> List[Dict]:
        """Fetch bioactivity data for a compound."""
        params = {
            "molecule_chembl_id": chembl_id,
            "limit": limit,
            "format": "json",
        }
        
        data = await self._make_chembl_request(session, "activity.json", params)
        
        if not data or "activities" not in data:
            return []
        
        bioactivities = []
        for act in data["activities"]:
            activity = {
                "type": act.get("standard_type"),
                "value": act.get("standard_value"),
                "units": act.get("standard_units"),
                "relation": act.get("standard_relation"),
                "target_name": act.get("target_pref_name"),
                "target_type": act.get("target_type"),
                "assay_type": act.get("assay_type"),
            }
            
            if activity["type"] and activity["value"]:
                bioactivities.append(activity)
        
        return bioactivities
    
    async def fetch_fungal_compounds(
        self,
        compound_names: Optional[List[str]] = None,
        limit_per_compound: int = 5,
        session: Optional[aiohttp.ClientSession] = None,
    ) -> List[Dict[str, Any]]:
        """
        Fetch data for known fungal compounds.
        """
        if compound_names is None:
            compound_names = self.PRIORITY_COMPOUNDS
        
        close_session = False
        if session is None:
            session = aiohttp.ClientSession()
            close_session = True
        
        try:
            all_compounds = []
            
            for name in compound_names:
                logger.info(f"Fetching compound: {name}")
                
                # Search PubChem
                cids = await self.search_pubchem(name, limit=limit_per_compound, session=session)
                
                for cid in cids:
                    compound = await self.fetch_pubchem_compound(cid, session)
                    if compound:
                        # Determine compound class
                        compound["compound_class"] = self._detect_compound_class(
                            name, compound.get("name", "")
                        )
                        all_compounds.append(compound)
                
                # Also search ChEMBL
                chembl_ids = await self.search_chembl(name, limit=limit_per_compound, session=session)
                
                for chembl_id in chembl_ids[:limit_per_compound]:
                    compound = await self.fetch_chembl_compound(chembl_id, session)
                    if compound:
                        compound["compound_class"] = self._detect_compound_class(
                            name, compound.get("name", "")
                        )
                        all_compounds.append(compound)
            
            return all_compounds
            
        finally:
            if close_session:
                await session.close()
    
    def _detect_compound_class(self, query: str, name: str) -> Optional[str]:
        """Detect compound class from name."""
        combined = f"{query} {name}".lower()
        
        class_patterns = {
            "alkaloid": ["alkaloid", "psilocybin", "psilocin", "muscarine", "ergot"],
            "terpene": ["terpene", "terpenoid"],
            "triterpene": ["triterpene", "ganodermic", "lanostane"],
            "polysaccharide": ["polysaccharide", "glucan", "lentinan"],
            "peptide": ["peptide", "amatoxin", "phallotoxin", "cyclopeptide"],
            "indole": ["indole", "tryptamine"],
            "sterol": ["sterol", "ergosterol"],
        }
        
        for compound_class, patterns in class_patterns.items():
            for pattern in patterns:
                if pattern in combined:
                    return compound_class
        
        return None
    
    async def search_by_species(
        self,
        species_name: str,
        limit: int = 50,
        session: Optional[aiohttp.ClientSession] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search for compounds produced by a specific fungal species.
        """
        close_session = False
        if session is None:
            session = aiohttp.ClientSession()
            close_session = True
        
        try:
            # Search PubChem with species name
            cids = await self.search_pubchem(species_name, limit=limit, session=session)
            
            compounds = []
            for cid in cids:
                compound = await self.fetch_pubchem_compound(cid, session)
                if compound:
                    if "producing_species" not in compound:
                        compound["producing_species"] = [species_name]
                    compounds.append(compound)
            
            return compounds
            
        finally:
            if close_session:
                await session.close()
    
    async def sync(
        self,
        compound_names: Optional[List[str]] = None,
        species_list: Optional[List[str]] = None,
        limit_per_source: int = 10,
    ) -> Dict[str, int]:
        """
        Sync fungal compound data to MINDEX.
        """
        if compound_names is None:
            compound_names = self.PRIORITY_COMPOUNDS
        
        if species_list is None:
            species_list = [
                "Amanita muscaria", "Psilocybe cubensis", "Ganoderma lucidum",
                "Hericium erinaceus", "Cordyceps militaris",
            ]
        
        stats = {
            "total_fetched": 0,
            "total_saved": 0,
            "from_pubchem": 0,
            "from_chembl": 0,
        }
        
        async with aiohttp.ClientSession() as session:
            # Fetch priority compounds
            logger.info("Fetching priority fungal compounds...")
            compounds = await self.fetch_fungal_compounds(
                compound_names=compound_names,
                limit_per_compound=limit_per_source,
                session=session,
            )
            
            for compound in compounds:
                stats["total_fetched"] += 1
                if compound.get("source") == "PubChem":
                    stats["from_pubchem"] += 1
                else:
                    stats["from_chembl"] += 1
                
                if self.db:
                    try:
                        await self._save_compound(compound)
                        stats["total_saved"] += 1
                    except Exception as e:
                        logger.error(f"Error saving compound: {e}")
            
            # Fetch compounds by species
            for species in species_list:
                logger.info(f"Fetching compounds for {species}...")
                
                species_compounds = await self.search_by_species(
                    species, limit=limit_per_source, session=session
                )
                
                for compound in species_compounds:
                    stats["total_fetched"] += 1
                    stats["from_pubchem"] += 1
                    
                    if self.db:
                        try:
                            await self._save_compound(compound)
                            stats["total_saved"] += 1
                        except Exception as e:
                            logger.error(f"Error saving compound: {e}")
        
        return stats
    
    async def _save_compound(self, compound: Dict[str, Any]) -> None:
        """Save compound to MINDEX database."""
        if not self.db:
            return
        
        import json
        
        query = """
        INSERT INTO core.compounds (
            name, iupac_name, pubchem_cid, chembl_id, smiles, inchi, inchi_key,
            molecular_formula, molecular_weight, exact_mass, xlogp,
            compound_class, bioactivity, producing_species, source, source_url,
            metadata, created_at
        ) VALUES (
            $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, NOW()
        )
        ON CONFLICT (pubchem_cid) DO UPDATE SET
            name = COALESCE(EXCLUDED.name, core.compounds.name),
            chembl_id = COALESCE(EXCLUDED.chembl_id, core.compounds.chembl_id),
            bioactivity = COALESCE(EXCLUDED.bioactivity, core.compounds.bioactivity),
            producing_species = array_cat(
                COALESCE(core.compounds.producing_species, ARRAY[]::text[]),
                COALESCE(EXCLUDED.producing_species, ARRAY[]::text[])
            ),
            updated_at = NOW()
        WHERE EXCLUDED.pubchem_cid IS NOT NULL
        """
        
        await self.db.execute(
            query,
            compound.get("name"),
            compound.get("iupac_name"),
            compound.get("pubchem_cid"),
            compound.get("chembl_id"),
            compound.get("smiles"),
            compound.get("inchi"),
            compound.get("inchi_key"),
            compound.get("molecular_formula"),
            compound.get("molecular_weight"),
            compound.get("exact_mass"),
            compound.get("xlogp"),
            compound.get("compound_class"),
            json.dumps(compound.get("bioactivity", [])) if compound.get("bioactivity") else None,
            compound.get("producing_species", []),
            compound.get("source"),
            compound.get("source_url"),
            {
                "synonyms": compound.get("synonyms", []),
                "natural_product": compound.get("natural_product"),
                "max_phase": compound.get("max_phase"),
            },
        )
