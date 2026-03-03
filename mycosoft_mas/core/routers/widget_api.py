"""
Widget & Visualization API - Interactive Response Widgets for MYCA
=================================================================

Provides API endpoints for MYCA to serve interactive widgets and
visualizations alongside her responses - maps, chemistry diagrams,
genetic visualizations, taxonomy trees, simulations, and more.

These widgets are rendered in the client (web/mobile) and provide
rich, interactive experiences beyond text.

Author: MYCA / Morgan Rockwell
Created: March 3, 2026
"""

import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/widgets", tags=["widgets"])


# ============================================================================
# Widget Types
# ============================================================================


class WidgetType(str, Enum):
    """Types of interactive widgets MYCA can serve."""
    MAP = "map"                          # Geographic/location map
    TAXONOMY_TREE = "taxonomy_tree"      # Taxonomic classification tree
    MOLECULE_3D = "molecule_3d"          # 3D molecular structure
    GENETIC_VIEWER = "genetic_viewer"    # DNA/RNA sequence viewer
    PHYLOGENETIC_TREE = "phylogenetic_tree"  # Evolutionary tree
    WEATHER_MAP = "weather_map"          # Weather/climate visualization
    SIMULATION = "simulation"            # Physics/chemistry simulation
    SPECIES_CARD = "species_card"        # Species information card
    CHART = "chart"                      # Data chart (line, bar, pie, scatter)
    IMAGE_GALLERY = "image_gallery"      # Image gallery with metadata
    TIMELINE = "timeline"                # Historical/event timeline
    NETWORK_GRAPH = "network_graph"      # Network/relationship graph
    HEATMAP = "heatmap"                  # Heatmap visualization
    ECOSYSTEM_MODEL = "ecosystem_model"  # Ecosystem interaction model
    CHEMICAL_REACTION = "chemical_reaction"  # Chemical reaction diagram
    PROTEIN_STRUCTURE = "protein_structure"  # Protein 3D structure


# ============================================================================
# Models
# ============================================================================


class WidgetRequest(BaseModel):
    """Request for a widget."""
    query: str
    widget_type: Optional[WidgetType] = None
    parameters: Dict[str, Any] = Field(default_factory=dict)
    size: str = "medium"  # "small", "medium", "large", "fullscreen"


class WidgetData(BaseModel):
    """Widget data to render in the client."""
    widget_id: str
    widget_type: WidgetType
    title: str
    description: str
    data: Dict[str, Any]
    render_config: Dict[str, Any] = Field(default_factory=dict)
    size: str = "medium"
    interactive: bool = True
    timestamp: str = ""


class WidgetSuggestion(BaseModel):
    """A suggested widget for a query."""
    widget_type: WidgetType
    relevance: float
    title: str
    description: str


# ============================================================================
# Widget Generation Logic
# ============================================================================


