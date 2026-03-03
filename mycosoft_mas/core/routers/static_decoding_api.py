"""
STATIC Constrained Decoding API

REST API for building and using STATIC constraint indexes for
constrained LLM decoding / generative retrieval across ALL MAS domains.

Core Endpoints:
    POST /api/static/indexes           - Build new index from sequences
    POST /api/static/indexes/strings   - Build new index from strings
    GET  /api/static/indexes           - List all indexes
    GET  /api/static/indexes/{name}    - Get index details
    DELETE /api/static/indexes/{name}  - Remove an index
    POST /api/static/decode            - Run constrained decoding
    POST /api/static/validate          - Validate a sequence
    POST /api/static/rerank            - Rerank candidates
    POST /api/static/mask              - Get logit mask for a step
    GET  /api/static/health            - Health check

Domain Endpoints:
    POST /api/static/domains/build-all - Build indexes for all data domains
    POST /api/static/domains/build     - Build indexes for a single domain
    GET  /api/static/domains           - List available domains and status
    GET  /api/static/domains/report    - Get last domain build report
    POST /api/static/domains/validate  - Validate entity against domain index

Created: March 3, 2026
"""

import logging
from typing import Any, Dict, List, Optional

import numpy as np
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from mycosoft_mas.llm.constrained.static_index import (
    IndexConfig,
    STATICIndex,
    build_index_from_strings,
    build_static_index,
)
from mycosoft_mas.llm.constrained.constraint_engine import ConstraintEngine
from mycosoft_mas.llm.constrained.token_masker import MaskingStrategy, TokenMasker
from mycosoft_mas.llm.constrained.domain_builders import (
    build_all_domain_indexes,
    DOMAIN_BUILDERS,
    DomainIndexReport,
    MINDEXConstraintConfig,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/static", tags=["static-decoding"])

# Shared engine instance
_engine = ConstraintEngine()
_maskers: Dict[str, TokenMasker] = {}
_domain_report: Optional[DomainIndexReport] = None


# --- Request/Response Models ---


class BuildIndexRequest(BaseModel):
    name: str = Field(..., description="Unique name for this constraint index")
    sequences: List[List[int]] = Field(
        ..., description="Valid token sequences to index"
    )
    vocab_size: int = Field(32000, description="Vocabulary size")
    dense_depth: int = Field(2, description="Number of dense lookup layers")


class BuildIndexFromStringsRequest(BaseModel):
    name: str = Field(..., description="Unique name for this constraint index")
    valid_strings: List[str] = Field(
        ..., description="Valid output strings to constrain to"
    )
    vocab_size: int = Field(32000, description="Vocabulary size")
    dense_depth: int = Field(2, description="Number of dense lookup layers")


class ConstrainedDecodeRequest(BaseModel):
    index_name: str = Field(..., description="Name of constraint index to use")
    beam_width: int = Field(4, description="Beam search width")
    max_steps: Optional[int] = Field(None, description="Maximum decoding steps")


class ValidateRequest(BaseModel):
    index_name: str = Field(..., description="Name of constraint index")
    tokens: List[int] = Field(..., description="Token sequence to validate")


class RerankRequest(BaseModel):
    index_name: str = Field(..., description="Name of constraint index")
    candidates: List[str] = Field(..., description="Candidate strings to rerank")


class MaskRequest(BaseModel):
    index_name: str = Field(..., description="Name of constraint index")
    states: List[int] = Field(..., description="Current trie states")
    step: int = Field(..., description="Current decoding step")
    vocab_size: Optional[int] = Field(None, description="Override vocab size")


class IndexResponse(BaseModel):
    status: str
    index: Optional[Dict[str, Any]] = None
    message: Optional[str] = None


class IndexListResponse(BaseModel):
    status: str
    indexes: Dict[str, Any]
    count: int


# --- Endpoints ---


@router.get("/health")
async def health():
    """Health check for STATIC decoding service."""
    return {
        "status": "healthy",
        "service": "static-constrained-decoding",
        "framework": "STATIC (Su et al., 2026)",
        "indexes_loaded": len(_engine.list_indexes()),
    }


@router.post("/indexes", response_model=IndexResponse)
async def build_index(req: BuildIndexRequest):
    """Build a new STATIC constraint index from token sequences."""
    if not req.sequences:
        raise HTTPException(400, "No sequences provided")

    if len(req.sequences) > 10_000_000:
        raise HTTPException(400, "Maximum 10M sequences per index")

    config = IndexConfig(vocab_size=req.vocab_size, dense_depth=req.dense_depth)

    max_len = max(len(s) for s in req.sequences)
    sequences = np.full((len(req.sequences), max_len), -1, dtype=np.int32)
    for i, seq in enumerate(req.sequences):
        sequences[i, : len(seq)] = seq

    index = build_static_index(sequences, config)
    _engine.register_index(req.name, index)
    _maskers[req.name] = TokenMasker(index)

    return IndexResponse(
        status="success",
        index=index.to_dict(),
        message=f"Built index '{req.name}': {index.num_states} states, "
        f"{index.num_sequences} sequences, {index.build_time_ms:.1f}ms",
    )


@router.post("/indexes/strings", response_model=IndexResponse)
async def build_index_from_string_list(req: BuildIndexFromStringsRequest):
    """Build a STATIC constraint index from valid output strings."""
    if not req.valid_strings:
        raise HTTPException(400, "No strings provided")

    config = IndexConfig(vocab_size=req.vocab_size, dense_depth=req.dense_depth)

    def byte_tokenize(s: str) -> List[int]:
        return list(s.encode("utf-8"))

    index = build_index_from_strings(req.valid_strings, byte_tokenize, config)
    _engine.register_index(req.name, index)
    _maskers[req.name] = TokenMasker(index)

    return IndexResponse(
        status="success",
        index=index.to_dict(),
        message=f"Built index '{req.name}' from {len(req.valid_strings)} strings",
    )


@router.get("/indexes", response_model=IndexListResponse)
async def list_indexes():
    """List all registered constraint indexes."""
    indexes = _engine.list_indexes()
    return IndexListResponse(
        status="success",
        indexes=indexes,
        count=len(indexes),
    )


@router.get("/indexes/{name}")
async def get_index(name: str):
    """Get details for a specific constraint index."""
    index = _engine.get_index(name)
    if not index:
        raise HTTPException(404, f"Index '{name}' not found")

    details = index.to_dict()
    masker = _maskers.get(name)
    if masker:
        details["cache_stats"] = masker.cache_stats()

    return {"status": "success", "index": details}


@router.delete("/indexes/{name}")
async def remove_index(name: str):
    """Remove a constraint index."""
    removed = _engine.remove_index(name)
    _maskers.pop(name, None)

    if not removed:
        raise HTTPException(404, f"Index '{name}' not found")

    return {"status": "success", "message": f"Index '{name}' removed"}


@router.post("/decode")
async def constrained_decode(req: ConstrainedDecodeRequest):
    """Run constrained beam search decoding against an index."""
    index = _engine.get_index(req.index_name)
    if not index:
        raise HTTPException(
            404,
            f"Index '{req.index_name}' not found. "
            f"Available: {list(_engine.list_indexes().keys())}",
        )

    def uniform_logit_fn(seqs, step):
        n = len(seqs) if seqs else 1
        return np.zeros((n, index.config.vocab_size), dtype=np.float32)

    result = _engine.constrained_beam_search(
        index_name=req.index_name,
        logit_fn=uniform_logit_fn,
        beam_width=req.beam_width,
        max_steps=req.max_steps,
    )

    return {"status": "success", "result": result.to_dict()}


@router.post("/validate")
async def validate_sequence(req: ValidateRequest):
    """Validate whether a token sequence satisfies index constraints."""
    index = _engine.get_index(req.index_name)
    if not index:
        raise HTTPException(404, f"Index '{req.index_name}' not found")

    is_valid = _engine._validate_sequence(index, req.tokens)

    return {
        "status": "success",
        "valid": is_valid,
        "tokens": req.tokens,
        "index_name": req.index_name,
    }


@router.post("/rerank")
async def rerank_candidates(req: RerankRequest):
    """Rerank candidate strings against constraint index."""
    if req.index_name not in _engine._indexes:
        raise HTTPException(404, f"Index '{req.index_name}' not found")

    def byte_tokenize(s: str) -> List[int]:
        return list(s.encode("utf-8"))

    results = _engine.constrained_rerank(
        index_name=req.index_name,
        candidates=req.candidates,
        tokenizer_fn=byte_tokenize,
    )

    return {
        "status": "success",
        "ranked": [
            {"candidate": c, "score": s, "valid": v} for c, s, v in results
        ],
    }


@router.post("/mask")
async def get_logit_mask(req: MaskRequest):
    """
    Get the constraint logit mask for a given step and states.

    Returns which tokens are valid at this step for each beam state.
    This is the core STATIC vectorized masking operation.
    """
    if req.index_name not in _engine._indexes:
        raise HTTPException(404, f"Index '{req.index_name}' not found")

    mask = _engine.build_logit_mask(
        index_name=req.index_name,
        current_states=req.states,
        step=req.step,
        vocab_size=req.vocab_size,
    )

    # Return valid token IDs per beam (more compact than full mask)
    valid_per_beam = []
    for b in range(mask.shape[0]):
        valid_tokens = np.where(mask[b])[0].tolist()
        valid_per_beam.append(valid_tokens)

    return {
        "status": "success",
        "step": req.step,
        "valid_tokens_per_beam": valid_per_beam,
        "total_valid": [len(v) for v in valid_per_beam],
    }


# --- Domain-Specific Request Models ---


class BuildAllDomainsRequest(BaseModel):
    domains: Optional[List[str]] = Field(
        None,
        description="Domains to build. None = all. "
        "Valid: mindex, taxonomy, crep, nlm, agents, devices, signals, users",
    )
    mindex_db_path: Optional[str] = Field(
        None, description="Path to MINDEX SQLite DB"
    )


class BuildDomainRequest(BaseModel):
    domain: str = Field(
        ...,
        description="Domain to build: mindex, taxonomy, crep, nlm, "
        "agents, devices, signals, users",
    )
    mindex_db_path: Optional[str] = Field(
        None, description="Path to MINDEX SQLite DB (for mindex/taxonomy)"
    )


class DomainValidateRequest(BaseModel):
    entity: str = Field(..., description="Entity string to validate")
    index_name: str = Field(
        ...,
        description="Index to validate against (e.g. mindex_species_scientific, "
        "agent_ids, crep_flights, sensor_types)",
    )


# --- Domain Endpoints ---


@router.get("/domains")
async def list_domains():
    """
    List all available STATIC constraint domains and their current status.

    Each domain can contain multiple constraint indexes covering different
    entity types within that domain.
    """
    domain_status = {}
    all_indexes = _engine.list_indexes()

    for domain in DOMAIN_BUILDERS:
        # Find indexes belonging to this domain
        prefix_map = {
            "mindex": "mindex_",
            "taxonomy": "taxonomy_",
            "crep": "crep_",
            "nlm": "nlm_",
            "agents": "agent_",
            "devices": ["device_", "sensor_", "mycobrain_", "stimulation_", "electrode_"],
            "signals": ["signal_", "sdr_", "fci_"],
            "users": ["user_", "access_"],
        }

        prefixes = prefix_map.get(domain, [domain + "_"])
        if isinstance(prefixes, str):
            prefixes = [prefixes]

        domain_indexes = {
            name: info
            for name, info in all_indexes.items()
            if any(name.startswith(p) for p in prefixes)
        }

        domain_status[domain] = {
            "available": True,
            "indexes_loaded": len(domain_indexes),
            "index_names": list(domain_indexes.keys()),
        }

    return {
        "status": "success",
        "domains": domain_status,
        "total_domains": len(DOMAIN_BUILDERS),
        "total_indexes_loaded": len(all_indexes),
    }


@router.post("/domains/build-all")
async def build_all_domains(req: BuildAllDomainsRequest):
    """
    Build STATIC constraint indexes for all (or selected) MAS data domains.

    Pulls live data from MINDEX, CREP, NLM, agent registry, device
    registry, and builds constraint indexes for every entity type.
    Domains run concurrently for maximum performance.

    Available domains: mindex, taxonomy, crep, nlm, agents, devices,
    signals, users
    """
    global _domain_report

    mindex_config = None
    if req.mindex_db_path:
        mindex_config = MINDEXConstraintConfig(db_path=req.mindex_db_path)

    report = await build_all_domain_indexes(
        domains=req.domains,
        mindex_config=mindex_config,
    )

    # Register all indexes
    for name, index in report.indexes.items():
        _engine.register_index(name, index)
        _maskers[name] = TokenMasker(index)

    _domain_report = report

    return {
        "status": "success",
        "report": report.to_dict(),
    }


@router.post("/domains/build")
async def build_single_domain(req: BuildDomainRequest):
    """
    Build STATIC constraint indexes for a single data domain.

    This is useful for rebuilding just one domain's indexes without
    affecting others (e.g. refreshing CREP flight data).
    """
    global _domain_report

    if req.domain not in DOMAIN_BUILDERS:
        raise HTTPException(
            400,
            f"Unknown domain '{req.domain}'. "
            f"Valid: {list(DOMAIN_BUILDERS.keys())}",
        )

    mindex_config = None
    if req.mindex_db_path:
        mindex_config = MINDEXConstraintConfig(db_path=req.mindex_db_path)

    report = await build_all_domain_indexes(
        domains=[req.domain],
        mindex_config=mindex_config,
    )

    for name, index in report.indexes.items():
        _engine.register_index(name, index)
        _maskers[name] = TokenMasker(index)

    _domain_report = report

    return {
        "status": "success",
        "domain": req.domain,
        "indexes_built": list(report.indexes.keys()),
        "report": report.to_dict(),
    }


@router.get("/domains/report")
async def get_domain_report():
    """Get the last domain build report with full statistics."""
    if _domain_report:
        return {
            "status": "success",
            "report": _domain_report.to_dict(),
        }
    return {
        "status": "success",
        "report": None,
        "message": "No domain build has been run yet. "
        "POST /api/static/domains/build-all to build all indexes.",
        "available_domains": list(DOMAIN_BUILDERS.keys()),
    }


@router.post("/domains/validate")
async def validate_domain_entity(req: DomainValidateRequest):
    """
    Validate whether an entity string exists in a domain constraint index.

    This is the primary hallucination-prevention endpoint: before using
    any LLM-generated identifier, validate it here to guarantee it exists.

    Example: validate "Agaricus bisporus" against "mindex_species_scientific"
    """
    index = _engine.get_index(req.index_name)
    if not index:
        available = list(_engine.list_indexes().keys())
        raise HTTPException(
            404,
            f"Index '{req.index_name}' not found. "
            f"Available indexes: {available}",
        )

    tokens = list(req.entity.encode("utf-8"))
    is_valid = _engine._validate_sequence(index, tokens)

    return {
        "status": "success",
        "entity": req.entity,
        "index_name": req.index_name,
        "valid": is_valid,
    }
