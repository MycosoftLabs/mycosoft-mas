"""
ChEMBL Integration Client.

Drug/compound search, bioactivity data, target identification, ADMET properties.
Uses the public ChEMBL REST API (no API key required).

Environment Variables:
    None required - ChEMBL API is public
"""

import logging
from typing import Any, Dict, List, Optional
from urllib.parse import quote

import httpx

logger = logging.getLogger(__name__)

CHEMBL_API_BASE = "https://www.ebi.ac.uk/chembl/api/data"


class ChEMBLClient:
    """Client for ChEMBL REST API."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.timeout = self.config.get("timeout", 30)
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=CHEMBL_API_BASE,
                headers={"Accept": "application/json"},
                timeout=self.timeout,
            )
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def get_molecule(self, chembl_id: str) -> Optional[Dict[str, Any]]:
        """Get molecule by ChEMBL ID (e.g. CHEMBL25, CHEMBL192)."""
        client = await self._get_client()
        try:
            r = await client.get(f"/molecule/{chembl_id}.json")
            if r.is_success:
                return r.json()
            return None
        except Exception as e:
            logger.warning("ChEMBL get_molecule failed: %s", e)
            return None

    async def search_molecules(
        self,
        pref_name: Optional[str] = None,
        synonym: Optional[str] = None,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """Search molecules by preferred name or synonym."""
        client = await self._get_client()
        params: Dict[str, Any] = {"limit": limit}
        if pref_name:
            params["pref_name__icontains"] = pref_name
        if synonym:
            params["molecule_synonyms__molecule_synonym__icontains"] = synonym
        try:
            r = await client.get("/molecule.json", params=params)
            if r.is_success:
                data = r.json()
                return data.get("molecules", [])
            return []
        except Exception as e:
            logger.warning("ChEMBL search_molecules failed: %s", e)
            return []

    async def get_target(self, target_id: str) -> Optional[Dict[str, Any]]:
        """Get target (protein, organism) by ChEMBL ID."""
        client = await self._get_client()
        try:
            r = await client.get(f"/target/{target_id}.json")
            if r.is_success:
                return r.json()
            return None
        except Exception as e:
            logger.warning("ChEMBL get_target failed: %s", e)
            return None

    async def get_activity(self, activity_id: int) -> Optional[Dict[str, Any]]:
        """Get single activity by ID."""
        client = await self._get_client()
        try:
            r = await client.get(f"/activity/{activity_id}.json")
            if r.is_success:
                return r.json()
            return None
        except Exception as e:
            logger.warning("ChEMBL get_activity failed: %s", e)
            return None

    async def get_activities_for_molecule(
        self,
        molecule_chembl_id: str,
        limit: int = 100,
        pchembl_value_only: bool = False,
    ) -> List[Dict[str, Any]]:
        """Get bioactivities for a molecule."""
        client = await self._get_client()
        params: Dict[str, Any] = {
            "molecule_chembl_id": molecule_chembl_id,
            "limit": limit,
        }
        if pchembl_value_only:
            params["pchembl_value__isnull"] = "false"
        try:
            r = await client.get("/activity.json", params=params)
            if r.is_success:
                data = r.json()
                return data.get("activities", [])
            return []
        except Exception as e:
            logger.warning("ChEMBL get_activities_for_molecule failed: %s", e)
            return []

    async def get_activities_for_target(
        self,
        target_chembl_id: str,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Get bioactivities for a target."""
        client = await self._get_client()
        params: Dict[str, Any] = {
            "target_chembl_id": target_chembl_id,
            "limit": limit,
        }
        try:
            r = await client.get("/activity.json", params=params)
            if r.is_success:
                data = r.json()
                return data.get("activities", [])
            return []
        except Exception as e:
            logger.warning("ChEMBL get_activities_for_target failed: %s", e)
            return []

    async def get_assay(self, assay_id: str) -> Optional[Dict[str, Any]]:
        """Get assay by ChEMBL ID."""
        client = await self._get_client()
        try:
            r = await client.get(f"/assay/{assay_id}.json")
            if r.is_success:
                return r.json()
            return None
        except Exception as e:
            logger.warning("ChEMBL get_assay failed: %s", e)
            return None

    async def substructure_search(
        self,
        smiles: str,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Substructure search by SMILES. Returns matching molecule IDs."""
        client = await self._get_client()
        encoded = quote(smiles, safe="")
        try:
            r = await client.get(
                f"/substructure/{encoded}.json",
                params={"limit": limit},
            )
            if r.is_success:
                data = r.json()
                return data.get("molecules", [])
            return []
        except Exception as e:
            logger.warning("ChEMBL substructure_search failed: %s", e)
            return []

    async def similarity_search(
        self,
        smiles: str,
        similarity: float = 0.7,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Similarity search by SMILES (Tanimoto, 0-1)."""
        client = await self._get_client()
        encoded = quote(smiles, safe="")
        try:
            r = await client.get(
                f"/similarity/{encoded}/{similarity}.json",
                params={"limit": limit},
            )
            if r.is_success:
                data = r.json()
                return data.get("molecules", [])
            return []
        except Exception as e:
            logger.warning("ChEMBL similarity_search failed: %s", e)
            return []

    async def get_drug(self, chembl_id: str) -> Optional[Dict[str, Any]]:
        """Get drug/approved molecule by ChEMBL ID."""
        client = await self._get_client()
        try:
            r = await client.get(f"/drug/{chembl_id}.json")
            if r.is_success:
                return r.json()
            return None
        except Exception as e:
            logger.warning("ChEMBL get_drug failed: %s", e)
            return None

    async def health_check(self) -> Dict[str, Any]:
        """Verify connectivity to ChEMBL API."""
        try:
            client = await self._get_client()
            r = await client.get("/molecule/CHEMBL25.json")
            if r.is_success:
                return {"status": "healthy"}
            return {"status": "unhealthy", "error": r.text[:200]}
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}