def _suggest_widgets_for_query(query: str) -> List[WidgetSuggestion]:
    """Suggest appropriate widgets based on query content."""
    query_lower = query.lower()
    suggestions = []

    # Map-related
    if any(kw in query_lower for kw in ["where", "location", "found", "habitat", "distribution", "map", "region"]):
        suggestions.append(WidgetSuggestion(
            widget_type=WidgetType.MAP,
            relevance=0.9,
            title="Location Map",
            description="Geographic distribution map",
        ))

    # Taxonomy-related
    if any(kw in query_lower for kw in ["species", "classification", "taxonomy", "kingdom", "phylum", "genus", "family"]):
        suggestions.append(WidgetSuggestion(
            widget_type=WidgetType.TAXONOMY_TREE,
            relevance=0.95,
            title="Taxonomic Tree",
            description="Interactive taxonomic classification",
        ))

    # Chemistry-related
    if any(kw in query_lower for kw in ["molecule", "compound", "chemical", "structure", "formula", "bond"]):
        suggestions.append(WidgetSuggestion(
            widget_type=WidgetType.MOLECULE_3D,
            relevance=0.9,
            title="3D Molecule",
            description="Interactive 3D molecular structure",
        ))

    # Genetics-related
    if any(kw in query_lower for kw in ["gene", "dna", "rna", "sequence", "genome", "genetic", "mutation"]):
        suggestions.append(WidgetSuggestion(
            widget_type=WidgetType.GENETIC_VIEWER,
            relevance=0.9,
            title="Genetic Sequence",
            description="DNA/RNA sequence viewer",
        ))

    # Evolution/phylogeny
    if any(kw in query_lower for kw in ["evolution", "phylogeny", "ancestor", "diverge", "clade"]):
        suggestions.append(WidgetSuggestion(
            widget_type=WidgetType.PHYLOGENETIC_TREE,
            relevance=0.9,
            title="Phylogenetic Tree",
            description="Evolutionary relationship tree",
        ))

    # Weather/climate
    if any(kw in query_lower for kw in ["weather", "climate", "temperature", "forecast", "storm", "precipitation"]):
        suggestions.append(WidgetSuggestion(
            widget_type=WidgetType.WEATHER_MAP,
            relevance=0.9,
            title="Weather Map",
            description="Weather/climate visualization",
        ))

    # Simulation
    if any(kw in query_lower for kw in ["simulate", "simulation", "model", "predict", "physics"]):
        suggestions.append(WidgetSuggestion(
            widget_type=WidgetType.SIMULATION,
            relevance=0.85,
            title="Simulation",
            description="Interactive simulation",
        ))

    # Species information
    if any(kw in query_lower for kw in ["mushroom", "fungus", "plant", "animal", "bird", "insect", "fish"]):
        suggestions.append(WidgetSuggestion(
            widget_type=WidgetType.SPECIES_CARD,
            relevance=0.85,
            title="Species Card",
            description="Detailed species information card",
        ))
        suggestions.append(WidgetSuggestion(
            widget_type=WidgetType.IMAGE_GALLERY,
            relevance=0.8,
            title="Species Images",
            description="Photo gallery of the species",
        ))

    # Protein/structure
    if any(kw in query_lower for kw in ["protein", "enzyme", "folding", "alphafold", "structure"]):
        suggestions.append(WidgetSuggestion(
            widget_type=WidgetType.PROTEIN_STRUCTURE,
            relevance=0.9,
            title="Protein Structure",
            description="3D protein structure viewer",
        ))

    # Ecosystem
    if any(kw in query_lower for kw in ["ecosystem", "food web", "symbiosis", "mycelium network", "interaction"]):
        suggestions.append(WidgetSuggestion(
            widget_type=WidgetType.ECOSYSTEM_MODEL,
            relevance=0.85,
            title="Ecosystem Model",
            description="Interactive ecosystem interaction model",
        ))

    # Chemical reaction
    if any(kw in query_lower for kw in ["reaction", "synthesis", "catalyst", "reagent", "yield"]):
        suggestions.append(WidgetSuggestion(
            widget_type=WidgetType.CHEMICAL_REACTION,
            relevance=0.9,
            title="Chemical Reaction",
            description="Reaction pathway diagram",
        ))

    # Sort by relevance
    suggestions.sort(key=lambda s: s.relevance, reverse=True)
    return suggestions[:5]  # Max 5 suggestions


