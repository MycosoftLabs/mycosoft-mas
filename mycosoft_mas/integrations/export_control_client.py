"""
Export Control Client for Mycosoft MAS.

Integrates with BIS Consolidated Screening List (trade.gov API) for entity screening.
ITAR/EAR classification reference data; deemed export screening.
Env: TRADE_GOV_API_KEY for trade.gov API (optional).
"""

import logging
import os
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# USML (ITAR) Categories - high-level reference
USML_CATEGORIES = {
    "I": "Firearms, Close Assault Weapons and Combat Shotguns",
    "II": "Guns and Armament",
    "III": "Ammunition/Ordnance",
    "IV": "Launch Vehicles, Guided Missiles, Ballistic Missiles, Rockets, Torpedoes, Bombs and Mines",
    "V": "Explosives and Energetic Materials, Propellants, Incendiary Agents and Their Constituents",
    "VI": "Vessels of War and Special Naval Equipment",
    "VII": "Tanks and Military Vehicles",
    "VIII": "Aircraft and Associated Equipment",
    "IX": "Military Training Equipment",
    "X": "Protective Personnel Equipment",
    "XI": "Military Electronics",
    "XII": "Fire Control, Range Finder, Optical and Guidance and Control Equipment",
    "XIII": "Auxiliary Military Equipment",
    "XIV": "Toxicological Agents, Including Chemical Agents, Biological Agents, and Associated Equipment",
    "XV": "Spacecraft Systems and Associated Equipment",
    "XVI": "Nuclear Weapons, Design and Testing Related Items",
    "XVII": "Classified Articles, Technical Data and Defense Services",
    "XVIII": "Directed Energy Weapons",
    "XIX": "Reserved",
}

# EAR ECCN structure (Category 0-9, Product Group A-E, Control reason)
ECCN_CATEGORIES = {
    "0": "Nuclear materials, facilities, equipment",
    "1": "Materials, chemicals, microorganisms, toxins",
    "2": "Materials processing",
    "3": "Electronics",
    "4": "Computers",
    "5": "Telecommunications and information security",
    "6": "Sensors and lasers",
    "7": "Navigation and avionics",
    "8": "Marine",
    "9": "Propulsion systems, space vehicles, and related equipment",
}


class ExportControlClient:
    """
    Client for export control screening and classification.
    Uses trade.gov Consolidated Screening List API when TRADE_GOV_API_KEY is set.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self._api_key = os.environ.get("TRADE_GOV_API_KEY", "")
        self._base_url = "https://api.trade.gov/consolidated_screening_list/search"
        self._client = None

    async def _get_client(self):
        if self._client is None:
            try:
                import httpx
                self._client = httpx.AsyncClient(timeout=30.0)
            except ImportError:
                logger.warning("httpx not installed; export control screening limited")
        return self._client

    async def health_check(self) -> Dict[str, Any]:
        """Check if client is configured and API reachable."""
        ok = bool(self._api_key)
        return {
            "status": "healthy" if ok else "not_configured",
            "api_configured": ok,
            "message": "TRADE_GOV_API_KEY required for screening" if not ok else "Ready",
        }

    async def screen_entity(self, name: str, countries: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Screen an entity (person or company) against the Consolidated Screening List.
        Returns potential matches; requires manual verification.
        """
        if not self._api_key:
            return {
                "status": "not_configured",
                "message": "TRADE_GOV_API_KEY not set",
                "matches": [],
            }
        client = await self._get_client()
        if not client:
            return {"status": "error", "message": "httpx not available", "matches": []}
        try:
            params = {"api_key": self._api_key, "q": name}
            if countries:
                params["countries"] = ",".join(c[:2] for c in countries[:5])
            resp = await client.get(self._base_url, params=params)
            resp.raise_for_status()
            data = resp.json()
            results = data.get("results", [])
            return {
                "status": "ok",
                "query": name,
                "matches": results[:20],
                "total": len(results),
            }
        except Exception as e:
            logger.exception("Export control screening failed: %s", e)
            return {"status": "error", "message": str(e), "matches": []}

    def get_usml_category(self, category: str) -> Optional[Dict[str, str]]:
        """Look up USML (ITAR) category by Roman numeral."""
        cat = category.upper().strip()
        if cat in USML_CATEGORIES:
            return {"category": cat, "description": USML_CATEGORIES[cat]}
        return None

    def list_usml_categories(self) -> Dict[str, str]:
        """Return all USML categories."""
        return dict(USML_CATEGORIES)

    def get_eccn_category(self, first_char: str) -> Optional[Dict[str, str]]:
        """Look up EAR ECCN category by first digit."""
        if first_char in ECCN_CATEGORIES:
            return {"category": first_char, "description": ECCN_CATEGORIES[first_char]}
        return None

    def list_eccn_categories(self) -> Dict[str, str]:
        """Return all EAR ECCN category descriptions."""
        return dict(ECCN_CATEGORIES)

    def parse_eccn(self, eccn: str) -> Dict[str, Any]:
        """
        Parse ECCN string (e.g., 3A001, 4D994) into components.
        Format: 1 digit (category) + 1 letter (product group) + 3 digits (reason/control)
        """
        eccn = eccn.strip().upper()
        if len(eccn) < 5:
            return {"valid": False, "eccn": eccn, "error": "ECCN must be 5 characters"}
        cat = eccn[0]
        group = eccn[1]
        if group not in "ABCDE":
            return {"valid": False, "eccn": eccn, "error": "Invalid product group"}
        return {
            "valid": True,
            "eccn": eccn,
            "category": cat,
            "category_desc": ECCN_CATEGORIES.get(cat, "Unknown"),
            "product_group": group,
        }

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None
