"""
KEGG Integration Client.

Metabolic pathway mapping, enzyme lookup, compound-reaction linking.
Uses the public KEGG REST API (https://rest.kegg.jp/) - no API key required.
Academic use only per KEGG terms.

Environment Variables:
    None required - KEGG REST API is public
"""

import logging
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

KEGG_API_BASE = "https://rest.kegg.jp"


def _parse_kegg_flat_file(text: str) -> Dict[str, Any]:
    """Parse KEGG flat file format into a dict of lists."""
    result: Dict[str, Any] = {}
    current_key: Optional[str] = None
    current_lines: List[str] = []
    for line in text.splitlines():
        if line.startswith(" "):
            if current_key:
                current_lines.append(line.strip())
            continue
        if current_key:
            result.setdefault(current_key, []).append(" ".join(current_lines))
        if line and not line.startswith(" "):
            key = line[:12].strip()
            value = line[12:].strip() if len(line) > 12 else ""
            current_key = key
            current_lines = [value] if value else []
    if current_key:
        result.setdefault(current_key, []).append(" ".join(current_lines))
    return result


def _parse_tab_list(text: str) -> List[Dict[str, str]]:
    """Parse tab-delimited list (id\tdescription)."""
    out: List[Dict[str, str]] = []
    for line in text.strip().splitlines():
        if "\t" in line:
            pid, desc = line.split("\t", 1)
            out.append({"id": pid.strip(), "description": desc.strip()})
    return out


class KEGGClient:
    """Client for KEGG REST API."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.timeout = self.config.get("timeout", 30)
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=KEGG_API_BASE,
                headers={"Accept": "text/plain"},
                timeout=self.timeout,
            )
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def get_pathway(
        self, pathway_id: str, option: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get pathway entry. pathway_id like 'hsa00010' or 'map00600'.
        option: aaseq, ntseq, mol, kcf, image, conf, kgml, json
        """
        client = await self._get_client()
        url = f"/get/{pathway_id}"
        if option:
            url += f"/{option}"
        try:
            r = await client.get(url)
            if r.is_success:
                if option == "json":
                    return r.json()
                return _parse_kegg_flat_file(r.text)
            return None
        except Exception as e:
            logger.warning("KEGG get_pathway failed: %s", e)
            return None

    async def list_pathways(self, org: Optional[str] = None) -> List[Dict[str, str]]:
        """List pathways. org e.g. 'hsa' for human, None for reference pathways."""
        client = await self._get_client()
        path = "/list/pathway" if not org else f"/list/pathway/{org}"
        try:
            r = await client.get(path)
            if r.is_success:
                return _parse_tab_list(r.text)
            return []
        except Exception as e:
            logger.warning("KEGG list_pathways failed: %s", e)
            return []

    async def find_pathways(self, query: str) -> List[Dict[str, str]]:
        """Find pathways by keyword."""
        client = await self._get_client()
        try:
            r = await client.get(f"/find/pathway/{query}")
            if r.is_success:
                return _parse_tab_list(r.text)
            return []
        except Exception as e:
            logger.warning("KEGG find_pathways failed: %s", e)
            return []

    async def get_compound(
        self, compound_id: str, option: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Get compound entry. compound_id like 'C00001' or 'cpd:C00001'."""
        if ":" not in compound_id:
            compound_id = (
                f"cpd:{compound_id}"
                if compound_id.upper().startswith("C")
                else f"cpd:C{compound_id}"
            )
        client = await self._get_client()
        url = f"/get/{compound_id}"
        if option:
            url += f"/{option}"
        try:
            r = await client.get(url)
            if r.is_success:
                if option == "json":
                    return r.json()
                return _parse_kegg_flat_file(r.text)
            return None
        except Exception as e:
            logger.warning("KEGG get_compound failed: %s", e)
            return None

    async def find_compounds(
        self,
        query: str,
        option: Optional[str] = None,
    ) -> List[Dict[str, str]]:
        """Find compounds. option: formula, exact_mass, mol_weight, nop."""
        client = await self._get_client()
        path = f"/find/compound/{query}"
        if option:
            path += f"/{option}"
        try:
            r = await client.get(path)
            if r.is_success:
                return _parse_tab_list(r.text)
            return []
        except Exception as e:
            logger.warning("KEGG find_compounds failed: %s", e)
            return []

    async def link_pathway_compound(
        self, pathway_id: Optional[str] = None, compound_id: Optional[str] = None
    ) -> List[Dict[str, str]]:
        """Link pathway to compounds or compound to pathways."""
        client = await self._get_client()
        if pathway_id and compound_id:
            return []
        if pathway_id:
            path = f"/link/compound/{pathway_id}"
        elif compound_id:
            path = f"/link/pathway/{compound_id}"
        else:
            path = "/link/compound/pathway"
        try:
            r = await client.get(path)
            if r.is_success:
                return _parse_tab_list(r.text)
            return []
        except Exception as e:
            logger.warning("KEGG link_pathway_compound failed: %s", e)
            return []

    async def get_reaction(self, reaction_id: str) -> Optional[Dict[str, Any]]:
        """Get reaction entry. reaction_id like 'R00001' or 'rn:R00001'."""
        rid = reaction_id if ":" in reaction_id else f"rn:{reaction_id}"
        client = await self._get_client()
        try:
            r = await client.get(f"/get/{rid}")
            if r.is_success:
                return _parse_kegg_flat_file(r.text)
            return None
        except Exception as e:
            logger.warning("KEGG get_reaction failed: %s", e)
            return None

    async def get_enzyme(self, ec_number: str) -> Optional[Dict[str, Any]]:
        """Get enzyme entry by EC number (e.g. 1.1.1.1)."""
        client = await self._get_client()
        ec = ec_number if ":" in ec_number else f"ec:{ec_number}"
        try:
            r = await client.get(f"/get/{ec}")
            if r.is_success:
                return _parse_kegg_flat_file(r.text)
            return None
        except Exception as e:
            logger.warning("KEGG get_enzyme failed: %s", e)
            return None

    async def info(self, database: str = "kegg") -> Optional[str]:
        """Get database info/statistics."""
        client = await self._get_client()
        try:
            r = await client.get(f"/info/{database}")
            if r.is_success:
                return r.text
            return None
        except Exception as e:
            logger.warning("KEGG info failed: %s", e)
            return None

    async def health_check(self) -> Dict[str, Any]:
        """Check KEGG API availability."""
        try:
            info_text = await self.info("pathway")
            ok = info_text is not None and len(info_text) > 0
            return {
                "status": "healthy" if ok else "unhealthy",
                "service": "kegg",
                "pathway_info_available": ok,
            }
        except Exception as e:
            logger.warning("KEGG health_check failed: %s", e)
            return {"status": "unhealthy", "service": "kegg", "error": str(e)}
