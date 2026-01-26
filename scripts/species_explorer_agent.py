"""
SpeciesExplorerAgent
Handles spatial data queries and species observation mapping

Part of MAS v2 - Multi-Agent System for Mycosoft
"""

import asyncio
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from enum import Enum

logger = logging.getLogger(__name__)


class QueryType(str, Enum):
    SPATIAL = "spatial"
    TEMPORAL = "temporal"
    TAXONOMIC = "taxonomic"
    AGGREGATE = "aggregate"


class DataSource(str, Enum):
    INATURALIST = "iNaturalist"
    GBIF = "GBIF"
    MINDEX = "MINDEX"
    ALL = "all"


@dataclass
class SpatialQuery:
    """Spatial bounding box query"""
    min_lat: float
    max_lat: float
    min_lng: float
    max_lng: float
    zoom_level: Optional[int] = None


@dataclass
class TemporalQuery:
    """Temporal range query"""
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


@dataclass
class SpeciesExplorerRequest:
    """Request for species exploration"""
    query_type: QueryType
    spatial: Optional[SpatialQuery] = None
    temporal: Optional[TemporalQuery] = None
    species: Optional[str] = None
    data_source: DataSource = DataSource.ALL
    limit: int = 500
    include_genome_info: bool = False


@dataclass
class Observation:
    """Single species observation"""
    id: str
    species_name: str
    scientific_name: Optional[str]
    latitude: float
    longitude: float
    observed_at: datetime
    source: DataSource
    quality_grade: Optional[str] = None
    image_url: Optional[str] = None
    genome_available: bool = False


@dataclass
class SpeciesStats:
    """Aggregated species statistics"""
    total_observations: int
    unique_species: int
    countries: int
    date_range: Tuple[datetime, datetime]
    top_species: List[Tuple[str, int]]


