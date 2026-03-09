"""
Capability Discovery — Search approved sources for capabilities.

Approved sources:
- Internal skill registry (existing skills)
- Approved packages (curated package list)
- MCP servers (available tool servers)
- Workflow library (n8n workflow templates)
- Agent capabilities (other agents' shared skills)

Never searches unapproved sources. Never runs arbitrary code from the internet.

Architecture: March 9, 2026
"""

from __future__ import annotations

import logging
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ApprovedSource(str, Enum):
    """Sources approved for capability discovery."""

    INTERNAL_REGISTRY = "internal_registry"
    APPROVED_PACKAGES = "approved_packages"
    MCP_SERVERS = "mcp_servers"
    WORKFLOW_LIBRARY = "workflow_library"
    AGENT_CAPABILITIES = "agent_capabilities"


# Curated list of approved packages by capability domain
_APPROVED_PACKAGES: Dict[str, List[Dict[str, str]]] = {
    "payment_processing": [
        {"name": "stripe", "package": "stripe", "description": "Stripe payment processing"},
    ],
    "accounting_integration": [
        {"name": "quickbooks", "package": "python-quickbooks", "description": "QuickBooks integration"},
    ],
    "email_management": [
        {"name": "email_handler", "package": "aiosmtplib", "description": "Async email sending"},
    ],
    "data_analysis": [
        {"name": "pandas_analyzer", "package": "pandas", "description": "Data analysis with pandas"},
    ],
    "data_visualization": [
        {"name": "plotly_viz", "package": "plotly", "description": "Interactive visualizations"},
    ],
    "web_scraping": [
        {"name": "httpx_scraper", "package": "httpx", "description": "HTTP client for web requests"},
    ],
    "language_translation": [
        {"name": "translation", "package": "deep-translator", "description": "Language translation"},
    ],
}

# Known internal agent capabilities
_AGENT_CAPABILITIES: Dict[str, List[Dict[str, str]]] = {
    "deployment_automation": [
        {"name": "deployment_agent", "agent": "DeploymentAgent", "description": "Infrastructure deployment"},
    ],
    "system_monitoring": [
        {"name": "monitoring_agent", "agent": "InfrastructureAgent", "description": "System health monitoring"},
    ],
    "calendar_management": [
        {"name": "secretary_agent", "agent": "SecretaryAgent", "description": "Calendar and scheduling"},
    ],
}


class CapabilityDiscovery:
    """
    Search approved sources for capability candidates.

    Only searches known, vetted sources. Never reaches out to
    arbitrary internet resources or unapproved registries.
    """

    def __init__(self) -> None:
        self._search_history: List[Dict[str, Any]] = []

    async def search(
        self,
        capability_name: str,
        sources: Optional[List[ApprovedSource]] = None,
    ) -> List:
        """
        Search for capability candidates across approved sources.

        Returns CapabilityCandidate objects from foundry module.
        """
        from mycosoft_mas.capabilities.foundry import CapabilityCandidate

        if sources is None:
            sources = list(ApprovedSource)

        candidates: List[CapabilityCandidate] = []

        for source in sources:
            found = await self._search_source(source, capability_name)
            candidates.extend(found)

        self._search_history.append(
            {
                "capability": capability_name,
                "sources_searched": [s.value for s in sources],
                "candidates_found": len(candidates),
            }
        )

        logger.info(
            "Discovery search for '%s': %d candidates from %d sources",
            capability_name, len(candidates), len(sources),
        )

        return candidates

    async def _search_source(
        self, source: ApprovedSource, capability_name: str
    ) -> List:
        """Search a specific approved source."""
        from mycosoft_mas.capabilities.foundry import CapabilityCandidate

        if source == ApprovedSource.APPROVED_PACKAGES:
            return self._search_packages(capability_name)

        if source == ApprovedSource.AGENT_CAPABILITIES:
            return self._search_agents(capability_name)

        if source == ApprovedSource.INTERNAL_REGISTRY:
            return self._search_internal_registry(capability_name)

        if source == ApprovedSource.WORKFLOW_LIBRARY:
            return self._search_workflows(capability_name)

        if source == ApprovedSource.MCP_SERVERS:
            return self._search_mcp_servers(capability_name)

        return []

    def _search_packages(self, capability_name: str) -> List:
        """Search curated approved packages."""
        from mycosoft_mas.capabilities.foundry import CapabilityCandidate

        candidates = []
        packages = _APPROVED_PACKAGES.get(capability_name, [])
        for pkg in packages:
            candidates.append(
                CapabilityCandidate(
                    source=f"approved_package:{pkg['package']}",
                    name=pkg["name"],
                    description=pkg["description"],
                    source_type="approved_package",
                    confidence=0.8,
                    requirements=[pkg["package"]],
                    risk_tier="medium",
                )
            )
        return candidates

    def _search_agents(self, capability_name: str) -> List:
        """Search existing agent capabilities."""
        from mycosoft_mas.capabilities.foundry import CapabilityCandidate

        candidates = []
        agent_caps = _AGENT_CAPABILITIES.get(capability_name, [])
        for cap in agent_caps:
            candidates.append(
                CapabilityCandidate(
                    source=f"agent:{cap['agent']}",
                    name=cap["name"],
                    description=cap["description"],
                    source_type="agent_capability",
                    confidence=0.9,  # High confidence for internal agents
                    risk_tier="low",
                )
            )
        return candidates

    def _search_internal_registry(self, capability_name: str) -> List:
        """Search the internal skill registry."""
        # In production, this would query the actual skill registry
        return []

    def _search_workflows(self, capability_name: str) -> List:
        """Search n8n workflow library."""
        # In production, this would search n8n workflow templates
        return []

    def _search_mcp_servers(self, capability_name: str) -> List:
        """Search available MCP servers."""
        # In production, this would query available MCP tool servers
        return []

    def get_search_history(self) -> List[Dict[str, Any]]:
        """Return search history."""
        return list(self._search_history)
