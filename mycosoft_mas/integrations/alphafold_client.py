"""
AlphaFold Protein Structure Database integration client.

Fetches existing AlphaFold predictions from EBI AlphaFold DB.
Supports UniProt ID lookup, PDB/mmCIF download URLs, and metadata.

Environment Variables:
    ALPHAFOLD_API_BASE: Optional override (default: https://alphafold.ebi.ac.uk/api)
"""

import logging
from typing import Any, Dict, Optional

import httpx

logger = logging.getLogger(__name__)

ALPHAFOLD_API_BASE = "https://alphafold.ebi.ac.uk/api"


class AlphaFoldClient:
    """Client for EBI AlphaFold Protein Structure Database API."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.base_url = self.config.get(
            "base_url", __import__("os").environ.get("ALPHAFOLD_API_BASE", ALPHAFOLD_API_BASE)
        )
        self.timeout = self.config.get("timeout", 60)
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url.rstrip("/"),
                timeout=self.timeout,
            )
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def get_prediction(self, uniprot_id: str) -> Optional[Dict[str, Any]]:
        """
        Get AlphaFold prediction metadata for a UniProt accession.
        Returns entry data with pdbUrl, cifUrl, paeImageUrl, confidence scores, etc.
        """
        client = await self._get_client()
        try:
            r = await client.get(f"/prediction/{uniprot_id}")
            if r.status_code == 404:
                logger.info("AlphaFold: no prediction for UniProt %s", uniprot_id)
                return None
            r.raise_for_status()
            data = r.json()
            if isinstance(data, list) and len(data) > 0:
                return data[0]
            return data if isinstance(data, dict) else None
        except httpx.HTTPStatusError as e:
            logger.warning("AlphaFold get_prediction failed for %s: %s", uniprot_id, e)
            return None
        except Exception as e:
            logger.warning("AlphaFold get_prediction error: %s", e)
            return None

    async def get_prediction_urls(self, uniprot_id: str) -> Dict[str, Optional[str]]:
        """Get download URLs for PDB, mmCIF, PAE image for a UniProt ID."""
        pred = await self.get_prediction(uniprot_id)
        if not pred:
            return {"pdb": None, "cif": None, "pae_image": None}
        return {
            "pdb": pred.get("pdbUrl") or pred.get("pdb_url"),
            "cif": pred.get("cifUrl") or pred.get("cif_url"),
            "pae_image": pred.get("paeImageUrl") or pred.get("pae_image_url"),
        }

    async def fetch_pdb_content(self, uniprot_id: str) -> Optional[str]:
        """Fetch PDB file content for a UniProt ID (follows pdbUrl)."""
        pred = await self.get_prediction(uniprot_id)
        url = (pred or {}).get("pdbUrl") or (pred or {}).get("pdb_url")
        if not url:
            return None
        try:
            async with httpx.AsyncClient(timeout=120) as c:
                r = await c.get(url)
                r.raise_for_status()
                return r.text
        except Exception as e:
            logger.warning("AlphaFold fetch_pdb_content failed: %s", e)
            return None

    async def get_uniprot_summary(
        self, uniprot_id: str, start: Optional[int] = None, end: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """Get UniProt summary for a residue range (qualifier format: uniprot_id or uniprot_id-start-end)."""
        client = await self._get_client()
        qualifier = uniprot_id
        if start is not None and end is not None:
            qualifier = f"{uniprot_id}-{start}-{end}"
        try:
            r = await client.get(f"/uniprot/summary/{qualifier}.json")
            if r.status_code == 404:
                return None
            r.raise_for_status()
            return r.json()
        except Exception as e:
            logger.warning("AlphaFold get_uniprot_summary failed: %s", e)
            return None

    async def search_by_sequence(self, sequence: str) -> Optional[Dict[str, Any]]:
        """Get sequence summary (sequence search)."""
        client = await self._get_client()
        try:
            r = await client.get("/sequence/summary", params={"sequence": sequence})
            r.raise_for_status()
            return r.json()
        except Exception as e:
            logger.warning("AlphaFold search_by_sequence failed: %s", e)
            return None

    async def health_check(self) -> Dict[str, Any]:
        """Verify AlphaFold API is reachable."""
        try:
            client = await self._get_client()
            r = await client.get("/prediction/P00520")
            ok = r.status_code in (200, 404)
            return {
                "status": "healthy" if ok else "unhealthy",
                "api_base": self.base_url,
                "status_code": r.status_code,
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "api_base": self.base_url,
                "error": str(e),
            }
