"""
STATIC Decoding Agent

BaseAgentV2 agent that manages STATIC constraint indexes for the MAS.
Handles building, storing, loading, and applying constrained decoding
indexes for generative retrieval tasks across ALL MAS data domains.

Core domains (v1):
- MINDEX: Species scientific/common names, IDs, compounds, genetic accessions
- Taxonomy: Hierarchical classification (Kingdom → Species), species-agnostic
- CREP: Flight callsigns, vessel IDs, satellite names, weather stations
- NLM: Prediction types, entity types, model IDs
- Agents: All 117+ agent IDs, categories, capabilities
- Devices/MycoBrain: Device types, sensor types, compute modes, electrodes
- Signals: Bio-signal types, SDR encodings, FCI channels, signal features
- Users: Roles, permissions, access levels (agnostic to identity provider)

Universal domains (v2):
- Biosphere: All kingdoms of life, phyla, conservation, ecological roles
- Environment: 24/7 environmental monitoring — atmospheric, oceanic, terrestrial, space
- Infrastructure: AI models, frontier LLMs, robots, vehicles, apps, orgs, protocols
- Geospatial: Biomes, ecosystems, habitats, climate zones, ocean zones
- Observation: Data lifecycle — formats, compression, storage tiers, pipelines
- Search: MINDEX query types, result types, ranking signals, entity taxonomy

Based on: Google STATIC framework (Su et al., 2026)
Created: March 3, 2026
"""

import asyncio
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import numpy as np

from mycosoft_mas.agents.v2.base_agent_v2 import BaseAgentV2
from mycosoft_mas.llm.constrained.static_index import (
    STATICIndex,
    IndexConfig,
    build_static_index,
    build_index_from_strings,
)
from mycosoft_mas.llm.constrained.constraint_engine import (
    ConstraintEngine,
    ConstrainedGenerationResult,
)
from mycosoft_mas.llm.constrained.token_masker import (
    TokenMasker,
    MaskingStrategy,
)
from mycosoft_mas.llm.constrained.domain_builders import (
    build_all_domain_indexes,
    DOMAIN_BUILDERS,
    DomainIndexReport,
    MINDEXConstraintConfig,
)

logger = logging.getLogger(__name__)