def _generate_map_widget(query: str, params: Dict[str, Any]) -> WidgetData:
    """Generate a map widget."""
    return WidgetData(
        widget_id=f"map_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
        widget_type=WidgetType.MAP,
        title=f"Distribution Map: {query[:50]}",
        description="Geographic distribution map showing observation locations",
        data={
            "type": "geojson",
            "center": params.get("center", [0, 0]),
            "zoom": params.get("zoom", 3),
            "markers": params.get("markers", []),
            "heatmap_data": params.get("heatmap_data", []),
            "layers": ["observations", "habitats"],
        },
        render_config={
            "renderer": "mapbox",
            "style": "satellite-streets",
            "controls": ["zoom", "search", "layers"],
        },
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


def _generate_taxonomy_tree_widget(query: str, params: Dict[str, Any]) -> WidgetData:
    """Generate a taxonomy tree widget."""
    return WidgetData(
        widget_id=f"taxon_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
        widget_type=WidgetType.TAXONOMY_TREE,
        title=f"Taxonomy: {query[:50]}",
        description="Interactive taxonomic classification tree",
        data={
            "root": params.get("root_taxon", "Life"),
            "levels": ["Kingdom", "Phylum", "Class", "Order", "Family", "Genus", "Species"],
            "nodes": params.get("nodes", []),
            "highlighted_path": params.get("path", []),
        },
        render_config={
            "renderer": "d3_tree",
            "collapsible": True,
            "searchable": True,
            "show_images": True,
        },
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


def _generate_species_card_widget(query: str, params: Dict[str, Any]) -> WidgetData:
    """Generate a species information card widget."""
    return WidgetData(
        widget_id=f"species_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
        widget_type=WidgetType.SPECIES_CARD,
        title=f"Species: {params.get('scientific_name', query[:50])}",
        description="Detailed species information card",
        data={
            "scientific_name": params.get("scientific_name", ""),
            "common_name": params.get("common_name", ""),
            "taxonomy": params.get("taxonomy", {}),
            "description": params.get("description", ""),
            "images": params.get("images", []),
            "habitat": params.get("habitat", ""),
            "distribution": params.get("distribution", ""),
            "conservation_status": params.get("conservation_status", ""),
            "observations_count": params.get("observations_count", 0),
            "genetic_data_available": params.get("genetic_data", False),
        },
        render_config={
            "renderer": "species_card",
            "show_map": True,
            "show_images": True,
            "show_taxonomy": True,
        },
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


def _generate_molecule_widget(query: str, params: Dict[str, Any]) -> WidgetData:
    """Generate a 3D molecule widget."""
    return WidgetData(
        widget_id=f"mol_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
        widget_type=WidgetType.MOLECULE_3D,
        title=f"Molecule: {params.get('name', query[:50])}",
        description="Interactive 3D molecular structure",
        data={
            "smiles": params.get("smiles", ""),
            "pdb_id": params.get("pdb_id", ""),
            "formula": params.get("formula", ""),
            "molecular_weight": params.get("molecular_weight", 0),
            "properties": params.get("properties", {}),
        },
        render_config={
            "renderer": "3dmol",
            "style": "ball_and_stick",
            "rotatable": True,
            "show_labels": True,
        },
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


# Widget type -> generator mapping
WIDGET_GENERATORS = {
    WidgetType.MAP: _generate_map_widget,
    WidgetType.TAXONOMY_TREE: _generate_taxonomy_tree_widget,
    WidgetType.SPECIES_CARD: _generate_species_card_widget,
    WidgetType.MOLECULE_3D: _generate_molecule_widget,
}


# ============================================================================
# Endpoints
# ============================================================================


@router.get("/health")
async def widgets_health():
    """Check widget system health."""
    return {
        "status": "healthy",
        "available_widget_types": [wt.value for wt in WidgetType],
        "total_types": len(WidgetType),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.post("/suggest")
async def suggest_widgets(request: WidgetRequest) -> Dict[str, Any]:
    """Suggest appropriate widgets for a query."""
    suggestions = _suggest_widgets_for_query(request.query)
    return {
        "status": "success",
        "query": request.query,
        "suggestions": [s.model_dump() for s in suggestions],
        "count": len(suggestions),
    }


@router.post("/generate")
async def generate_widget(request: WidgetRequest) -> Dict[str, Any]:
    """Generate a widget for a query."""
    widget_type = request.widget_type

    # Auto-suggest if not specified
    if widget_type is None:
        suggestions = _suggest_widgets_for_query(request.query)
        if not suggestions:
            return {"status": "no_widget", "message": "No appropriate widget for this query"}
        widget_type = suggestions[0].widget_type

    # Generate widget
    generator = WIDGET_GENERATORS.get(widget_type)
    if generator:
        widget = generator(request.query, request.parameters)
        widget.size = request.size
        return {"status": "success", "widget": widget.model_dump()}

    # Default widget
    return {
        "status": "success",
        "widget": WidgetData(
            widget_id=f"generic_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
            widget_type=widget_type,
            title=f"{widget_type.value}: {request.query[:50]}",
            description=f"Interactive {widget_type.value} visualization",
            data=request.parameters,
            render_config={"renderer": "generic"},
            size=request.size,
            timestamp=datetime.now(timezone.utc).isoformat(),
        ).model_dump(),
    }


@router.get("/types")
async def list_widget_types() -> Dict[str, Any]:
    """List all available widget types."""
    return {
        "status": "success",
        "types": [
            {
                "type": wt.value,
                "name": wt.name.replace("_", " ").title(),
                "description": f"Interactive {wt.value.replace('_', ' ')} visualization",
            }
            for wt in WidgetType
        ],
        "total": len(WidgetType),
    }


@router.post("/batch")
async def generate_batch_widgets(queries: List[WidgetRequest]) -> Dict[str, Any]:
    """Generate multiple widgets for a complex response."""
    widgets = []
    for req in queries[:10]:  # Max 10 widgets per batch
        suggestions = _suggest_widgets_for_query(req.query)
        widget_type = req.widget_type or (suggestions[0].widget_type if suggestions else WidgetType.CHART)

        generator = WIDGET_GENERATORS.get(widget_type)
        if generator:
            widget = generator(req.query, req.parameters)
            widgets.append(widget.model_dump())

    return {
        "status": "success",
        "widgets": widgets,
        "count": len(widgets),
    }
