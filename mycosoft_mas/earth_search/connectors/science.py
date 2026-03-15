"""
Science Connector — chemical compounds, genetics, research papers, LLM synthesis.

Data sources: PubChem, GenBank/NCBI, PubMed, MINDEX local, LLM integration.

Created: March 15, 2026
"""

from __future__ import annotations

import logging
import uuid
from typing import Any, Dict, List, Optional

from mycosoft_mas.earth_search.connectors.base import BaseConnector
from mycosoft_mas.earth_search.models import (
    EarthSearchDomain,
    EarthSearchResult,
    GeoFilter,
    TemporalFilter,
)

logger = logging.getLogger(__name__)

SCIENCE_DOMAINS = {
    EarthSearchDomain.COMPOUNDS, EarthSearchDomain.GENETICS,
    EarthSearchDomain.RESEARCH, EarthSearchDomain.LLM_SYNTHESIS,
    EarthSearchDomain.MATHEMATICS, EarthSearchDomain.PHYSICS,
}


class ScienceConnector(BaseConnector):
    """Connector for scientific databases, compound/genetics search, and LLM synthesis."""

    source_id = "science"
    rate_limit_rps = 3.0

    PUBCHEM_BASE = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"
    NCBI_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
    MINDEX_BASE_DEFAULT = "http://192.168.0.189:8000"

    async def search(
        self,
        query: str,
        domains: List[EarthSearchDomain],
        geo: Optional[GeoFilter] = None,
        temporal: Optional[TemporalFilter] = None,
        limit: int = 20,
    ) -> List[EarthSearchResult]:
        relevant = [d for d in domains if d in SCIENCE_DOMAINS]
        if not relevant:
            return []

        results: List[EarthSearchResult] = []

        if EarthSearchDomain.COMPOUNDS in relevant:
            results.extend(await self._search_pubchem(query, limit))

        if EarthSearchDomain.GENETICS in relevant:
            results.extend(await self._search_genbank(query, limit))

        if EarthSearchDomain.RESEARCH in relevant:
            results.extend(await self._search_pubmed(query, limit))

        return results[:limit]

    async def _search_pubchem(self, query: str, limit: int) -> List[EarthSearchResult]:
        """Search PubChem for chemical compounds."""
        data = await self._get(
            f"{self.PUBCHEM_BASE}/compound/name/{query}/JSON",
        )
        if not data:
            # Try autocomplete
            data = await self._get(
                f"{self.PUBCHEM_BASE}/compound/name/{query}/property/MolecularFormula,MolecularWeight,IUPACName,InChI/JSON",
            )
        if not data:
            return []

        results: List[EarthSearchResult] = []
        compounds = data.get("PC_Compounds", data.get("PropertyTable", {}).get("Properties", []))
        if not isinstance(compounds, list):
            return []

        for comp in compounds[:limit]:
            cid = comp.get("CID") or comp.get("id", {}).get("id", {}).get("cid")
            results.append(EarthSearchResult(
                result_id=f"pubchem-{cid or uuid.uuid4().hex[:8]}",
                domain=EarthSearchDomain.COMPOUNDS,
                source="pubchem",
                title=comp.get("IUPACName", query),
                description=f"Formula: {comp.get('MolecularFormula', '?')}, MW: {comp.get('MolecularWeight', '?')}",
                data={
                    "cid": cid,
                    "molecular_formula": comp.get("MolecularFormula"),
                    "molecular_weight": comp.get("MolecularWeight"),
                    "iupac_name": comp.get("IUPACName"),
                    "inchi": comp.get("InChI"),
                },
                confidence=0.9,
                crep_layer="compounds",
                url=f"https://pubchem.ncbi.nlm.nih.gov/compound/{cid}" if cid else None,
            ))
        return results

    async def _search_genbank(self, query: str, limit: int) -> List[EarthSearchResult]:
        """Search GenBank/NCBI nucleotide database."""
        # Step 1: ESearch
        search_data = await self._get(
            f"{self.NCBI_BASE}/esearch.fcgi",
            params={"db": "nucleotide", "term": query, "retmax": min(limit, 10), "retmode": "json"},
        )
        if not search_data:
            return []

        id_list = search_data.get("esearchresult", {}).get("idlist", [])
        if not id_list:
            return []

        # Step 2: ESummary
        summary_data = await self._get(
            f"{self.NCBI_BASE}/esummary.fcgi",
            params={"db": "nucleotide", "id": ",".join(id_list), "retmode": "json"},
        )
        if not summary_data:
            return []

        results: List[EarthSearchResult] = []
        result_map = summary_data.get("result", {})
        for gid in id_list:
            rec = result_map.get(gid, {})
            if not isinstance(rec, dict):
                continue
            results.append(EarthSearchResult(
                result_id=f"genbank-{gid}",
                domain=EarthSearchDomain.GENETICS,
                source="genbank",
                title=rec.get("title", query),
                description=f"Accession: {rec.get('caption', '?')}, Length: {rec.get('slen', '?')}bp",
                data={
                    "gi": gid,
                    "accession": rec.get("caption"),
                    "title": rec.get("title"),
                    "organism": rec.get("organism"),
                    "length_bp": rec.get("slen"),
                    "mol_type": rec.get("moltype"),
                    "create_date": rec.get("createdate"),
                },
                confidence=0.9,
                crep_layer="genetics",
                url=f"https://www.ncbi.nlm.nih.gov/nuccore/{rec.get('caption', gid)}",
            ))
        return results

    async def _search_pubmed(self, query: str, limit: int) -> List[EarthSearchResult]:
        """Search PubMed for research papers."""
        search_data = await self._get(
            f"{self.NCBI_BASE}/esearch.fcgi",
            params={"db": "pubmed", "term": query, "retmax": min(limit, 10), "retmode": "json"},
        )
        if not search_data:
            return []

        id_list = search_data.get("esearchresult", {}).get("idlist", [])
        if not id_list:
            return []

        summary_data = await self._get(
            f"{self.NCBI_BASE}/esummary.fcgi",
            params={"db": "pubmed", "id": ",".join(id_list), "retmode": "json"},
        )
        if not summary_data:
            return []

        results: List[EarthSearchResult] = []
        result_map = summary_data.get("result", {})
        for pmid in id_list:
            rec = result_map.get(pmid, {})
            if not isinstance(rec, dict):
                continue
            authors = rec.get("authors", [])
            first_author = authors[0].get("name", "") if authors else ""
            results.append(EarthSearchResult(
                result_id=f"pubmed-{pmid}",
                domain=EarthSearchDomain.RESEARCH,
                source="pubmed",
                title=rec.get("title", query),
                description=f"{first_author} et al. ({rec.get('pubdate', '?')}) — {rec.get('source', '')}",
                data={
                    "pmid": pmid,
                    "authors": [a.get("name", "") for a in authors[:5]],
                    "journal": rec.get("source"),
                    "pub_date": rec.get("pubdate"),
                    "doi": rec.get("elocationid"),
                    "pub_type": rec.get("pubtype"),
                },
                confidence=0.9,
                crep_layer="research",
                url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
            ))
        return results