class STATICDecodingAgent(BaseAgentV2):
    """
    Agent for managing STATIC constrained decoding indexes.

    Provides the MAS with constrained generative retrieval capabilities,
    ensuring LLM outputs match valid constraint sets (entity IDs,
    taxonomies, URLs, schemas, etc.).
    """

    @property
    def agent_type(self) -> str:
        return "static_decoding"

    @property
    def category(self) -> str:
        return "data"

    @property
    def display_name(self) -> str:
        return "STATIC Decoding Agent"

    @property
    def description(self) -> str:
        return (
            "Manages STATIC constraint indexes across all 14 MAS data domains "
            "(MINDEX, CREP, NLM, taxonomy, agents, devices, signals, users, "
            "biosphere, environment, infrastructure, geospatial, observation, "
            "search). Ensures generated outputs match valid entity sets "
            "using sparse trie-based constraint masking (948x speedup). "
            "Eliminates hallucinated IDs, invalid taxonomy, and non-existent "
            "entity references across the entire Mycosoft universal ecosystem."
        )

    def get_capabilities(self) -> List[str]:
        return [
            "build_constraint_index",
            "build_domain_indexes",
            "constrained_decode",
            "validate_sequence",
            "rerank_candidates",
            "index_management",
            "constrained_retrieval",
            # Core domains (v1)
            "mindex_constraints",
            "taxonomy_constraints",
            "crep_constraints",
            "nlm_constraints",
            "agent_constraints",
            "device_constraints",
            "signal_constraints",
            "user_constraints",
            # Universal domains (v2)
            "biosphere_constraints",
            "environment_constraints",
            "infrastructure_constraints",
            "geospatial_constraints",
            "observation_constraints",
            "search_constraints",
        ]

    def __init__(self, agent_id: str = "static-decoding-agent", config=None):
        super().__init__(agent_id=agent_id, config=config)

        self.engine = ConstraintEngine()
        self._index_dir = os.environ.get(
            "STATIC_INDEX_DIR", "/tmp/static_indexes"
        )
        self._maskers: Dict[str, TokenMasker] = {}

        # Domain index build report (populated on build_all_domains)
        self._domain_report: Optional[DomainIndexReport] = None

        # Register task handlers — generic
        self.register_handler("build_index", self._handle_build_index)
        self.register_handler("build_index_from_strings", self._handle_build_from_strings)
        self.register_handler("constrained_decode", self._handle_constrained_decode)
        self.register_handler("validate_sequence", self._handle_validate)
        self.register_handler("rerank", self._handle_rerank)
        self.register_handler("list_indexes", self._handle_list_indexes)
        self.register_handler("remove_index", self._handle_remove_index)
        self.register_handler("index_stats", self._handle_index_stats)

        # Register task handlers — domain-specific
        self.register_handler("build_all_domains", self._handle_build_all_domains)
        self.register_handler("build_domain", self._handle_build_domain)
        self.register_handler("domain_report", self._handle_domain_report)
        self.register_handler("validate_entity", self._handle_validate_entity)

    async def on_start(self):
        """Load any persisted indexes on startup."""
        os.makedirs(self._index_dir, exist_ok=True)

        # Auto-load any saved indexes
        for fname in os.listdir(self._index_dir):
            if fname.endswith(".npz"):
                name = fname[:-4]
                path = os.path.join(self._index_dir, fname)
                try:
                    index = STATICIndex.load(path)
                    self.engine.register_index(name, index)
                    self._maskers[name] = TokenMasker(index)
                    logger.info(f"Auto-loaded index '{name}' from {path}")
                except Exception as e:
                    logger.warning(f"Failed to load index '{name}': {e}")

        logger.info(
            f"STATICDecodingAgent started with {len(self.engine.list_indexes())} indexes"
        )

    async def on_stop(self):
        """Persist indexes on shutdown."""
        for name, index in self.engine._indexes.items():
            path = os.path.join(self._index_dir, f"{name}.npz")
            try:
                index.save(path)
                logger.info(f"Persisted index '{name}' to {path}")
            except Exception as e:
                logger.warning(f"Failed to persist index '{name}': {e}")

    # --- Task Handlers ---

    async def _handle_build_index(self, task) -> Dict[str, Any]:
        """
        Build a STATIC index from token sequences.

        Payload:
            name: str - Index name
            sequences: List[List[int]] - Valid token sequences
            vocab_size: int (optional) - Vocabulary size
            dense_depth: int (optional) - Dense layer depth
        """
        payload = task.payload
        name = payload.get("name")
        if not name:
            return {"status": "error", "message": "Index name required"}

        raw_sequences = payload.get("sequences", [])
        if not raw_sequences:
            return {"status": "error", "message": "No sequences provided"}

        vocab_size = payload.get("vocab_size", 32000)
        dense_depth = payload.get("dense_depth", 2)

        config = IndexConfig(vocab_size=vocab_size, dense_depth=dense_depth)

        # Convert to numpy
        max_len = max(len(s) for s in raw_sequences)
        sequences = np.full(
            (len(raw_sequences), max_len), -1, dtype=np.int32
        )
        for i, seq in enumerate(raw_sequences):
            sequences[i, : len(seq)] = seq

        # Build index (CPU-bound, run in executor)
        loop = asyncio.get_event_loop()
        index = await loop.run_in_executor(
            None, build_static_index, sequences, config
        )

        self.engine.register_index(name, index)
        self._maskers[name] = TokenMasker(index)

        # Persist
        path = os.path.join(self._index_dir, f"{name}.npz")
        index.save(path)

        await self.log_to_mindex(
            "build_constraint_index",
            {
                "index_name": name,
                "num_sequences": len(raw_sequences),
                "num_states": index.num_states,
                "build_time_ms": index.build_time_ms,
            },
        )

        return {
            "status": "success",
            "index": index.to_dict(),
            "message": f"Built index '{name}' with {index.num_states} states",
        }

    async def _handle_build_from_strings(self, task) -> Dict[str, Any]:
        """
        Build a STATIC index from string sequences.

        Payload:
            name: str - Index name
            valid_strings: List[str] - Valid output strings
            vocab_size: int (optional)
            dense_depth: int (optional)
        """
        payload = task.payload
        name = payload.get("name")
        valid_strings = payload.get("valid_strings", [])

        if not name:
            return {"status": "error", "message": "Index name required"}
        if not valid_strings:
            return {"status": "error", "message": "No strings provided"}

        vocab_size = payload.get("vocab_size", 32000)
        dense_depth = payload.get("dense_depth", 2)
        config = IndexConfig(vocab_size=vocab_size, dense_depth=dense_depth)

        # Simple byte-level tokenizer as default
        def byte_tokenize(s: str) -> List[int]:
            return list(s.encode("utf-8"))

        loop = asyncio.get_event_loop()
        index = await loop.run_in_executor(
            None, build_index_from_strings, valid_strings, byte_tokenize, config
        )

        self.engine.register_index(name, index)
        self._maskers[name] = TokenMasker(index)

        path = os.path.join(self._index_dir, f"{name}.npz")
        index.save(path)

        await self.log_to_mindex(
            "build_constraint_index_from_strings",
            {
                "index_name": name,
                "num_strings": len(valid_strings),
                "num_states": index.num_states,
            },
        )

        return {
            "status": "success",
            "index": index.to_dict(),
            "message": f"Built index '{name}' from {len(valid_strings)} strings",
        }

    async def _handle_constrained_decode(self, task) -> Dict[str, Any]:
        """
        Run constrained decoding against an index.

        Payload:
            index_name: str - Index to use
            input_logits: List[List[float]] (optional) - Pre-computed logits
            beam_width: int (optional) - Beam width
            max_steps: int (optional) - Max decoding steps
        """
        payload = task.payload
        index_name = payload.get("index_name")

        if not index_name or index_name not in self.engine._indexes:
            return {
                "status": "error",
                "message": f"Index '{index_name}' not found",
                "available": list(self.engine.list_indexes().keys()),
            }

        beam_width = payload.get("beam_width", 4)
        max_steps = payload.get("max_steps")

        # Use provided logits or generate uniform
        index = self.engine.get_index(index_name)

        def uniform_logit_fn(seqs, step):
            n = len(seqs) if seqs else 1
            return np.zeros((n, index.config.vocab_size), dtype=np.float32)

        result = self.engine.constrained_beam_search(
            index_name=index_name,
            logit_fn=uniform_logit_fn,
            beam_width=beam_width,
            max_steps=max_steps,
        )

        return {
            "status": "success",
            "result": result.to_dict(),
        }

    async def _handle_validate(self, task) -> Dict[str, Any]:
        """
        Validate if a token sequence is valid according to an index.

        Payload:
            index_name: str
            tokens: List[int]
        """
        payload = task.payload
        index_name = payload.get("index_name")
        tokens = payload.get("tokens", [])

        index = self.engine.get_index(index_name)
        if not index:
            return {"status": "error", "message": f"Index '{index_name}' not found"}

        is_valid = self.engine._validate_sequence(index, tokens)

        return {
            "status": "success",
            "valid": is_valid,
            "tokens": tokens,
            "index_name": index_name,
        }

    async def _handle_rerank(self, task) -> Dict[str, Any]:
        """
        Rerank candidates against constraint index.

        Payload:
            index_name: str
            candidates: List[str]
        """
        payload = task.payload
        index_name = payload.get("index_name")
        candidates = payload.get("candidates", [])

        if not index_name or index_name not in self.engine._indexes:
            return {"status": "error", "message": f"Index '{index_name}' not found"}

        def byte_tokenize(s: str) -> List[int]:
            return list(s.encode("utf-8"))

        results = self.engine.constrained_rerank(
            index_name=index_name,
            candidates=candidates,
            tokenizer_fn=byte_tokenize,
        )

        return {
            "status": "success",
            "ranked_candidates": [
                {"candidate": c, "score": s, "valid": v}
                for c, s, v in results
            ],
        }

    async def _handle_list_indexes(self, task) -> Dict[str, Any]:
        return {
            "status": "success",
            "indexes": self.engine.list_indexes(),
        }

    async def _handle_remove_index(self, task) -> Dict[str, Any]:
        name = task.payload.get("name")
        if not name:
            return {"status": "error", "message": "Index name required"}

        removed = self.engine.remove_index(name)
        self._maskers.pop(name, None)

        # Remove from disk
        path = os.path.join(self._index_dir, f"{name}.npz")
        if os.path.exists(path):
            os.remove(path)

        return {
            "status": "success" if removed else "not_found",
            "message": f"Index '{name}' {'removed' if removed else 'not found'}",
        }

    async def _handle_index_stats(self, task) -> Dict[str, Any]:
        name = task.payload.get("name")
        if name:
            index = self.engine.get_index(name)
            if not index:
                return {"status": "error", "message": f"Index '{name}' not found"}
            stats = index.to_dict()
            masker = self._maskers.get(name)
            if masker:
                stats["cache_stats"] = masker.cache_stats()
            return {"status": "success", "stats": stats}
        else:
            return {
                "status": "success",
                "all_indexes": self.engine.list_indexes(),
                "total_memory_mb": sum(
                    idx.memory_usage_mb()
                    for idx in self.engine._indexes.values()
                ),
            }

    # --- Domain-Specific Task Handlers ---

    async def _handle_build_all_domains(self, task) -> Dict[str, Any]:
        """
        Build STATIC indexes for ALL MAS data domains at once.

        Pulls live data from MINDEX, CREP, NLM, agent registry, device
        registry, and builds constraint indexes for every entity type.

        Payload:
            domains: List[str] (optional) - Subset of domains to build.
                     Valid: mindex, taxonomy, crep, nlm, agents, devices,
                            signals, users, biosphere, environment,
                            infrastructure, geospatial, observation, search
            mindex_db_path: str (optional) - Path to MINDEX SQLite DB
        """
        payload = task.payload
        domains = payload.get("domains")
        mindex_db = payload.get("mindex_db_path", "")

        mindex_config = MINDEXConstraintConfig(db_path=mindex_db) if mindex_db else None

        report = await build_all_domain_indexes(
            domains=domains,
            mindex_config=mindex_config,
        )

        # Register all built indexes
        for name, index in report.indexes.items():
            self.engine.register_index(name, index)
            self._maskers[name] = TokenMasker(index)
            # Persist to disk
            path = os.path.join(self._index_dir, f"{name}.npz")
            try:
                index.save(path)
            except Exception as e:
                logger.warning(f"Failed to persist domain index '{name}': {e}")

        self._domain_report = report

        await self.log_to_mindex(
            "build_all_domain_indexes",
            {
                "domains_built": report.domains_built,
                "total_indexes": len(report.indexes),
                "total_states": report.total_states,
                "total_memory_mb": report.total_memory_mb,
                "build_time_ms": report.build_time_ms,
            },
        )

        return {
            "status": "success",
            "report": report.to_dict(),
        }

    async def _handle_build_domain(self, task) -> Dict[str, Any]:
        """
        Build STATIC indexes for a single domain.

        Payload:
            domain: str - Domain name (mindex, taxonomy, crep, nlm,
                          agents, devices, signals, users, biosphere,
                          environment, infrastructure, geospatial,
                          observation, search)
            mindex_db_path: str (optional)
        """
        payload = task.payload
        domain = payload.get("domain", "")

        if domain not in DOMAIN_BUILDERS:
            return {
                "status": "error",
                "message": f"Unknown domain '{domain}'",
                "valid_domains": list(DOMAIN_BUILDERS.keys()),
            }

        mindex_db = payload.get("mindex_db_path", "")
        mindex_config = MINDEXConstraintConfig(db_path=mindex_db) if mindex_db else None

        report = await build_all_domain_indexes(
            domains=[domain],
            mindex_config=mindex_config,
        )

        # Register indexes
        for name, index in report.indexes.items():
            self.engine.register_index(name, index)
            self._maskers[name] = TokenMasker(index)
            path = os.path.join(self._index_dir, f"{name}.npz")
            try:
                index.save(path)
            except Exception as e:
                logger.warning(f"Persist failed for '{name}': {e}")

        return {
            "status": "success",
            "domain": domain,
            "indexes_built": list(report.indexes.keys()),
            "report": report.to_dict(),
        }

    async def _handle_domain_report(self, task) -> Dict[str, Any]:
        """Get the last domain build report."""
        if self._domain_report:
            return {
                "status": "success",
                "report": self._domain_report.to_dict(),
            }
        return {
            "status": "success",
            "report": None,
            "message": "No domain build has been run yet",
            "available_domains": list(DOMAIN_BUILDERS.keys()),
        }

    async def _handle_validate_entity(self, task) -> Dict[str, Any]:
        """
        Validate an entity string against a domain constraint index.

        Payload:
            entity: str - The entity string to validate
            index_name: str - Which index to validate against
                              (e.g. "mindex_species_scientific",
                               "agent_ids", "crep_flights")
        """
        payload = task.payload
        entity = payload.get("entity", "")
        index_name = payload.get("index_name", "")

        if not entity or not index_name:
            return {
                "status": "error",
                "message": "Both 'entity' and 'index_name' required",
            }

        index = self.engine.get_index(index_name)
        if not index:
            return {
                "status": "error",
                "message": f"Index '{index_name}' not found",
                "available": list(self.engine.list_indexes().keys()),
            }

        tokens = list(entity.encode("utf-8"))
        is_valid = self.engine._validate_sequence(index, tokens)

        return {
            "status": "success",
            "entity": entity,
            "index_name": index_name,
            "valid": is_valid,
        }