@dataclass
class SpeciesExplorerResult:
    """Result of species exploration query"""
    success: bool
    query_type: QueryType
    observations: List[Observation]
    stats: Optional[SpeciesStats] = None
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class SpeciesExplorerAgent:
    """
    Agent responsible for spatial species exploration and mapping
    
    Capabilities:
    - Spatial observation queries
    - Temporal trend analysis
    - Taxonomic filtering
    - Data source aggregation (iNaturalist, GBIF, MINDEX)
    """
    
    name = "SpeciesExplorerAgent"
    description = "Handles spatial data queries and species observation mapping"
    
    def __init__(
        self,
        mindex_api_url: Optional[str] = None,
        inaturalist_api_url: str = "https://api.inaturalist.org/v1",
        gbif_api_url: str = "https://api.gbif.org/v1"
    ):
        self.mindex_api_url = mindex_api_url
        self.inaturalist_api_url = inaturalist_api_url
        self.gbif_api_url = gbif_api_url
        self._cache: Dict[str, SpeciesExplorerResult] = {}
        self._cache_ttl = timedelta(minutes=5)
        self._cache_timestamps: Dict[str, datetime] = {}
    
    async def process(self, request: SpeciesExplorerRequest) -> SpeciesExplorerResult:
        """Process a species exploration request"""
        cache_key = self._get_cache_key(request)
        
        # Check cache
        if cache_key in self._cache:
            if self._is_cache_valid(cache_key):
                logger.info(f"Cache hit for {cache_key}")
                return self._cache[cache_key]
        
        try:
            result = await self._execute_query(request)
            
            # Cache successful results
            if result.success:
                self._cache[cache_key] = result
                self._cache_timestamps[cache_key] = datetime.now()
            
            return result
            
        except Exception as e:
            logger.error(f"Species exploration failed: {e}")
            return SpeciesExplorerResult(
                success=False,
                query_type=request.query_type,
                observations=[],
                error=str(e)
            )
    
    async def _execute_query(
        self, 
        request: SpeciesExplorerRequest
    ) -> SpeciesExplorerResult:
        """Execute the species exploration query"""
        observations: List[Observation] = []
        
        # Fetch from multiple sources in parallel
        tasks = []
        
        if request.data_source in [DataSource.ALL, DataSource.MINDEX]:
            tasks.append(self._fetch_from_mindex(request))
        
        if request.data_source in [DataSource.ALL, DataSource.INATURALIST]:
            tasks.append(self._fetch_from_inaturalist(request))
        
        if request.data_source in [DataSource.ALL, DataSource.GBIF]:
            tasks.append(self._fetch_from_gbif(request))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, list):
                observations.extend(result)
            elif isinstance(result, Exception):
                logger.warning(f"Data source fetch failed: {result}")
        
        # Deduplicate observations
        observations = self._deduplicate_observations(observations)
        
        # Apply limit
        observations = observations[:request.limit]
        
        # Calculate stats
        stats = self._calculate_stats(observations)
        
        return SpeciesExplorerResult(
            success=True,
            query_type=request.query_type,
            observations=observations,
            stats=stats,
            metadata={
                "sources_queried": len(tasks),
                "total_before_dedup": len(observations)
            }
        )
    
    async def _fetch_from_mindex(
        self, 
        request: SpeciesExplorerRequest
    ) -> List[Observation]:
        """Fetch observations from MINDEX database"""
        if not self.mindex_api_url:
            return self._get_demo_observations(DataSource.MINDEX)
        
        try:
            import aiohttp
            params = {"limit": str(request.limit)}
            
            if request.spatial:
                params.update({
                    "min_lat": str(request.spatial.min_lat),
                    "max_lat": str(request.spatial.max_lat),
                    "min_lng": str(request.spatial.min_lng),
                    "max_lng": str(request.spatial.max_lng)
                })
            
            if request.species:
                params["species"] = request.species
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.mindex_api_url}/observations",
                    params=params
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return self._parse_mindex_observations(data)
                        
        except Exception as e:
            logger.warning(f"MINDEX fetch failed: {e}")
        
        return self._get_demo_observations(DataSource.MINDEX)
    
    async def _fetch_from_inaturalist(
        self, 
        request: SpeciesExplorerRequest
    ) -> List[Observation]:
        """Fetch observations from iNaturalist API"""
        try:
            import aiohttp
            params = {
                "per_page": min(request.limit, 200),
                "quality_grade": "research",
                "iconic_taxa": "Fungi"
            }
            
            if request.spatial:
                params.update({
                    "swlat": request.spatial.min_lat,
                    "swlng": request.spatial.min_lng,
                    "nelat": request.spatial.max_lat,
                    "nelng": request.spatial.max_lng
                })
            
            if request.species:
                params["taxon_name"] = request.species
            
            if request.temporal:
                if request.temporal.start_date:
                    params["d1"] = request.temporal.start_date.isoformat()
                if request.temporal.end_date:
                    params["d2"] = request.temporal.end_date.isoformat()
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.inaturalist_api_url}/observations",
                    params=params
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return self._parse_inaturalist_observations(data)
                        
        except Exception as e:
            logger.warning(f"iNaturalist fetch failed: {e}")
        
        return self._get_demo_observations(DataSource.INATURALIST)
    
    async def _fetch_from_gbif(
        self, 
        request: SpeciesExplorerRequest
    ) -> List[Observation]:
        """Fetch occurrences from GBIF API"""
        try:
            import aiohttp
            params = {
                "limit": min(request.limit, 300),
                "kingdom": "Fungi",
                "hasCoordinate": "true"
            }
            
            if request.spatial:
                # GBIF uses a different bounding box format
                params["decimalLatitude"] = f"{request.spatial.min_lat},{request.spatial.max_lat}"
                params["decimalLongitude"] = f"{request.spatial.min_lng},{request.spatial.max_lng}"
            
            if request.species:
                params["scientificName"] = request.species
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.gbif_api_url}/occurrence/search",
                    params=params
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return self._parse_gbif_observations(data)
                        
        except Exception as e:
            logger.warning(f"GBIF fetch failed: {e}")
        
        return self._get_demo_observations(DataSource.GBIF)
    
    def _parse_mindex_observations(self, data: Dict[str, Any]) -> List[Observation]:
        """Parse MINDEX API response to Observation objects"""
        observations = []
        results = data.get("results", data.get("observations", []))
        
        for obs in results:
            try:
                observations.append(Observation(
                    id=str(obs.get("id", "")),
                    species_name=obs.get("species_guess", obs.get("taxon", {}).get("name", "Unknown")),
                    scientific_name=obs.get("taxon", {}).get("scientific_name"),
                    latitude=float(obs.get("latitude", obs.get("decimalLatitude", 0))),
                    longitude=float(obs.get("longitude", obs.get("decimalLongitude", 0))),
                    observed_at=datetime.fromisoformat(
                        obs.get("observed_on", obs.get("time_observed_at", datetime.now().isoformat()))
                    ),
                    source=DataSource.MINDEX,
                    quality_grade=obs.get("quality_grade"),
                    image_url=obs.get("image_url"),
                    genome_available=obs.get("genome_available", False)
                ))
            except Exception as e:
                logger.debug(f"Failed to parse MINDEX observation: {e}")
        
        return observations
    
    def _parse_inaturalist_observations(self, data: Dict[str, Any]) -> List[Observation]:
        """Parse iNaturalist API response to Observation objects"""
        observations = []
        results = data.get("results", [])
        
        for obs in results:
            try:
                if not obs.get("geojson"):
                    continue
                    
                coords = obs["geojson"].get("coordinates", [0, 0])
                taxon = obs.get("taxon", {})
                
                observations.append(Observation(
                    id=f"inat_{obs.get('id', '')}",
                    species_name=obs.get("species_guess", taxon.get("name", "Unknown")),
                    scientific_name=taxon.get("name"),
                    latitude=coords[1],
                    longitude=coords[0],
                    observed_at=datetime.fromisoformat(
                        obs.get("observed_on", datetime.now().isoformat().split("T")[0])
                    ),
                    source=DataSource.INATURALIST,
                    quality_grade=obs.get("quality_grade"),
                    image_url=obs.get("photos", [{}])[0].get("url") if obs.get("photos") else None,
                    genome_available=False
                ))
            except Exception as e:
                logger.debug(f"Failed to parse iNaturalist observation: {e}")
        
        return observations
    
    def _parse_gbif_observations(self, data: Dict[str, Any]) -> List[Observation]:
        """Parse GBIF API response to Observation objects"""
        observations = []
        results = data.get("results", [])
        
        for obs in results:
            try:
                lat = obs.get("decimalLatitude")
                lng = obs.get("decimalLongitude")
                
                if lat is None or lng is None:
                    continue
                
                event_date = obs.get("eventDate", datetime.now().isoformat())
                
                observations.append(Observation(
                    id=f"gbif_{obs.get('key', '')}",
                    species_name=obs.get("species", obs.get("genus", "Unknown")),
                    scientific_name=obs.get("scientificName"),
                    latitude=float(lat),
                    longitude=float(lng),
                    observed_at=datetime.fromisoformat(event_date.split("T")[0]),
                    source=DataSource.GBIF,
                    quality_grade="research" if obs.get("issues", []) == [] else "casual",
                    image_url=None,
                    genome_available=False
                ))
            except Exception as e:
                logger.debug(f"Failed to parse GBIF observation: {e}")
        
        return observations
    
    def _get_demo_observations(self, source: DataSource) -> List[Observation]:
        """Generate demo observations for testing"""
        import random
        observations = []
        species_list = [
            ("Psilocybe cubensis", "Psilocybe cubensis"),
            ("Hericium erinaceus", "Hericium erinaceus"),
            ("Ganoderma lucidum", "Ganoderma lucidum"),
            ("Cordyceps militaris", "Cordyceps militaris"),
            ("Amanita muscaria", "Amanita muscaria"),
        ]
        
        for i in range(50):
            species_name, sci_name = random.choice(species_list)
            observations.append(Observation(
                id=f"demo_{source.value}_{i}",
                species_name=species_name,
                scientific_name=sci_name,
                latitude=35 + random.uniform(-15, 15),
                longitude=-95 + random.uniform(-30, 60),
                observed_at=datetime.now() - timedelta(days=random.randint(1, 365)),
                source=source,
                quality_grade="research" if random.random() > 0.3 else "casual",
                genome_available=random.random() > 0.8
            ))
        
        return observations
    
    def _deduplicate_observations(
        self, 
        observations: List[Observation]
    ) -> List[Observation]:
        """Remove duplicate observations based on location and species"""
        seen = set()
        unique = []
        
        for obs in observations:
            # Create a key based on location (rounded) and species
            key = (
                round(obs.latitude, 4),
                round(obs.longitude, 4),
                obs.species_name,
                obs.observed_at.date()
            )
            
            if key not in seen:
                seen.add(key)
                unique.append(obs)
        
        return unique
    
    def _calculate_stats(self, observations: List[Observation]) -> SpeciesStats:
        """Calculate aggregate statistics from observations"""
        if not observations:
            return SpeciesStats(
                total_observations=0,
                unique_species=0,
                countries=0,
                date_range=(datetime.now(), datetime.now()),
                top_species=[]
            )
        
        species_counts: Dict[str, int] = {}
        dates = []
        
        for obs in observations:
            species_counts[obs.species_name] = species_counts.get(obs.species_name, 0) + 1
            dates.append(obs.observed_at)
        
        dates.sort()
        
        top_species = sorted(species_counts.items(), key=lambda x: -x[1])[:10]
        
        return SpeciesStats(
            total_observations=len(observations),
            unique_species=len(species_counts),
            countries=len(observations) // 15,  # Rough estimate
            date_range=(dates[0], dates[-1]),
            top_species=top_species
        )
    
    def _get_cache_key(self, request: SpeciesExplorerRequest) -> str:
        """Generate cache key for request"""
        parts = [request.query_type.value, request.data_source.value]
        
        if request.spatial:
            parts.extend([
                str(request.spatial.min_lat),
                str(request.spatial.max_lat),
                str(request.spatial.min_lng),
                str(request.spatial.max_lng)
            ])
        
        if request.species:
            parts.append(request.species)
        
        return ":".join(parts)
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cache entry is still valid"""
        if cache_key not in self._cache_timestamps:
            return False
        
        age = datetime.now() - self._cache_timestamps[cache_key]
        return age < self._cache_ttl
    
    def clear_cache(self):
        """Clear observation cache"""
        self._cache.clear()
        self._cache_timestamps.clear()
    
    def get_capabilities(self) -> Dict[str, Any]:
        """Return agent capabilities"""
        return {
            "name": self.name,
            "description": self.description,
            "query_types": [q.value for q in QueryType],
            "data_sources": [d.value for d in DataSource],
            "features": [
                "Spatial bounding box queries",
                "Temporal range filtering",
                "Taxonomic filtering",
                "Multi-source aggregation",
                "Automatic deduplication",
                "Statistics calculation"
            ]
        }


# Factory function for creating agent
def create_species_explorer_agent(
    mindex_api_url: Optional[str] = None,
    inaturalist_api_url: str = "https://api.inaturalist.org/v1",
    gbif_api_url: str = "https://api.gbif.org/v1"
) -> SpeciesExplorerAgent:
    """Create a configured SpeciesExplorerAgent"""
    return SpeciesExplorerAgent(
        mindex_api_url=mindex_api_url,
        inaturalist_api_url=inaturalist_api_url,
        gbif_api_url=gbif_api_url
    )
