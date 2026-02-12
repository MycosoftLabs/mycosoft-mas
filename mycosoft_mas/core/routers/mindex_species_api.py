"""
MINDEX Species API Router - Feb 5, 2026

Comprehensive API endpoints for MINDEX species, images, sequences, research, and compounds.
This is the canonical data layer for all Mycosoft applications.
"""

from fastapi import APIRouter, HTTPException, Query, Body, Path, Depends
from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/mindex", tags=["MINDEX"])


# =============================================================================
# Request/Response Models
# =============================================================================

class SpeciesSearchRequest(BaseModel):
    query: str
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)
    include_images: bool = False
    include_sequences: bool = False


class SpeciesResponse(BaseModel):
    id: int
    scientific_name: str
    common_name: Optional[str] = None
    kingdom: str = "Fungi"
    phylum: Optional[str] = None
    class_name: Optional[str] = None
    order: Optional[str] = None
    family: Optional[str] = None
    genus: Optional[str] = None
    rank: str = "species"
    author: Optional[str] = None
    year: Optional[int] = None
    gbif_key: Optional[int] = None
    inat_id: Optional[int] = None
    mycobank_id: Optional[str] = None
    image_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    source: Optional[str] = None
    source_url: Optional[str] = None


class ImageResponse(BaseModel):
    id: str
    species_id: Optional[int] = None
    scientific_name: str
    url: str
    thumbnail_url: Optional[str] = None
    attribution: Optional[str] = None
    license: Optional[str] = None
    photographer: Optional[str] = None
    observation_url: Optional[str] = None
    quality_score: float = 0.5
    source: str


class SequenceResponse(BaseModel):
    id: int
    accession: str
    scientific_name: str
    gene_region: Optional[str] = None
    sequence_length: int
    gc_content: Optional[float] = None
    organism: Optional[str] = None
    strain: Optional[str] = None
    country: Optional[str] = None
    source: str = "GenBank"
    source_url: Optional[str] = None


class ResearchPaperResponse(BaseModel):
    id: int
    pmid: Optional[str] = None
    doi: Optional[str] = None
    title: str
    authors: List[Dict[str, Any]] = []
    journal: Optional[str] = None
    year: Optional[int] = None
    abstract: Optional[str] = None
    keywords: List[str] = []
    related_species: List[str] = []
    is_open_access: bool = False
    source_url: Optional[str] = None


class CompoundResponse(BaseModel):
    id: int
    name: str
    iupac_name: Optional[str] = None
    molecular_formula: Optional[str] = None
    molecular_weight: Optional[float] = None
    smiles: Optional[str] = None
    compound_class: Optional[str] = None
    producing_species: List[str] = []
    bioactivity: List[Dict[str, Any]] = []
    toxicity_class: Optional[str] = None
    source: str
    source_url: Optional[str] = None


class WebResultResponse(BaseModel):
    """A semantic web search result (Exa)."""
    url: str
    title: str
    score: float = 0.0
    published_date: Optional[str] = None
    author: Optional[str] = None
    text: Optional[str] = None
    highlights: List[str] = []
    summary: Optional[str] = None
    source: str = "exa"


class UnifiedSearchResponse(BaseModel):
    query: str
    total_results: int
    species: List[SpeciesResponse] = []
    images: List[ImageResponse] = []
    sequences: List[SequenceResponse] = []
    papers: List[ResearchPaperResponse] = []
    compounds: List[CompoundResponse] = []
    web: List[WebResultResponse] = []


# =============================================================================
# Database connection helper (placeholder - inject real connection)
# =============================================================================

async def get_db():
    """Get database connection. Override in production."""
    # This should be replaced with actual database connection
    from mycosoft_mas.mindex.database import get_mindex_db
    return await get_mindex_db()


# =============================================================================
# Species Endpoints
# =============================================================================

