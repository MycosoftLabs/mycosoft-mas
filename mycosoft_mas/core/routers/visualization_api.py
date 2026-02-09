"""Visualization API for genomic and phylogenetic data.
Created: February 9, 2026
"""
from fastapi import APIRouter, HTTPException, Query, Response
from typing import Dict, Any, Optional, List
import logging
import json

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/visualization", tags=["visualization"])

@router.get("/circos")
async def get_circos_plot(
    species_id: Optional[str] = Query(None, description="Species ID for gene network"),
    format: str = Query("svg", description="Output format: svg or png"),
) -> Response:
    """Generate circular plot for gene networks using pyCirclize."""
    try:
        # Try to import pyCirclize - if not available, return informative error
        try:
            from pycirclize import Circos
        except ImportError:
            raise HTTPException(
                status_code=503,
                detail="pyCirclize not installed. Install with: pip install pycirclize"
            )
        
        # Create a basic circos plot for the species
        circos = Circos(sectors={"GeneA": 100, "GeneB": 80, "GeneC": 60, "GeneD": 120})
        for sector in circos.sectors:
            track = sector.add_track((80, 100))
            track.axis()
            track.text(sector.name, fontsize=8)
        
        fig = circos.plotfig()
        
        import io
        buf = io.BytesIO()
        if format == "png":
            fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
            media_type = "image/png"
        else:
            fig.savefig(buf, format="svg", bbox_inches="tight")
            media_type = "image/svg+xml"
        buf.seek(0)
        
        import matplotlib.pyplot as plt
        plt.close(fig)
        
        return Response(content=buf.read(), media_type=media_type)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Circos plot generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/phylogeny")
async def get_phylogeny_tree(
    taxon: Optional[str] = Query(None, description="Root taxon for phylogenetic tree"),
    format: str = Query("svg", description="Output format: svg or png"),
) -> Response:
    """Generate phylogenetic circular tree."""
    try:
        try:
            from pycirclize import Circos
        except ImportError:
            raise HTTPException(
                status_code=503,
                detail="pyCirclize not installed. Install with: pip install pycirclize"
            )
        
        # Create a phylogenetic-style circular layout
        sectors = {}
        if taxon:
            sectors = {f"{taxon}_clade_{i}": 50 + i * 10 for i in range(1, 7)}
        else:
            sectors = {
                "Basidiomycota": 120,
                "Ascomycota": 100,
                "Zygomycota": 60,
                "Chytridiomycota": 40,
                "Glomeromycota": 30,
            }
        
        circos = Circos(sectors=sectors)
        for sector in circos.sectors:
            track = sector.add_track((70, 95))
            track.axis()
            track.text(sector.name, fontsize=7, r=55)
        
        fig = circos.plotfig()
        
        import io
        buf = io.BytesIO()
        if format == "png":
            fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
            media_type = "image/png"
        else:
            fig.savefig(buf, format="svg", bbox_inches="tight")
            media_type = "image/svg+xml"
        buf.seek(0)
        
        import matplotlib.pyplot as plt
        plt.close(fig)
        
        return Response(content=buf.read(), media_type=media_type)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Phylogeny tree generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health")
async def visualization_health() -> Dict[str, Any]:
    """Check visualization service health and available backends."""
    backends = {}
    try:
        import pycirclize
        backends["pycirclize"] = {"available": True, "version": getattr(pycirclize, "__version__", "unknown")}
    except ImportError:
        backends["pycirclize"] = {"available": False}
    
    try:
        import matplotlib
        backends["matplotlib"] = {"available": True, "version": matplotlib.__version__}
    except ImportError:
        backends["matplotlib"] = {"available": False}
    
    return {
        "status": "healthy",
        "backends": backends,
        "endpoints": ["/api/visualization/circos", "/api/visualization/phylogeny"],
    }
