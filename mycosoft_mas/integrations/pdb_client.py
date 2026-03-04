"""
RCSB PDB Integration Client.

Protein structure search, PDB file download, ligand binding analysis.
Uses RCSB PDB Search API (search.rcsb.org) and Data API (data.rcsb.org).
No API key required for public access.

Environment Variables:
    None required.
"""

import logging
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

SEARCH_BASE = "https://search.rcsb.org/rcsbsearch/v2"
DATA_BASE = "https://data.rcsb.org"
FILES_BASE = "https://files.rcsb.org"


class PDBClient:
    """Client for RCSB PDB Search, Data, and file download."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.timeout = self.config.get("timeout", 60)
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def get_entry(
        self,
        pdb_id: str,
        include_graphql: bool = True,
    ) -> Optional[Dict[str, Any]]:
        """Get PDB entry metadata by ID (e.g. 4HHB, 1XYZ)."""
        pdb_id = pdb_id.upper()[:4]
        if include_graphql:
            data = await self._graphql_entry(pdb_id)
            if data:
                return data
        result = await self.search(query={"attribute": "rcsb_id", "operator": "exact_match", "value": pdb_id})
        hits = result.get("result_set", [])
        if hits:
            return {"identifier": hits[0].get("identifier"), "score": hits[0].get("score")}
        return None

    async def _graphql_entry(self, pdb_id: str) -> Optional[Dict[str, Any]]:
        """Fetch entry via GraphQL Data API."""
        query = """
        query ($id: String!) {
          entry(entry_id: $id) {
            rcsb_id
            struct {
              title
              pdbx_descriptor
            }
            exptl {
              method
            }
            rcsb_entry_info {
              resolution_combined
              molecular_weight
              polymer_entity_count
            }
            polymer_entities {
              entity_poly {
                type
                pdbx_strand_id
              }
              rcsb_polymer_entity {
                pdbx_description
              }
            }
          }
        }
        """
        client = await self._get_client()
        try:
            r = await client.post(
                f"{DATA_BASE}/graphql",
                json={"query": query, "variables": {"id": pdb_id}},
                headers={"Content-Type": "application/json"},
            )
            r.raise_for_status()
            j = r.json()
            return j.get("data", {}).get("entry")
        except Exception as e:
            logger.debug("PDB GraphQL failed for %s: %s", pdb_id, e)
            return None

    async def get_pdb_file(self, pdb_id: str) -> Optional[str]:
        """Download PDB file content as text."""
        pdb_id = pdb_id.upper()[:4]
        client = await self._get_client()
        try:
            r = await client.get(f"{FILES_BASE}/download/{pdb_id}.pdb")
            r.raise_for_status()
            return r.text
        except Exception as e:
            logger.warning("PDB file download failed for %s: %s", pdb_id, e)
            return None

    async def search(
        self,
        query: Optional[Dict[str, Any]] = None,
        query_obj: Optional[Dict[str, Any]] = None,
        return_type: str = "entry",
        request_options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Search PDB using RCSB Search API. Pass query (terminal) or full query_obj."""
        if query_obj is None:
            if query is None:
                return {"result_set": [], "total_count": 0}
            query_obj = {
                "query": {"type": "terminal", "service": "text", "parameters": query},
                "return_type": return_type,
            }
        if request_options:
            query_obj["request_options"] = request_options

        client = await self._get_client()
        try:
            r = await client.post(f"{SEARCH_BASE}/query", json=query_obj)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            logger.warning("PDB search failed: %s", e)
            return {"result_set": [], "total_count": 0}

    async def search_by_uniprot(self, uniprot_id: str) -> Dict[str, Any]:
        """Search PDB structures for a UniProt accession."""
        query_obj = {
            "query": {
                "type": "group",
                "logical_operator": "and",
                "nodes": [
                    {
                        "type": "terminal",
                        "service": "text",
                        "parameters": {
                            "attribute": "rcsb_polymer_entity_container_identifiers.reference_sequence_identifiers.database_accession",
                            "operator": "exact_match",
                            "value": uniprot_id,
                        },
                    },
                    {
                        "type": "terminal",
                        "service": "text",
                        "parameters": {
                            "attribute": "rcsb_polymer_entity_container_identifiers.reference_sequence_identifiers.database_name",
                            "operator": "exact_match",
                            "value": "UniProt",
                        },
                    },
                ],
            },
            "return_type": "entry",
            "request_options": {"results_content_type": ["computational", "experimental"]},
        }
        return await self.search(query_obj=query_obj)

    async def search_by_keyword(self, keyword: str, limit: int = 100) -> Dict[str, Any]:
        """Search by protein/description keyword."""
        return await self.search(
            query={
                "attribute": "rcsb_polymer_entity.pdbx_description",
                "operator": "contains_phrase",
                "value": keyword,
            }
        )

    async def search_by_resolution(self, max_resolution: float) -> Dict[str, Any]:
        """Search structures with resolution better than max_resolution (Angstroms)."""
        return await self.search(
            query={
                "attribute": "rcsb_entry_info.resolution_combined",
                "operator": "less_or_equal",
                "value": str(max_resolution),
            }
        )

    async def get_summary(self, pdb_id: str) -> Optional[Dict[str, Any]]:
        """Get compact summary: title, method, resolution, weight."""
        entry = await self._graphql_entry(pdb_id.upper()[:4])
        if not entry:
            return None
        struct = entry.get("struct") or {}
        title = struct.get("title", "") if isinstance(struct, dict) else ""
        exptl = entry.get("exptl", [{}])
        method = exptl[0].get("method", "") if exptl and isinstance(exptl[0], dict) else ""
        info = entry.get("rcsb_entry_info") or {}
        resolution = info.get("resolution_combined") if isinstance(info, dict) else None
        weight = info.get("molecular_weight") if isinstance(info, dict) else None
        return {
            "pdb_id": entry.get("rcsb_id"),
            "title": title,
            "method": method,
            "resolution": resolution,
            "molecular_weight": weight,
        }

    async def health_check(self) -> Dict[str, Any]:
        """Check API connectivity."""
        try:
            entry = await self.get_entry("4HHB")
            ok = entry is not None
            return {"ok": ok, "message": "PDB API reachable" if ok else "No response"}
        except Exception as e:
            return {"ok": False, "message": str(e)}
