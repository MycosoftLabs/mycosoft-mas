"""Cross-check harness outputs against MINDEX facts when applicable."""

from __future__ import annotations

import re
from typing import Any

from mycosoft_mas.harness.mindex_client import MindexClient


class HarnessEvaluator:
    def __init__(self, mindex: MindexClient) -> None:
        self._mindex = mindex

    async def verify_species_mention(self, text: str, species_id: str | None) -> dict[str, Any]:
        """If answer cites a species ID, compare to MINDEX record; else heuristic only."""
        out: dict[str, Any] = {"needs_review": False, "reasons": []}
        if not species_id:
            m = re.search(r"species[/\\](\d+)", text)
            if m:
                species_id = m.group(1)
        if not species_id:
            return out
        rec = await self._mindex.get_species(species_id)
        if rec is None:
            out["needs_review"] = True
            out["reasons"].append("species_id_not_in_mindex")
            return out
        sci = str(rec.get("scientific_name") or rec.get("scientificName") or "")
        if sci and sci.lower() not in text.lower():
            out["needs_review"] = True
            out["reasons"].append("scientific_name_mismatch")
        return out
