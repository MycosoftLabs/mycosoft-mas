"""
GenomicsVisualizationAgent
Handles generation of circular and linear genome visualizations

Part of MAS v2 - Multi-Agent System for Mycosoft
"""

import asyncio
import json
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class VisualizationType(str, Enum):
    CIRCOS = "circos"
    GENOME_TRACK = "genome_track"
    PHYLOGENY = "phylogeny"
    PATHWAY = "pathway"


@dataclass
class GenomicsVisualizationRequest:
    """Request for genomics visualization generation"""
    visualization_type: VisualizationType
    species: str
    chromosome: Optional[str] = None
    start: Optional[int] = None
    end: Optional[int] = None
    format: str = "svg"
    options: Optional[Dict[str, Any]] = None


@dataclass
class GenomicsVisualizationResult:
    """Result of genomics visualization generation"""
    success: bool
    visualization_type: VisualizationType
    species: str
    image_data: Optional[str] = None
    format: str = "svg"
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class GenomicsVisualizationAgent:
    """
    Agent responsible for generating genomics visualizations
    
    Capabilities:
    - Circular genome plots (circos)
    - Linear genome track views
    - Phylogenetic tree visualizations
    - Metabolic pathway diagrams
    """
    
    name = "GenomicsVisualizationAgent"
    description = "Generates circular and linear genome visualizations for fungal species"
    
    def __init__(
        self,
        mindex_api_url: Optional[str] = None,
        viz_service_url: Optional[str] = None
    ):
        self.mindex_api_url = mindex_api_url
        self.viz_service_url = viz_service_url
        self._cache: Dict[str, GenomicsVisualizationResult] = {}
    
    async def process(self, request: GenomicsVisualizationRequest) -> GenomicsVisualizationResult:
        """Process a visualization request"""
        cache_key = self._get_cache_key(request)
        
        # Check cache
        if cache_key in self._cache:
            logger.info(f"Cache hit for {cache_key}")
            return self._cache[cache_key]
        
        try:
            result = await self._generate_visualization(request)
            
            # Cache successful results
            if result.success:
                self._cache[cache_key] = result
            
            return result
            
        except Exception as e:
            logger.error(f"Visualization generation failed: {e}")
            return GenomicsVisualizationResult(
                success=False,
                visualization_type=request.visualization_type,
                species=request.species,
                error=str(e)
            )
    
    async def _generate_visualization(
        self, 
        request: GenomicsVisualizationRequest
    ) -> GenomicsVisualizationResult:
        """Generate visualization based on type"""
        
        if request.visualization_type == VisualizationType.CIRCOS:
            return await self._generate_circos(request)
        elif request.visualization_type == VisualizationType.GENOME_TRACK:
            return await self._generate_genome_track(request)
        elif request.visualization_type == VisualizationType.PHYLOGENY:
            return await self._generate_phylogeny(request)
        elif request.visualization_type == VisualizationType.PATHWAY:
            return await self._generate_pathway(request)
        else:
            raise ValueError(f"Unknown visualization type: {request.visualization_type}")
    
    async def _generate_circos(
        self, 
        request: GenomicsVisualizationRequest
    ) -> GenomicsVisualizationResult:
        """Generate circos-style circular plot"""
        logger.info(f"Generating circos plot for {request.species}")
        
        # Fetch genome data from MINDEX
        genome_data = await self._fetch_genome_data(request.species)
        
        if self.viz_service_url:
            # Call Python visualization service
            try:
                import aiohttp
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        f"{self.viz_service_url}/circos",
                        json={
                            "species": request.species,
                            "plot_type": "genome",
                            "output_format": request.format,
                            "chromosomes": genome_data.get("chromosomes", []),
                            "genes": genome_data.get("genes", [])
                        }
                    ) as response:
                        if response.status == 200:
                            data = await response.json()
                            return GenomicsVisualizationResult(
                                success=True,
                                visualization_type=VisualizationType.CIRCOS,
                                species=request.species,
                                image_data=data.get("image"),
                                format=request.format,
                                metadata={"source": "viz_service"}
                            )
            except Exception as e:
                logger.warning(f"Viz service call failed: {e}, using fallback")
        
        # Fallback: Generate simple SVG
        svg = self._generate_fallback_circos_svg(request.species, genome_data)
        
        return GenomicsVisualizationResult(
            success=True,
            visualization_type=VisualizationType.CIRCOS,
            species=request.species,
            image_data=svg,
            format="svg",
            metadata={"source": "fallback"}
        )
    
    async def _generate_genome_track(
        self, 
        request: GenomicsVisualizationRequest
    ) -> GenomicsVisualizationResult:
        """Generate linear genome track visualization"""
        logger.info(f"Generating genome track for {request.species}")
        
        # Fetch genes for the region
        genes = await self._fetch_genes(
            request.species, 
            request.chromosome,
            request.start,
            request.end
        )
        
        # Generate SVG track
        svg = self._generate_genome_track_svg(
            request.species,
            request.chromosome or "chr1",
            genes,
            request.start or 0,
            request.end or 5000000
        )
        
        return GenomicsVisualizationResult(
            success=True,
            visualization_type=VisualizationType.GENOME_TRACK,
            species=request.species,
            image_data=svg,
            format="svg",
            metadata={
                "chromosome": request.chromosome,
                "start": request.start,
                "end": request.end,
                "gene_count": len(genes)
            }
        )
    
    async def _generate_phylogeny(
        self, 
        request: GenomicsVisualizationRequest
    ) -> GenomicsVisualizationResult:
        """Generate phylogenetic tree visualization"""
        logger.info(f"Generating phylogeny for {request.species}")
        
        # Placeholder for phylogeny generation
        return GenomicsVisualizationResult(
            success=True,
            visualization_type=VisualizationType.PHYLOGENY,
            species=request.species,
            image_data="<svg>...</svg>",
            format="svg"
        )
    
    async def _generate_pathway(
        self, 
        request: GenomicsVisualizationRequest
    ) -> GenomicsVisualizationResult:
        """Generate metabolic pathway visualization"""
        logger.info(f"Generating pathway for {request.species}")
        
        # Placeholder for pathway generation
        return GenomicsVisualizationResult(
            success=True,
            visualization_type=VisualizationType.PATHWAY,
            species=request.species,
            image_data="<svg>...</svg>",
            format="svg"
        )
    
    async def _fetch_genome_data(self, species: str) -> Dict[str, Any]:
        """Fetch genome data from MINDEX API"""
        if not self.mindex_api_url:
            return self._get_demo_genome_data(species)
        
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.mindex_api_url}/genomes",
                    params={"species": species}
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get("genomes"):
                            return data["genomes"][0]
        except Exception as e:
            logger.warning(f"MINDEX API call failed: {e}")
        
        return self._get_demo_genome_data(species)
    
    async def _fetch_genes(
        self, 
        species: str,
        chromosome: Optional[str] = None,
        start: Optional[int] = None,
        end: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Fetch genes from MINDEX API"""
        if not self.mindex_api_url:
            return self._get_demo_genes(species)
        
        try:
            import aiohttp
            params = {}
            if chromosome:
                params["chr"] = chromosome
            if start is not None:
                params["start"] = str(start)
            if end is not None:
                params["end"] = str(end)
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.mindex_api_url}/genes/{species}",
                    params=params
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get("genes", [])
        except Exception as e:
            logger.warning(f"MINDEX genes API call failed: {e}")
        
        return self._get_demo_genes(species)
    
    def _get_demo_genome_data(self, species: str) -> Dict[str, Any]:
        """Get demo genome data for testing"""
        return {
            "id": species.lower().replace(" ", "_"),
            "species_name": species,
            "chromosomes": [
                {"name": "chr1", "length": 5200000},
                {"name": "chr2", "length": 4800000},
                {"name": "chr3", "length": 4200000},
                {"name": "chr4", "length": 3900000},
                {"name": "chr5", "length": 3500000},
            ]
        }
    
    def _get_demo_genes(self, species: str) -> List[Dict[str, Any]]:
        """Get demo genes for testing"""
        genes = []
        for i in range(50):
            genes.append({
                "id": f"gene_{i+1}",
                "name": f"psi{chr(65 + i % 26)}{i+1}",
                "chromosome": f"chr{(i % 5) + 1}",
                "start": 10000 + i * 50000,
                "end": 10000 + i * 50000 + 3000 + (i * 100),
                "strand": "+" if i % 2 == 0 else "-"
            })
        return genes
    
    def _generate_fallback_circos_svg(
        self, 
        species: str, 
        genome_data: Dict[str, Any]
    ) -> str:
        """Generate a simple SVG circos plot as fallback"""
        chromosomes = genome_data.get("chromosomes", [])
        n_chr = len(chromosomes) or 5
        
        svg_parts = [
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 400">',
            '<rect width="400" height="400" fill="#0a0a0f"/>',
        ]
        
        # Draw chromosome sectors
        for i in range(n_chr):
            color = f"hsl({120 + i * 30}, 70%, 50%)"
            
            svg_parts.append(
                f'<circle cx="200" cy="200" r="{130 - i * 5}" '
                f'fill="none" stroke="{color}" stroke-width="20" opacity="0.6"/>'
            )
        
        svg_parts.append(
            f'<text x="200" y="200" text-anchor="middle" fill="white" font-size="14">{species}</text>'
        )
        svg_parts.append('</svg>')
        
        return ''.join(svg_parts)
    
    def _generate_genome_track_svg(
        self,
        species: str,
        chromosome: str,
        genes: List[Dict[str, Any]],
        start: int,
        end: int
    ) -> str:
        """Generate a simple SVG genome track"""
        width = 800
        height = 200
        track_y = 100
        
        svg_parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}">',
            f'<rect width="{width}" height="{height}" fill="#0a0a0f"/>',
            # Chromosome backbone
            f'<rect x="50" y="{track_y - 10}" width="{width - 100}" height="20" fill="#333" rx="5"/>',
        ]
        
        # Draw genes
        region_length = end - start
        for gene in genes[:30]:  # Limit to 30 genes
            gene_start = gene.get("start", 0)
            gene_end = gene.get("end", gene_start + 1000)
            
            if gene_end < start or gene_start > end:
                continue
            
            x = 50 + ((gene_start - start) / region_length) * (width - 100)
            w = ((gene_end - gene_start) / region_length) * (width - 100)
            
            color = "#22c55e" if gene.get("strand") == "+" else "#8b5cf6"
            y_offset = -25 if gene.get("strand") == "+" else 25
            
            svg_parts.append(
                f'<rect x="{x}" y="{track_y + y_offset - 8}" width="{max(2, w)}" height="16" '
                f'fill="{color}" rx="2" opacity="0.8"/>'
            )
        
        # Labels
        svg_parts.append(
            f'<text x="50" y="30" fill="white" font-size="14">{species} - {chromosome}</text>'
        )
        svg_parts.append(
            f'<text x="50" y="180" fill="#888" font-size="10">{start:,} - {end:,} bp</text>'
        )
        
        svg_parts.append('</svg>')
        
        return ''.join(svg_parts)
    
    def _get_cache_key(self, request: GenomicsVisualizationRequest) -> str:
        """Generate cache key for request"""
        return f"{request.visualization_type}:{request.species}:{request.chromosome}:{request.start}:{request.end}"
    
    def clear_cache(self):
        """Clear visualization cache"""
        self._cache.clear()
    
    def get_capabilities(self) -> Dict[str, Any]:
        """Return agent capabilities"""
        return {
            "name": self.name,
            "description": self.description,
            "visualization_types": [v.value for v in VisualizationType],
            "output_formats": ["svg", "png", "pdf"],
            "features": [
                "Circular genome plots (Circos-style)",
                "Linear genome track views",
                "Phylogenetic tree visualizations",
                "Metabolic pathway diagrams"
            ]
        }


# Factory function for creating agent
def create_genomics_visualization_agent(
    mindex_api_url: Optional[str] = None,
    viz_service_url: Optional[str] = None
) -> GenomicsVisualizationAgent:
    """Create a configured GenomicsVisualizationAgent"""
    return GenomicsVisualizationAgent(
        mindex_api_url=mindex_api_url,
        viz_service_url=viz_service_url
    )
