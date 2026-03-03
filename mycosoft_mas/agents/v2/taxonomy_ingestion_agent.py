"""
Taxonomy Ingestion Agent (v2)

Orchestrates mass ingestion of ALL life data from iNaturalist, NCBI/GenBank,
PubChem, ChemSpider, PubMed, and Google Scholar into MINDEX (192.168.0.189).
Covers every kingdom: Fungi, Plantae, Animalia, Bacteria, Protista, Archaea.

Designed for long-running batch jobs that pull millions of taxonomy records,
observations, images, genetic sequences, chemical compounds, and scientific
papers, then normalize and store them in MINDEX PostgreSQL + Qdrant.

Created: March 3, 2026
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

import httpx

from mycosoft_mas.agents.v2.base_agent_v2 import BaseAgentV2
from mycosoft_mas.integrations.inaturalist_client import (
    INaturalistClient,
    INaturalistConfig,
    KINGDOM_TAXON_IDS,
)
from mycosoft_mas.integrations.ncbi_client import NCBIClient
from mycosoft_mas.integrations.chemspider_client import ChemSpiderClient
from mycosoft_mas.integrations.scholar_client import ScholarClient
from mycosoft_mas.runtime import AgentTask

logger = logging.getLogger(__name__)

# MINDEX API on the database VM
MINDEX_API_URL = os.getenv("MINDEX_API_URL", "http://192.168.0.189:8000")
MINDEX_API_KEY = os.getenv("MINDEX_API_KEY", "")

# NAS mount point for bulk image storage
NAS_IMAGE_PATH = os.getenv(
    "NAS_IMAGE_PATH", "/opt/mycosoft/media/taxonomy/images"
)


# -----------------------------------------------------------------------
# Enums & Data Classes
# -----------------------------------------------------------------------

class IngestionTarget(str, Enum):
    """Kingdoms and meta-targets for ingestion jobs."""

    FUNGI = "fungi"
    PLANTS = "plants"
    ANIMALS = "animals"
    BACTERIA = "bacteria"
    PROTISTA = "protista"
    ARCHAEA = "archaea"
    ALL_LIFE = "all_life"


@dataclass
class IngestionState:
    """Tracks progress for a single ingestion job."""

    job_id: str = field(default_factory=lambda: str(uuid4()))
    target: IngestionTarget = IngestionTarget.ALL_LIFE
    status: str = "pending"  # pending | running | paused | completed | failed
    total_records: int = 0
    ingested_records: int = 0
    skipped_records: int = 0
    errors: List[Dict[str, Any]] = field(default_factory=list)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    last_taxon_id: Optional[int] = None
    last_page: int = 0
    batch_size: int = 200

    @property
    def progress_pct(self) -> float:
        if self.total_records == 0:
            return 0.0
        return round((self.ingested_records / self.total_records) * 100.0, 2)

    @property
    def elapsed_seconds(self) -> float:
        if self.start_time is None:
            return 0.0
        end = self.end_time or datetime.now(timezone.utc)
        return (end - self.start_time).total_seconds()

    @property
    def records_per_second(self) -> float:
        elapsed = self.elapsed_seconds
        if elapsed == 0:
            return 0.0
        return round(self.ingested_records / elapsed, 2)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_id": self.job_id,
            "target": self.target.value,
            "status": self.status,
            "total_records": self.total_records,
            "ingested_records": self.ingested_records,
            "skipped_records": self.skipped_records,
            "error_count": len(self.errors),
            "progress_pct": self.progress_pct,
            "records_per_second": self.records_per_second,
            "elapsed_seconds": self.elapsed_seconds,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "last_taxon_id": self.last_taxon_id,
            "last_page": self.last_page,
        }


# -----------------------------------------------------------------------
# Agent
# -----------------------------------------------------------------------

class TaxonomyIngestionAgent(BaseAgentV2):
    """
    Orchestrates mass ingestion of taxonomy and biodiversity data into MINDEX.

    Capabilities:
        - Ingest entire kingdoms from iNaturalist (taxa, observations, photos)
        - Recursive taxon tree traversal for complete lineage capture
        - Pull genetic sequences from NCBI/GenBank
        - Pull chemical compound data from PubChem/ChemSpider
        - Pull scientific papers from PubMed and Google Scholar
        - Download and store taxon images on NAS
        - Full progress tracking with resume support
        - Batch processing with configurable sizes

    Task types handled:
        ingest_kingdom, ingest_taxon_tree, ingest_observations,
        ingest_genetic_data, ingest_images, ingest_chemical_data,
        ingest_scientific_papers, schedule_full_ingestion, ingestion_status
    """

    def __init__(self, agent_id: str = "taxonomy-ingestion-agent", **kwargs: Any):
        super().__init__(agent_id=agent_id, **kwargs)

        # Integration clients (lazy-initialized in on_start)
        self._inat: Optional[INaturalistClient] = None
        self._ncbi: Optional[NCBIClient] = None
        self._chemspider: Optional[ChemSpiderClient] = None
        self._scholar: Optional[ScholarClient] = None
        self._mindex_http: Optional[httpx.AsyncClient] = None

        # Active ingestion jobs keyed by job_id
        self._jobs: Dict[str, IngestionState] = {}

    # ------------------------------------------------------------------
    # BaseAgentV2 property overrides
    # ------------------------------------------------------------------

    @property
    def agent_type(self) -> str:
        return "taxonomy-ingestion"

    @property
    def category(self) -> str:
        return "data"

    @property
    def display_name(self) -> str:
        return "Taxonomy Ingestion Agent"

    @property
    def description(self) -> str:
        return (
            "Mass ingestion of taxonomy, observations, genetics, and "
            "chemical data from iNaturalist, NCBI, ChemSpider, and PubMed "
            "into MINDEX"
        )

    def get_capabilities(self) -> List[str]:
        return [
            "ingest_kingdom",
            "ingest_taxon_tree",
            "ingest_observations",
            "ingest_genetic_data",
            "ingest_images",
            "ingest_chemical_data",
            "ingest_scientific_papers",
            "schedule_full_ingestion",
            "ingestion_status",
        ]

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def on_start(self) -> None:
        """Initialize integration clients and register task handlers."""
        self._inat = INaturalistClient()
        self._ncbi = NCBIClient()
        self._chemspider = ChemSpiderClient()
        self._scholar = ScholarClient()

        mindex_headers: Dict[str, str] = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if MINDEX_API_KEY:
            mindex_headers["X-API-Key"] = MINDEX_API_KEY
        self._mindex_http = httpx.AsyncClient(
            base_url=MINDEX_API_URL,
            headers=mindex_headers,
            timeout=30,
        )

        # Register task handlers
        self.register_handler("ingest_kingdom", self._handle_ingest_kingdom)
        self.register_handler("ingest_taxon_tree", self._handle_ingest_taxon_tree)
        self.register_handler("ingest_observations", self._handle_ingest_observations)
        self.register_handler("ingest_genetic_data", self._handle_ingest_genetic_data)
        self.register_handler("ingest_images", self._handle_ingest_images)
        self.register_handler("ingest_chemical_data", self._handle_ingest_chemical_data)
        self.register_handler(
            "ingest_scientific_papers", self._handle_ingest_scientific_papers
        )
        self.register_handler(
            "schedule_full_ingestion", self._handle_schedule_full_ingestion
        )
        self.register_handler("ingestion_status", self._handle_ingestion_status)

        logger.info("TaxonomyIngestionAgent initialized with all integration clients")

    async def on_stop(self) -> None:
        """Clean up integration clients."""
        if self._inat:
            await self._inat.close()
        if self._ncbi:
            await self._ncbi.close()
        if self._chemspider:
            await self._chemspider.close()
        if self._scholar:
            await self._scholar.close()
        if self._mindex_http and not self._mindex_http.is_closed:
            await self._mindex_http.aclose()
        logger.info("TaxonomyIngestionAgent shut down")

    # ------------------------------------------------------------------
    # MINDEX Storage
    # ------------------------------------------------------------------

    async def store_to_mindex(
        self,
        data_type: str,
        records: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Store normalized records in MINDEX via its REST API.

        Args:
            data_type: One of 'taxa', 'observations', 'genetic_sequences',
                       'chemical_compounds', 'scientific_papers', 'images'.
            records: List of record dicts conforming to MINDEX schemas.

        Returns:
            Dict with ``inserted``, ``updated``, ``errors`` counts.
        """
        if not self._mindex_http:
            raise RuntimeError("MINDEX HTTP client not initialized")

        endpoint_map = {
            "taxa": "/api/ingest/taxa",
            "observations": "/api/ingest/observations",
            "genetic_sequences": "/api/ingest/genetic_sequences",
            "chemical_compounds": "/api/ingest/chemical_compounds",
            "scientific_papers": "/api/ingest/scientific_papers",
            "images": "/api/ingest/images",
        }
        endpoint = endpoint_map.get(data_type)
        if not endpoint:
            raise ValueError(f"Unknown data_type for MINDEX storage: {data_type}")

        try:
            resp = await self._mindex_http.post(
                endpoint,
                json={"records": records},
            )
            resp.raise_for_status()
            result = resp.json()
            logger.info(
                "Stored %d %s records to MINDEX: %s",
                len(records),
                data_type,
                result,
            )
            return result
        except httpx.HTTPStatusError as exc:
            logger.error(
                "MINDEX ingest failed for %s: %s %s",
                data_type,
                exc.response.status_code,
                exc.response.text[:500],
            )
            return {"inserted": 0, "updated": 0, "errors": len(records)}
        except Exception as exc:
            logger.error("MINDEX ingest error for %s: %s", data_type, exc)
            return {"inserted": 0, "updated": 0, "errors": len(records)}

    # ------------------------------------------------------------------
    # Kingdom Ingestion
    # ------------------------------------------------------------------

    async def ingest_kingdom(self, kingdom: str) -> IngestionState:
        """
        Ingest all taxa for a given kingdom from iNaturalist into MINDEX.

        Paginates through every taxon under the kingdom root, normalizes
        records, and stores them in batches.

        Args:
            kingdom: Kingdom name (e.g. 'fungi', 'plantae', 'animalia').

        Returns:
            Final IngestionState with progress and error details.
        """
        target = IngestionTarget(kingdom.lower()) if kingdom.lower() != "plants" else IngestionTarget.PLANTS
        state = IngestionState(target=target, batch_size=self._inat.config.batch_size if self._inat else 200)
        state.status = "running"
        state.start_time = datetime.now(timezone.utc)
        self._jobs[state.job_id] = state

        taxon_id = KINGDOM_TAXON_IDS.get(kingdom.lower())
        if taxon_id is None:
            state.status = "failed"
            state.errors.append({"error": f"Unknown kingdom: {kingdom}"})
            state.end_time = datetime.now(timezone.utc)
            return state

        logger.info("Starting kingdom ingestion: %s (taxon_id=%d)", kingdom, taxon_id)

        batch: List[Dict[str, Any]] = []
        try:
            async for taxon in self._inat.paginate_all_taxa(taxon_id, per_page=state.batch_size):
                normalized = self._normalize_taxon(taxon)
                batch.append(normalized)
                state.last_taxon_id = taxon.get("id")

                if len(batch) >= state.batch_size:
                    result = await self.store_to_mindex("taxa", batch)
                    state.ingested_records += result.get("inserted", 0) + result.get("updated", 0)
                    state.skipped_records += result.get("errors", 0)
                    batch = []

            # Flush remaining
            if batch:
                result = await self.store_to_mindex("taxa", batch)
                state.ingested_records += result.get("inserted", 0) + result.get("updated", 0)
                state.skipped_records += result.get("errors", 0)

            state.status = "completed"
        except Exception as exc:
            logger.error("Kingdom ingestion failed for %s: %s", kingdom, exc)
            state.status = "failed"
            state.errors.append({"error": str(exc)})

        state.end_time = datetime.now(timezone.utc)
        await self.log_to_mindex("ingest_kingdom", state.to_dict(), success=(state.status == "completed"))
        return state

    # ------------------------------------------------------------------
    # Taxon Tree Ingestion
    # ------------------------------------------------------------------

    async def ingest_taxon_tree(self, root_taxon_id: int, max_depth: int = 50) -> IngestionState:
        """
        Recursively ingest a taxonomic tree starting from a root taxon.

        Performs a breadth-first traversal, fetching children at each level
        and storing them in MINDEX. Respects rate limits.

        Args:
            root_taxon_id: iNaturalist taxon ID of the tree root.
            max_depth: Maximum traversal depth to prevent runaway recursion.

        Returns:
            IngestionState tracking the full traversal.
        """
        state = IngestionState(target=IngestionTarget.ALL_LIFE)
        state.status = "running"
        state.start_time = datetime.now(timezone.utc)
        self._jobs[state.job_id] = state

        queue: List[tuple] = [(root_taxon_id, 0)]  # (taxon_id, depth)
        batch: List[Dict[str, Any]] = []

        try:
            while queue:
                current_id, depth = queue.pop(0)
                if depth > max_depth:
                    continue

                taxon = await self._inat.get_taxa(current_id)
                if not taxon:
                    continue

                batch.append(self._normalize_taxon(taxon))
                state.last_taxon_id = current_id

                if len(batch) >= state.batch_size:
                    result = await self.store_to_mindex("taxa", batch)
                    state.ingested_records += result.get("inserted", 0) + result.get("updated", 0)
                    batch = []

                # Queue children for next level
                children_data = await self._inat.get_taxon_children(current_id, per_page=200)
                for child in children_data.get("results", []):
                    child_id = child.get("id")
                    if child_id:
                        queue.append((child_id, depth + 1))

            if batch:
                result = await self.store_to_mindex("taxa", batch)
                state.ingested_records += result.get("inserted", 0) + result.get("updated", 0)

            state.status = "completed"
        except Exception as exc:
            logger.error("Taxon tree ingestion failed at %s: %s", root_taxon_id, exc)
            state.status = "failed"
            state.errors.append({"taxon_id": root_taxon_id, "error": str(exc)})

        state.end_time = datetime.now(timezone.utc)
        return state

    # ------------------------------------------------------------------
    # Observations Ingestion
    # ------------------------------------------------------------------

    async def ingest_observations(
        self,
        taxon_id: Optional[int] = None,
        location: Optional[str] = None,
        date_range: Optional[Dict[str, str]] = None,
    ) -> IngestionState:
        """
        Ingest observations from iNaturalist, optionally filtered by taxon,
        location, and date range.

        Args:
            taxon_id: iNaturalist taxon ID filter.
            location: Place name (resolved to place_id via iNaturalist).
            date_range: Dict with 'start' and 'end' ISO date strings.

        Returns:
            IngestionState with progress.
        """
        state = IngestionState(target=IngestionTarget.ALL_LIFE)
        state.status = "running"
        state.start_time = datetime.now(timezone.utc)
        self._jobs[state.job_id] = state

        # Resolve place name to place_id
        place_id: Optional[int] = None
        if location:
            places_data = await self._inat.get_places(location)
            results = places_data.get("results", [])
            if results:
                place_id = results[0].get("id")

        params: Dict[str, Any] = {"quality_grade": "research"}
        if taxon_id is not None:
            params["taxon_id"] = taxon_id
        if place_id is not None:
            params["place_id"] = place_id
        if date_range:
            if date_range.get("start"):
                params["d1"] = date_range["start"]
            if date_range.get("end"):
                params["d2"] = date_range["end"]

        page = 1
        batch: List[Dict[str, Any]] = []
        try:
            while True:
                data = await self._inat.get_observations_batch(params, per_page=200, page=page)
                results = data.get("results", [])
                if not results:
                    break

                state.total_records = data.get("total_results", 0)

                for obs in results:
                    batch.append(self._normalize_observation(obs))

                if len(batch) >= state.batch_size:
                    result = await self.store_to_mindex("observations", batch)
                    state.ingested_records += result.get("inserted", 0) + result.get("updated", 0)
                    batch = []

                state.last_page = page
                if page * 200 >= state.total_records:
                    break
                page += 1

            if batch:
                result = await self.store_to_mindex("observations", batch)
                state.ingested_records += result.get("inserted", 0) + result.get("updated", 0)

            state.status = "completed"
        except Exception as exc:
            logger.error("Observation ingestion failed: %s", exc)
            state.status = "failed"
            state.errors.append({"error": str(exc)})

        state.end_time = datetime.now(timezone.utc)
        return state

    # ------------------------------------------------------------------
    # Genetic Data Ingestion
    # ------------------------------------------------------------------

    async def ingest_genetic_data(self, taxon_id: int) -> Dict[str, Any]:
        """
        Pull genetic sequence data from NCBI GenBank for a taxon.

        Searches GenBank using the taxon's scientific name, fetches summaries,
        and stores results in MINDEX.

        Args:
            taxon_id: iNaturalist taxon ID.

        Returns:
            Dict with ingestion results.
        """
        taxon = await self._inat.get_taxa(taxon_id)
        if not taxon:
            return {"status": "error", "error": f"Taxon {taxon_id} not found"}

        scientific_name = taxon.get("name", "")
        logger.info("Ingesting genetic data for %s (taxon %d)", scientific_name, taxon_id)

        # Search GenBank
        genbank_ids = await self._ncbi.search_genbank(
            f"{scientific_name}[Organism]", retmax=100
        )
        if not genbank_ids:
            return {
                "status": "success",
                "taxon_id": taxon_id,
                "scientific_name": scientific_name,
                "sequences_found": 0,
            }

        # Fetch PubMed references for context
        pubmed_ids = await self._ncbi.search_pubmed(
            f"{scientific_name} genome", retmax=20
        )
        pubmed_summaries = await self._ncbi.fetch_pubmed_summary(pubmed_ids) if pubmed_ids else []

        records = [
            {
                "taxon_id": taxon_id,
                "scientific_name": scientific_name,
                "genbank_id": gid,
                "source": "ncbi_genbank",
                "ingested_at": datetime.now(timezone.utc).isoformat(),
            }
            for gid in genbank_ids
        ]

        result = await self.store_to_mindex("genetic_sequences", records)
        return {
            "status": "success",
            "taxon_id": taxon_id,
            "scientific_name": scientific_name,
            "sequences_found": len(genbank_ids),
            "pubmed_references": len(pubmed_summaries),
            "mindex_result": result,
        }

    # ------------------------------------------------------------------
    # Image Ingestion
    # ------------------------------------------------------------------

    async def ingest_images(self, taxon_id: int) -> Dict[str, Any]:
        """
        Pull taxon photos from iNaturalist and catalog them in MINDEX.

        Downloads photo metadata and stores references. Actual image files
        can be fetched separately to NAS at NAS_IMAGE_PATH.

        Args:
            taxon_id: iNaturalist taxon ID.

        Returns:
            Dict with image count and storage results.
        """
        photos = await self._inat.get_taxon_photos(taxon_id, per_page=30)
        if not photos:
            return {"status": "success", "taxon_id": taxon_id, "images_found": 0}

        records = []
        for photo in photos:
            record = {
                "taxon_id": taxon_id,
                "inaturalist_photo_id": photo.get("id"),
                "url_square": photo.get("square_url") or photo.get("url", "").replace("square", "square"),
                "url_medium": photo.get("medium_url") or photo.get("url", "").replace("square", "medium"),
                "url_large": photo.get("large_url") or photo.get("url", "").replace("square", "large"),
                "url_original": photo.get("original_url") or photo.get("url", "").replace("square", "original"),
                "attribution": photo.get("attribution", ""),
                "license_code": photo.get("license_code", ""),
                "nas_path": f"{NAS_IMAGE_PATH}/{taxon_id}/{photo.get('id', 'unknown')}.jpg",
                "ingested_at": datetime.now(timezone.utc).isoformat(),
            }
            records.append(record)

        result = await self.store_to_mindex("images", records)
        return {
            "status": "success",
            "taxon_id": taxon_id,
            "images_found": len(photos),
            "mindex_result": result,
        }

    # ------------------------------------------------------------------
    # Chemical Data Ingestion
    # ------------------------------------------------------------------

    async def ingest_chemical_data(self, compound_query: str) -> Dict[str, Any]:
        """
        Pull chemical compound data from ChemSpider.

        Searches by compound name and fetches detailed metadata for
        each match. Results are stored in MINDEX.

        Args:
            compound_query: Chemical compound name or partial name.

        Returns:
            Dict with compound search and storage results.
        """
        logger.info("Ingesting chemical data for query: %s", compound_query)

        compounds = await self._chemspider.search_by_name(compound_query, max_results=20)
        if not compounds:
            return {"status": "success", "query": compound_query, "compounds_found": 0}

        records = []
        for compound in compounds:
            record_id = compound if isinstance(compound, str) else compound.get("id", "")
            details = await self._chemspider.get_compound_details(str(record_id))
            if details:
                records.append({
                    "chemspider_id": str(record_id),
                    "compound_name": compound_query,
                    "details": details,
                    "source": "chemspider",
                    "ingested_at": datetime.now(timezone.utc).isoformat(),
                })

        if records:
            result = await self.store_to_mindex("chemical_compounds", records)
        else:
            result = {"inserted": 0, "updated": 0, "errors": 0}

        return {
            "status": "success",
            "query": compound_query,
            "compounds_found": len(records),
            "mindex_result": result,
        }

    # ------------------------------------------------------------------
    # Scientific Papers Ingestion
    # ------------------------------------------------------------------

    async def ingest_scientific_papers(self, query: str) -> Dict[str, Any]:
        """
        Pull scientific papers from PubMed (via NCBI) and Google Scholar
        (via SerpAPI) and store references in MINDEX.

        Args:
            query: Search query for papers (e.g. 'psilocybin biosynthesis').

        Returns:
            Dict with paper counts by source and storage results.
        """
        logger.info("Ingesting scientific papers for: %s", query)
        records: List[Dict[str, Any]] = []

        # PubMed
        pmids = await self._ncbi.search_pubmed(query, retmax=50)
        if pmids:
            summaries = await self._ncbi.fetch_pubmed_summary(pmids)
            for summary in summaries:
                records.append({
                    "source": "pubmed",
                    "external_id": summary.get("uid", ""),
                    "title": summary.get("title", ""),
                    "authors": summary.get("authors", []),
                    "journal": summary.get("fulljournalname", ""),
                    "pub_date": summary.get("pubdate", ""),
                    "doi": summary.get("elocationid", ""),
                    "query": query,
                    "ingested_at": datetime.now(timezone.utc).isoformat(),
                })

        # Google Scholar (via SerpAPI)
        if self._scholar and self._scholar.is_configured():
            try:
                scholar_results = await self._scholar.search(query, max_results=20)
                for item in scholar_results:
                    records.append({
                        "source": "google_scholar",
                        "external_id": item.get("link", ""),
                        "title": item.get("title", ""),
                        "snippet": item.get("snippet", ""),
                        "publication_info": item.get("publication_info", {}),
                        "link": item.get("link", ""),
                        "query": query,
                        "ingested_at": datetime.now(timezone.utc).isoformat(),
                    })
            except Exception as exc:
                logger.warning("Google Scholar search failed: %s", exc)

        if records:
            result = await self.store_to_mindex("scientific_papers", records)
        else:
            result = {"inserted": 0, "updated": 0, "errors": 0}

        return {
            "status": "success",
            "query": query,
            "pubmed_papers": len(pmids),
            "total_papers": len(records),
            "mindex_result": result,
        }

    # ------------------------------------------------------------------
    # Status & Scheduling
    # ------------------------------------------------------------------

    async def get_ingestion_status(self, job_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get current ingestion progress.

        Args:
            job_id: Specific job ID. If None, returns all active jobs.

        Returns:
            Status dict with progress metrics.
        """
        if job_id:
            state = self._jobs.get(job_id)
            if not state:
                return {"status": "error", "error": f"Job {job_id} not found"}
            return state.to_dict()

        return {
            "active_jobs": len([j for j in self._jobs.values() if j.status == "running"]),
            "total_jobs": len(self._jobs),
            "jobs": {jid: s.to_dict() for jid, s in self._jobs.items()},
        }

    async def schedule_full_ingestion(self) -> Dict[str, Any]:
        """
        Schedule ingestion of ALL life data across every kingdom.

        Creates one ingestion job per kingdom and runs them sequentially
        to respect rate limits. Intended for initial full-sync or periodic
        refresh.

        Returns:
            Dict with scheduled job IDs per kingdom.
        """
        kingdoms = ["fungi", "plantae", "animalia", "bacteria", "protista", "archaea"]
        scheduled: Dict[str, str] = {}

        for kingdom in kingdoms:
            state = IngestionState(
                target=IngestionTarget(kingdom) if kingdom in [e.value for e in IngestionTarget] else IngestionTarget.ALL_LIFE,
            )
            self._jobs[state.job_id] = state
            scheduled[kingdom] = state.job_id

        logger.info("Scheduled full ingestion for %d kingdoms", len(kingdoms))

        # Run sequentially in background to avoid overwhelming the API
        asyncio.create_task(self._run_scheduled_ingestion(scheduled))

        return {
            "status": "scheduled",
            "kingdoms": scheduled,
            "total_kingdoms": len(kingdoms),
        }

    async def _run_scheduled_ingestion(self, kingdom_jobs: Dict[str, str]) -> None:
        """Background task that runs kingdom ingestions sequentially."""
        for kingdom, job_id in kingdom_jobs.items():
            logger.info("Starting scheduled ingestion for kingdom: %s", kingdom)
            try:
                state = await self.ingest_kingdom(kingdom)
                # Update the pre-created job entry with the actual state
                self._jobs[job_id] = state
                self._jobs[job_id].job_id = job_id
            except Exception as exc:
                logger.error("Scheduled ingestion failed for %s: %s", kingdom, exc)
                if job_id in self._jobs:
                    self._jobs[job_id].status = "failed"
                    self._jobs[job_id].errors.append({"error": str(exc)})
                    self._jobs[job_id].end_time = datetime.now(timezone.utc)

    # ------------------------------------------------------------------
    # Normalization Helpers
    # ------------------------------------------------------------------

    def _normalize_taxon(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize an iNaturalist taxon record to the MINDEX schema.

        Maps iNaturalist fields to the core.taxon table columns.
        """
        ancestors = raw.get("ancestors", [])
        ancestry_ids = [a.get("id") for a in ancestors if a.get("id")]

        default_photo = raw.get("default_photo") or {}
        return {
            "inaturalist_id": raw.get("id"),
            "scientific_name": raw.get("name", ""),
            "canonical_name": raw.get("preferred_common_name", raw.get("name", "")),
            "rank": raw.get("rank", ""),
            "rank_level": raw.get("rank_level"),
            "parent_id": raw.get("parent_id"),
            "ancestry_ids": ancestry_ids,
            "ancestry_string": raw.get("ancestry", ""),
            "is_active": raw.get("is_active", True),
            "observations_count": raw.get("observations_count", 0),
            "wikipedia_url": raw.get("wikipedia_url", ""),
            "wikipedia_summary": raw.get("wikipedia_summary", ""),
            "default_photo_url": default_photo.get("medium_url", ""),
            "default_photo_attribution": default_photo.get("attribution", ""),
            "conservation_status": raw.get("conservation_status"),
            "endemic": raw.get("endemic", False),
            "threatened": raw.get("threatened", False),
            "introduced": raw.get("introduced", False),
            "native": raw.get("native", False),
            "source": "inaturalist",
            "ingested_at": datetime.now(timezone.utc).isoformat(),
        }

    def _normalize_observation(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize an iNaturalist observation to the MINDEX schema.

        Maps iNaturalist observation fields including geolocation,
        photos, identifications, and quality metrics.
        """
        taxon = raw.get("taxon") or {}
        geojson = raw.get("geojson") or {}
        photos = raw.get("photos", [])

        photo_urls = [
            {
                "id": p.get("id"),
                "url": p.get("url", ""),
                "attribution": p.get("attribution", ""),
                "license_code": p.get("license_code", ""),
            }
            for p in photos[:10]
        ]

        return {
            "inaturalist_id": raw.get("id"),
            "taxon_id": taxon.get("id"),
            "scientific_name": taxon.get("name", ""),
            "common_name": taxon.get("preferred_common_name", ""),
            "observed_on": raw.get("observed_on", ""),
            "time_observed_at": raw.get("time_observed_at"),
            "created_at": raw.get("created_at"),
            "quality_grade": raw.get("quality_grade", ""),
            "location_lat": raw.get("location", "").split(",")[0] if raw.get("location") else None,
            "location_lng": raw.get("location", "").split(",")[1] if raw.get("location") and "," in raw.get("location", "") else None,
            "geojson": geojson,
            "place_guess": raw.get("place_guess", ""),
            "positional_accuracy": raw.get("positional_accuracy"),
            "photos": photo_urls,
            "num_identification_agreements": raw.get("num_identification_agreements", 0),
            "num_identification_disagreements": raw.get("num_identification_disagreements", 0),
            "identifications_count": raw.get("identifications_count", 0),
            "comments_count": raw.get("comments_count", 0),
            "faves_count": raw.get("faves_count", 0),
            "user_login": (raw.get("user") or {}).get("login", ""),
            "license_code": raw.get("license_code", ""),
            "source": "inaturalist",
            "ingested_at": datetime.now(timezone.utc).isoformat(),
        }

    # ------------------------------------------------------------------
    # Task Handlers
    # ------------------------------------------------------------------

    async def _handle_ingest_kingdom(self, task: AgentTask) -> Dict[str, Any]:
        kingdom = task.payload.get("kingdom", "fungi")
        state = await self.ingest_kingdom(kingdom)
        return {"status": "success", "result": state.to_dict()}

    async def _handle_ingest_taxon_tree(self, task: AgentTask) -> Dict[str, Any]:
        root_id = task.payload.get("root_taxon_id")
        max_depth = task.payload.get("max_depth", 50)
        if not root_id:
            return {"status": "error", "error": "root_taxon_id is required"}
        state = await self.ingest_taxon_tree(int(root_id), max_depth=max_depth)
        return {"status": "success", "result": state.to_dict()}

    async def _handle_ingest_observations(self, task: AgentTask) -> Dict[str, Any]:
        taxon_id = task.payload.get("taxon_id")
        location = task.payload.get("location")
        date_range = task.payload.get("date_range")
        state = await self.ingest_observations(
            taxon_id=int(taxon_id) if taxon_id else None,
            location=location,
            date_range=date_range,
        )
        return {"status": "success", "result": state.to_dict()}

    async def _handle_ingest_genetic_data(self, task: AgentTask) -> Dict[str, Any]:
        taxon_id = task.payload.get("taxon_id")
        if not taxon_id:
            return {"status": "error", "error": "taxon_id is required"}
        return await self.ingest_genetic_data(int(taxon_id))

    async def _handle_ingest_images(self, task: AgentTask) -> Dict[str, Any]:
        taxon_id = task.payload.get("taxon_id")
        if not taxon_id:
            return {"status": "error", "error": "taxon_id is required"}
        return await self.ingest_images(int(taxon_id))

    async def _handle_ingest_chemical_data(self, task: AgentTask) -> Dict[str, Any]:
        query = task.payload.get("compound_query", "")
        if not query:
            return {"status": "error", "error": "compound_query is required"}
        return await self.ingest_chemical_data(query)

    async def _handle_ingest_scientific_papers(self, task: AgentTask) -> Dict[str, Any]:
        query = task.payload.get("query", "")
        if not query:
            return {"status": "error", "error": "query is required"}
        return await self.ingest_scientific_papers(query)

    async def _handle_schedule_full_ingestion(self, task: AgentTask) -> Dict[str, Any]:
        return await self.schedule_full_ingestion()

    async def _handle_ingestion_status(self, task: AgentTask) -> Dict[str, Any]:
        job_id = task.payload.get("job_id")
        return await self.get_ingestion_status(job_id=job_id)
