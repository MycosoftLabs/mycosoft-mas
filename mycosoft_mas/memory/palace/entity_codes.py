"""
Entity Code Registry for AAAK Compression.
Created: April 7, 2026

Maps agents, domains, and system entities to 3-character codes
for AAAK compression. Extensible via registration.
"""

from typing import Dict, Optional

# Pre-defined entity codes for MYCA's ecosystem
AGENT_CODES: Dict[str, str] = {
    # Core
    "orchestrator": "ORC",
    "agent_manager": "AMG",
    "cluster_manager": "CLM",
    # Corporate
    "ceo_agent": "CEO",
    "cfo_agent": "CFO",
    "cto_agent": "CTO",
    "coo_agent": "COO",
    "legal_agent": "LEG",
    "hr_agent": "HRA",
    # Infrastructure
    "proxmox_agent": "PRX",
    "docker_agent": "DOC",
    "network_agent": "NET",
    "deployment_agent": "DEP",
    "cloudflare_agent": "CFL",
    # Scientific
    "lab_agent": "LAB",
    "hypothesis_agent": "HYP",
    "simulation_agent": "SIM",
    "alphafold_agent": "ALF",
    # Device
    "mycobrain_coordinator": "MBC",
    "firmware_agent": "FWA",
    # Data
    "mindex_agent": "MIX",
    "etl_agent": "ETL",
    "search_agent": "SRC",
    "route_monitor_agent": "RMA",
    # Integration
    "n8n_agent": "N8N",
    "notion_agent": "NOT",
    "website_agent": "WEB",
    "anthropic_agent": "ANT",
    # Financial
    "financial_agent": "FIN",
    # Security
    "security_agent": "SEC",
    "guardian_agent": "GRD",
    # Mycology
    "mycology_bio_agent": "MYB",
    "mycology_knowledge_agent": "MYK",
    # Earth2
    "earth2_orchestrator": "E2O",
    "weather_forecast": "WTH",
    "climate_simulation": "CLI",
    # V2/Advanced
    "grounding_agent": "GND",
    "intention_agent": "INT",
    "reflection_agent": "REF",
    "planner_agent": "PLN",
    # Memory
    "graph_memory_agent": "GMA",
    "long_term_memory_agent": "LTM",
    "vector_memory_agent": "VMA",
    # Business
    "secretary_agent": "SEC",
    "sales_agent": "SAL",
    "marketing_agent": "MKT",
    "project_manager_agent": "PMA",
}

# Domain entity codes
DOMAIN_CODES: Dict[str, str] = {
    # Systems
    "mycosoft": "MYC",
    "mindex": "MIX",
    "natureos": "NOS",
    "mycobrain": "MBR",
    "earth2": "E2D",
    "crep": "CRP",
    "personaplex": "PPX",
    # VMs
    "sandbox": "SBX",
    "mas_vm": "MAS",
    "mindex_vm": "MDX",
    "gpu_vm": "GPU",
    "myca_workspace": "MWS",
    # Databases
    "postgresql": "PGS",
    "redis": "RDS",
    "qdrant": "QDR",
    # Integrations
    "notion": "NOT",
    "slack": "SLK",
    "github": "GHB",
    "stripe": "STR",
    "cloudflare": "CLF",
    "n8n": "N8N",
}

# Emotion codes (for MYCA's emotional states)
EMOTION_CODES: Dict[str, str] = {
    "curiosity": "cur",
    "warmth": "wrm",
    "excitement": "exc",
    "concern": "cnr",
    "satisfaction": "sat",
    "frustration": "frs",
    "empathy": "emp",
    "confidence": "cnf",
    "uncertainty": "unc",
    "determination": "det",
    "creativity": "cre",
    "focus": "fcs",
    "calm": "clm",
    "urgency": "urg",
    "pride": "prd",
    "worry": "wry",
    "joy": "joy",
    "surprise": "sur",
}

# Flag definitions (importance markers)
FLAG_KEYWORDS: Dict[str, list] = {
    "ORIGIN": ["founded", "created", "launched", "first time", "genesis", "born"],
    "CORE": ["fundamental", "essential", "principle", "always", "core", "critical"],
    "PIVOT": ["turning point", "breakthrough", "realized", "epiphany", "pivot"],
    "DECISION": ["decided", "chose", "switched", "because", "selected"],
    "TECHNICAL": ["api", "database", "deploy", "algorithm", "architecture"],
    "SPECIES": ["species", "genus", "family", "mushroom", "fungal"],
    "DEVICE": ["sensor", "mycobrain", "fci", "electrode", "bme"],
    "CREP": ["flight", "vessel", "satellite", "weather", "environmental"],
    "WEATHER": ["forecast", "climate", "temperature", "simulation"],
    "COMPOUND": ["compound", "molecule", "alkaloid", "terpene", "chemical"],
}


class EntityCodeRegistry:
    """Manages entity-to-code mappings for AAAK compression."""

    def __init__(self):
        self._codes: Dict[str, str] = {}
        self._codes.update(AGENT_CODES)
        self._codes.update(DOMAIN_CODES)
        self._reverse: Dict[str, str] = {v: k for k, v in self._codes.items()}

    def get_code(self, entity: str) -> str:
        """Get 3-char code for an entity, auto-generating if needed."""
        entity_lower = entity.lower().replace(" ", "_")
        if entity_lower in self._codes:
            return self._codes[entity_lower]

        # Auto-generate: first 3 uppercase chars
        code = entity[:3].upper()
        while code in self._reverse:
            # Collision — try next chars
            if len(entity) > 3:
                code = (entity[0] + entity[2] + entity[-1]).upper()
            else:
                code = code[:2] + str(len(self._codes) % 10)

        self._codes[entity_lower] = code
        self._reverse[code] = entity_lower
        return code

    def get_entity(self, code: str) -> Optional[str]:
        """Look up entity name from code."""
        return self._reverse.get(code)

    def register(self, entity: str, code: str) -> None:
        """Manually register an entity-code mapping."""
        self._codes[entity.lower().replace(" ", "_")] = code
        self._reverse[code] = entity.lower().replace(" ", "_")

    def all_codes(self) -> Dict[str, str]:
        """Return all registered codes."""
        return dict(self._codes)


# Singleton
_registry: Optional[EntityCodeRegistry] = None


def get_entity_registry() -> EntityCodeRegistry:
    """Get the singleton entity code registry."""
    global _registry
    if _registry is None:
        _registry = EntityCodeRegistry()
    return _registry
