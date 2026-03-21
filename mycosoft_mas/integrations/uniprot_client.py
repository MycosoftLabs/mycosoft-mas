"""
UniProt Integration Client.

Protein sequence search, function annotation, pathway mapping.
Uses UniProt REST API (rest.uniprot.org). No API key required for public access.

Environment Variables:
    UNIPROT_EMAIL: Optional contact email for high-volume requests (recommended)
"""

import logging
import os
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

UNIPROT_BASE = "https://rest.uniprot.org"


class UniProtClient:
    """Client for UniProt REST API."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.email = self.config.get("email", os.getenv("UNIPROT_EMAIL", ""))
        self.timeout = self.config.get("timeout", 60)
        self._client: Optional[httpx.AsyncClient] = None

    def _headers(self) -> Dict[str, str]:
        h = {"Accept": "application/json"}
        if self.email:
            h["User-Agent"] = f"UniProtClient ({self.email})"
        return h

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=UNIPROT_BASE,
                headers=self._headers(),
                timeout=self.timeout,
            )
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def get_entry(
        self,
        accession: str,
        format: str = "json",
    ) -> Optional[Dict[str, Any]]:
        """Get UniProtKB entry by accession (e.g. P51811, Q9Y6K9)."""
        client = await self._get_client()
        try:
            r = await client.get(f"/uniprotkb/{accession}", params={"format": format})
            r.raise_for_status()
            return r.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.debug("UniProt entry not found: %s", accession)
                return None
            logger.warning("UniProt get_entry error %s: %s", e.response.status_code, e)
            return None
        except Exception as e:
            logger.warning("UniProt get_entry failed: %s", e)
            return None

    async def get_sequence(self, accession: str) -> Optional[str]:
        """Get protein sequence for an accession."""
        entry = await self.get_entry(accession)
        if not entry or "sequence" not in entry:
            return None
        seq = entry.get("sequence", {})
        if isinstance(seq, dict):
            return seq.get("value")
        return None

    async def get_fasta(self, accession: str) -> Optional[str]:
        """Get FASTA format sequence."""
        client = await self._get_client()
        try:
            r = await client.get(f"/uniprotkb/{accession}.fasta")
            r.raise_for_status()
            return r.text
        except Exception as e:
            logger.warning("UniProt get_fasta failed: %s", e)
            return None

    async def get_summary(self, accession: str) -> Optional[Dict[str, Any]]:
        """Get a compact summary: accession, name, organism, sequence length, function."""
        entry = await self.get_entry(accession)
        if not entry:
            return None
        pd = entry.get("proteinDescription", {})
        rec = (
            pd.get("recommendedName") or pd.get("submittedNames", [{}])[0]
            if pd.get("submittedNames")
            else {}
        )
        name = ""
        if isinstance(rec, dict):
            fn = rec.get("fullName") or rec.get("shortName") or {}
            name = fn.get("value", "") if isinstance(fn, dict) else str(fn)
        genes = entry.get("genes", [{}])
        gene = genes[0].get("geneName", {}).get("value", "") if genes else ""
        org = entry.get("organism", {})
        organism = org.get("scientificName", "") if isinstance(org, dict) else ""
        seq = entry.get("sequence", {})
        length = seq.get("length", 0) if isinstance(seq, dict) else 0
        func = ""
        for c in entry.get("comments", []):
            if c.get("commentType") == "FUNCTION":
                texts = c.get("texts", [{}])
                if texts and isinstance(texts[0], dict):
                    func = texts[0].get("value", "")[:500]
                break
        return {
            "accession": entry.get("primaryAccession"),
            "id": entry.get("uniProtkbId"),
            "name": name,
            "gene": gene,
            "organism": organism,
            "length": length,
            "function": func,
        }

    async def search(
        self,
        query: str,
        fields: Optional[List[str]] = None,
        size: int = 100,
        format: str = "json",
    ) -> Dict[str, Any]:
        """Search UniProtKB. Query uses UniProt query language (e.g. 'gene:BRCA1', 'organism_id:9606')."""
        client = await self._get_client()
        default_fields = [
            "accession",
            "id",
            "protein_name",
            "gene_names",
            "organism_name",
            "length",
            "cc_function",
        ]
        fields = fields or default_fields
        try:
            r = await client.get(
                "/uniprotkb/search",
                params={
                    "query": query,
                    "fields": ",".join(fields),
                    "size": size,
                    "format": format,
                },
            )
            r.raise_for_status()
            data = r.json()
            return {
                "results": data.get("results", []),
                "count": data.get("results", []).__len__(),
            }
        except Exception as e:
            logger.warning("UniProt search failed: %s", e)
            return {"results": [], "count": 0}

    async def map_ids(
        self,
        ids: List[str],
        from_db: str = "UniProtKB_AC-ID",
        to_db: str = "UniProtKB",
    ) -> Dict[str, List[str]]:
        """Map identifiers to UniProt accessions. Uses ID Mapping API (async job)."""
        if not ids:
            return {}
        import asyncio

        client = await self._get_client()
        try:
            r = await client.post(
                "/idmapping/run",
                json={"ids": ids[:1000], "from": from_db, "to": to_db},
            )
            r.raise_for_status()
            job = r.json()
            job_id = job.get("jobId")
            if not job_id:
                return {}
            for _ in range(30):
                await asyncio.sleep(1)
                r2 = await client.get(f"/idmapping/status/{job_id}")
                r2.raise_for_status()
                status = r2.json()
                if status.get("jobStatus") == "FINISHED":
                    results = status.get("results", [])
                    mapping: Dict[str, List[str]] = {}
                    for item in results:
                        from_id = item.get("from")
                        to_obj = item.get("to")
                        to_id = to_obj.get("primaryAccession") if isinstance(to_obj, dict) else None
                        if from_id and to_id:
                            mapping.setdefault(from_id, []).append(to_id)
                    return mapping
                if status.get("jobStatus") == "FAILED":
                    break
            return {}
        except Exception as e:
            logger.warning("UniProt id mapping failed: %s", e)
            return {}

    async def health_check(self) -> Dict[str, Any]:
        """Check API connectivity."""
        try:
            entry = await self.get_entry("P12345")
            ok = entry is not None
            return {"ok": ok, "message": "UniProt API reachable" if ok else "No response"}
        except Exception as e:
            return {"ok": False, "message": str(e)}