@router.get("/species/search", response_model=List[SpeciesResponse])
async def search_species(
    q: str = Query(..., min_length=2, description="Search query"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    include_images: bool = Query(False),
):
    """
    Search for fungal species by name.
    
    Searches scientific names, common names, and synonyms.
    """
    try:
        db = await get_db()
        
        query = """
        SELECT 
            t.id, t.scientific_name, t.common_name, t.kingdom, t.phylum,
            t.class as class_name, t."order", t.family, t.genus, t.rank,
            t.author, t.year, t.gbif_key, t.inat_id, t.source_id as mycobank_id,
            t.source, t.source_url,
            COALESCE(si.image_url, t.thumbnail_url) as image_url
        FROM core.taxon t
        LEFT JOIN core.species_with_images si ON t.scientific_name = si.scientific_name
        WHERE 
            t.scientific_name ILIKE $1
            OR t.common_name ILIKE $1
            OR t.synonyms::text ILIKE $1
        ORDER BY 
            CASE WHEN t.scientific_name ILIKE $2 THEN 0 ELSE 1 END,
            t.scientific_name
        LIMIT $3 OFFSET $4
        """
        
        search_pattern = f"%{q}%"
        exact_pattern = f"{q}%"
        
        rows = await db.fetch(query, search_pattern, exact_pattern, limit, offset)
        
        return [SpeciesResponse(**dict(row)) for row in rows]
        
    except Exception as e:
        logger.error(f"Species search error: {e}")
        # Fallback to empty results on error
        return []


@router.get("/species/{species_id}", response_model=SpeciesResponse)
async def get_species(
    species_id: int = Path(..., description="Species/taxon ID"),
):
    """Get detailed species information by ID."""
    try:
        db = await get_db()
        
        query = """
        SELECT 
            t.id, t.scientific_name, t.common_name, t.kingdom, t.phylum,
            t.class as class_name, t."order", t.family, t.genus, t.rank,
            t.author, t.year, t.gbif_key, t.inat_id, t.source_id as mycobank_id,
            t.source, t.source_url,
            COALESCE(si.image_url, t.thumbnail_url) as image_url
        FROM core.taxon t
        LEFT JOIN core.species_with_images si ON t.scientific_name = si.scientific_name
        WHERE t.id = $1
        """
        
        row = await db.fetchone(query, species_id)
        
        if not row:
            raise HTTPException(status_code=404, detail="Species not found")
        
        return SpeciesResponse(**dict(row))
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get species error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/species/by-name/{scientific_name:path}", response_model=SpeciesResponse)
async def get_species_by_name(
    scientific_name: str = Path(..., description="Scientific name"),
):
    """Get species by scientific name."""
    try:
        db = await get_db()
        
        query = """
        SELECT 
            t.id, t.scientific_name, t.common_name, t.kingdom, t.phylum,
            t.class as class_name, t."order", t.family, t.genus, t.rank,
            t.author, t.year, t.gbif_key, t.inat_id, t.source_id as mycobank_id,
            t.source, t.source_url,
            COALESCE(si.image_url, t.thumbnail_url) as image_url
        FROM core.taxon t
        LEFT JOIN core.species_with_images si ON t.scientific_name = si.scientific_name
        WHERE t.scientific_name ILIKE $1
        LIMIT 1
        """
        
        row = await db.fetchone(query, scientific_name)
        
        if not row:
            raise HTTPException(status_code=404, detail="Species not found")
        
        return SpeciesResponse(**dict(row))
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get species by name error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# =============================================================================
# Images Endpoints
# =============================================================================

@router.get("/images/for-species/{species_id}", response_model=List[ImageResponse])
async def get_images_for_species(
    species_id: int = Path(..., description="Species ID"),
    limit: int = Query(10, ge=1, le=50),
):
    """Get images for a species by ID."""
    try:
        db = await get_db()
        
        query = """
        SELECT 
            si.id::text, si.taxon_id as species_id, si.scientific_name,
            b.original_url as url, 
            COALESCE(b.file_path, b.original_url) as thumbnail_url,
            si.attribution, si.license, si.photographer,
            si.observation_url, si.quality_score, b.source
        FROM core.species_images si
        JOIN core.blobs b ON si.blob_id = b.id
        WHERE si.taxon_id = $1
        ORDER BY si.is_primary DESC, si.quality_score DESC
        LIMIT $2
        """
        
        rows = await db.fetch(query, species_id, limit)
        
        return [ImageResponse(**dict(row)) for row in rows]
        
    except Exception as e:
        logger.error(f"Get images error: {e}")
        return []


@router.get("/images/search", response_model=List[ImageResponse])
async def search_images(
    q: str = Query(..., min_length=2, description="Species name to search"),
    limit: int = Query(20, ge=1, le=50),
):
    """Search images by species name."""
    try:
        db = await get_db()
        
        query = """
        SELECT 
            si.id::text, si.taxon_id as species_id, si.scientific_name,
            b.original_url as url,
            COALESCE(b.file_path, b.original_url) as thumbnail_url,
            si.attribution, si.license, si.photographer,
            si.observation_url, si.quality_score, b.source
        FROM core.species_images si
        JOIN core.blobs b ON si.blob_id = b.id
        WHERE si.scientific_name ILIKE $1
        ORDER BY si.is_primary DESC, si.quality_score DESC
        LIMIT $2
        """
        
        rows = await db.fetch(query, f"%{q}%", limit)
        
        return [ImageResponse(**dict(row)) for row in rows]
        
    except Exception as e:
        logger.error(f"Search images error: {e}")
        return []


# =============================================================================
# DNA Sequences Endpoints
# =============================================================================

@router.get("/sequences/for-species/{species_id}", response_model=List[SequenceResponse])
async def get_sequences_for_species(
    species_id: int = Path(..., description="Species ID"),
    gene_region: Optional[str] = Query(None, description="Filter by gene region (ITS, LSU, etc.)"),
    limit: int = Query(20, ge=1, le=100),
):
    """Get DNA sequences for a species by ID."""
    try:
        db = await get_db()
        
        query = """
        SELECT 
            ds.id, ds.accession, ds.scientific_name, ds.gene_region,
            ds.sequence_length, ds.gc_content, ds.organism, ds.strain,
            ds.country, ds.source, ds.source_url
        FROM core.dna_sequences ds
        WHERE ds.taxon_id = $1
        """
        
        params = [species_id]
        
        if gene_region:
            query += " AND ds.gene_region = $2"
            params.append(gene_region)
            query += " ORDER BY ds.sequence_length DESC LIMIT $3"
            params.append(limit)
        else:
            query += " ORDER BY ds.sequence_length DESC LIMIT $2"
            params.append(limit)
        
        rows = await db.fetch(query, *params)
        
        return [SequenceResponse(**dict(row)) for row in rows]
        
    except Exception as e:
        logger.error(f"Get sequences error: {e}")
        return []


@router.get("/sequences/search", response_model=List[SequenceResponse])
async def search_sequences(
    q: str = Query(..., min_length=2, description="Species name or accession"),
    gene_region: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
):
    """Search DNA sequences by species name or accession."""
    try:
        db = await get_db()
        
        query = """
        SELECT 
            ds.id, ds.accession, ds.scientific_name, ds.gene_region,
            ds.sequence_length, ds.gc_content, ds.organism, ds.strain,
            ds.country, ds.source, ds.source_url
        FROM core.dna_sequences ds
        WHERE (ds.scientific_name ILIKE $1 OR ds.accession ILIKE $1)
        """
        
        params = [f"%{q}%"]
        
        if gene_region:
            query += " AND ds.gene_region = $2"
            params.append(gene_region)
            query += " ORDER BY ds.sequence_length DESC LIMIT $3"
            params.append(limit)
        else:
            query += " ORDER BY ds.sequence_length DESC LIMIT $2"
            params.append(limit)
        
        rows = await db.fetch(query, *params)
        
        return [SequenceResponse(**dict(row)) for row in rows]
        
    except Exception as e:
        logger.error(f"Search sequences error: {e}")
        return []


@router.get("/sequences/{accession}", response_model=SequenceResponse)
async def get_sequence_by_accession(
    accession: str = Path(..., description="GenBank accession number"),
):
    """Get a specific DNA sequence by accession number."""
    try:
        db = await get_db()
        
        query = """
        SELECT 
            ds.id, ds.accession, ds.scientific_name, ds.gene_region,
            ds.sequence_length, ds.gc_content, ds.organism, ds.strain,
            ds.country, ds.source, ds.source_url
        FROM core.dna_sequences ds
        WHERE ds.accession = $1
        """
        
        row = await db.fetchone(query, accession)
        
        if not row:
            raise HTTPException(status_code=404, detail="Sequence not found")
        
        return SequenceResponse(**dict(row))
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get sequence error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# =============================================================================
# Research Papers Endpoints
# =============================================================================

@router.get("/research/for-species/{species_id}", response_model=List[ResearchPaperResponse])
async def get_research_for_species(
    species_id: int = Path(..., description="Species ID"),
    limit: int = Query(20, ge=1, le=100),
):
    """Get research papers related to a species."""
    try:
        db = await get_db()
        
        # First get the species name
        species_query = "SELECT scientific_name FROM core.taxon WHERE id = $1"
        species_row = await db.fetchone(species_query, species_id)
        
        if not species_row:
            return []
        
        scientific_name = species_row["scientific_name"]
        
        query = """
        SELECT 
            rp.id, rp.pmid, rp.doi, rp.title, rp.authors, rp.journal,
            rp.year, rp.abstract, rp.keywords, rp.related_species,
            rp.is_open_access, rp.source_url
        FROM core.research_papers rp
        WHERE $1 = ANY(rp.related_species)
        ORDER BY rp.year DESC, rp.citation_count DESC
        LIMIT $2
        """
        
        rows = await db.fetch(query, scientific_name, limit)
        
        return [ResearchPaperResponse(**dict(row)) for row in rows]
        
    except Exception as e:
        logger.error(f"Get research error: {e}")
        return []


@router.get("/research/search", response_model=List[ResearchPaperResponse])
async def search_research(
    q: str = Query(..., min_length=2, description="Search query"),
    year_from: Optional[int] = Query(None),
    year_to: Optional[int] = Query(None),
    limit: int = Query(20, ge=1, le=100),
):
    """Search research papers by title, abstract, or keywords."""
    try:
        db = await get_db()
        
        query = """
        SELECT 
            rp.id, rp.pmid, rp.doi, rp.title, rp.authors, rp.journal,
            rp.year, rp.abstract, rp.keywords, rp.related_species,
            rp.is_open_access, rp.source_url
        FROM core.research_papers rp
        WHERE (
            rp.title ILIKE $1 
            OR rp.abstract ILIKE $1 
            OR $2 = ANY(rp.keywords)
            OR $2 = ANY(rp.related_species)
        )
        """
        
        params = [f"%{q}%", q]
        param_idx = 3
        
        if year_from:
            query += f" AND rp.year >= ${param_idx}"
            params.append(year_from)
            param_idx += 1
        
        if year_to:
            query += f" AND rp.year <= ${param_idx}"
            params.append(year_to)
            param_idx += 1
        
        query += f" ORDER BY rp.year DESC, rp.citation_count DESC LIMIT ${param_idx}"
        params.append(limit)
        
        rows = await db.fetch(query, *params)
        
        return [ResearchPaperResponse(**dict(row)) for row in rows]
        
    except Exception as e:
        logger.error(f"Search research error: {e}")
        return []


# =============================================================================
# Compounds Endpoints
# =============================================================================

@router.get("/compounds/for-species/{species_id}", response_model=List[CompoundResponse])
async def get_compounds_for_species(
    species_id: int = Path(..., description="Species ID"),
    limit: int = Query(20, ge=1, le=100),
):
    """Get chemical compounds produced by a species."""
    try:
        db = await get_db()
        
        # First get the species name
        species_query = "SELECT scientific_name FROM core.taxon WHERE id = $1"
        species_row = await db.fetchone(species_query, species_id)
        
        if not species_row:
            return []
        
        scientific_name = species_row["scientific_name"]
        
        query = """
        SELECT 
            c.id, c.name, c.iupac_name, c.molecular_formula, c.molecular_weight,
            c.smiles, c.compound_class, c.producing_species, c.bioactivity,
            c.toxicity_class, c.source, c.source_url
        FROM core.compounds c
        WHERE $1 = ANY(c.producing_species)
        ORDER BY c.name
        LIMIT $2
        """
        
        rows = await db.fetch(query, scientific_name, limit)
        
        return [CompoundResponse(**dict(row)) for row in rows]
        
    except Exception as e:
        logger.error(f"Get compounds error: {e}")
        return []


@router.get("/compounds/search", response_model=List[CompoundResponse])
async def search_compounds(
    q: str = Query(..., min_length=2, description="Compound name or class"),
    compound_class: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
):
    """Search chemical compounds by name or class."""
    try:
        db = await get_db()
        
        query = """
        SELECT 
            c.id, c.name, c.iupac_name, c.molecular_formula, c.molecular_weight,
            c.smiles, c.compound_class, c.producing_species, c.bioactivity,
            c.toxicity_class, c.source, c.source_url
        FROM core.compounds c
        WHERE c.name ILIKE $1 OR c.iupac_name ILIKE $1
        """
        
        params = [f"%{q}%"]
        
        if compound_class:
            query += " AND c.compound_class = $2"
            params.append(compound_class)
            query += " ORDER BY c.name LIMIT $3"
            params.append(limit)
        else:
            query += " ORDER BY c.name LIMIT $2"
            params.append(limit)
        
        rows = await db.fetch(query, *params)
        
        return [CompoundResponse(**dict(row)) for row in rows]
        
    except Exception as e:
        logger.error(f"Search compounds error: {e}")
        return []


# =============================================================================
# Unified Search Endpoint
# =============================================================================

@router.get("/unified/search", response_model=UnifiedSearchResponse)
async def unified_search(
    q: str = Query(..., min_length=2, description="Search query"),
    include_species: bool = Query(True),
    include_images: bool = Query(False),
    include_sequences: bool = Query(False),
    include_research: bool = Query(False),
    include_compounds: bool = Query(False),
    include_web: bool = Query(False, description="Include Exa semantic web results (requires EXA_API_KEY)"),
    limit: int = Query(10, ge=1, le=50),
):
    """
    Unified search across all MINDEX data types.
    
    This is the primary endpoint for search applications.
    """
    results = UnifiedSearchResponse(query=q, total_results=0)
    
    try:
        if include_species:
            species = await search_species(q=q, limit=limit)
            results.species = species
            results.total_results += len(species)
        
        if include_images:
            images = await search_images(q=q, limit=limit)
            results.images = images
            results.total_results += len(images)
        
        if include_sequences:
            sequences = await search_sequences(q=q, limit=limit)
            results.sequences = sequences
            results.total_results += len(sequences)
        
        if include_research:
            papers = await search_research(q=q, limit=limit)
            results.papers = papers
            results.total_results += len(papers)
        
        if include_compounds:
            compounds = await search_compounds(q=q, limit=limit)
            results.compounds = compounds
            results.total_results += len(compounds)

        if include_web:
            exa = None
            try:
                from mycosoft_mas.integrations.exa_client import ExaClient

                exa = ExaClient()
                exa_resp = await exa.semantic_search(query=q, num_results=limit)
                results.web = [
                    WebResultResponse(
                        url=r.url,
                        title=r.title,
                        score=r.score,
                        published_date=r.published_date,
                        author=r.author,
                        text=r.text,
                        highlights=r.highlights,
                        summary=r.summary,
                    )
                    for r in exa_resp.results
                    if r.url and r.title
                ]
                results.total_results += len(results.web)
            except Exception as e:
                logger.error(f"Exa web search error: {e}")
            finally:
                if exa is not None:
                    try:
                        await exa.close()
                    except Exception:
                        pass
        
    except Exception as e:
        logger.error(f"Unified search error: {e}")
    
    return results


# =============================================================================
# Stats Endpoint
# =============================================================================

@router.get("/stats")
async def get_mindex_stats():
    """Get MINDEX database statistics."""
    try:
        db = await get_db()
        
        stats = {}
        
        # Count tables
        tables = [
            ("species", "core.taxon"),
            ("images", "core.species_images"),
            ("sequences", "core.dna_sequences"),
            ("papers", "core.research_papers"),
            ("compounds", "core.compounds"),
            ("blobs", "core.blobs"),
        ]
        
        for name, table in tables:
            try:
                row = await db.fetchone(f"SELECT COUNT(*) as count FROM {table}")
                stats[name] = row["count"] if row else 0
            except Exception:
                stats[name] = 0
        
        stats["last_updated"] = datetime.utcnow().isoformat()
        
        return stats
        
    except Exception as e:
        logger.error(f"Get stats error: {e}")
        return {
            "species": 0,
            "images": 0,
            "sequences": 0,
            "papers": 0,
            "compounds": 0,
            "blobs": 0,
            "last_updated": datetime.utcnow().isoformat(),
            "error": str(e),
        }
