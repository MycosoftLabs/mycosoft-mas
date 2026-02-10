"""
MAS v2 Agents

All priority agents for the MAS v2 system.
Optional imports so v2 submodules (e.g. myca_agent, planner_agent) load when
heavy deps (docker, runtime) are missing.
"""

import logging

_log = logging.getLogger(__name__)

try:
    from .base_agent_v2 import BaseAgentV2
except Exception as e:
    _log.warning("v2 BaseAgentV2 unavailable: %s", e)
    BaseAgentV2 = None  # type: ignore[misc, assignment]

try:
    from .corporate_agents import (
        CEOAgent,
        CFOAgent,
        CTOAgent,
        COOAgent,
        LegalAgent,
        HRAgent,
        MarketingAgent,
        SalesAgent,
        ProcurementAgent,
    )
except Exception as e:
    _log.warning("v2 corporate_agents unavailable: %s", e)
    CEOAgent = CFOAgent = CTOAgent = COOAgent = None  # type: ignore[misc, assignment]
    LegalAgent = HRAgent = MarketingAgent = SalesAgent = ProcurementAgent = None  # type: ignore[misc, assignment]

try:
    from .infrastructure_agents import (
        ProxmoxAgent,
        DockerAgent,
        NetworkAgent,
        StorageAgent,
        MonitoringAgent,
        DeploymentAgent,
        CloudflareAgent,
        SecurityAgent,
    )
except Exception as e:
    _log.warning("v2 infrastructure_agents unavailable: %s", e)
    ProxmoxAgent = DockerAgent = NetworkAgent = StorageAgent = None  # type: ignore[misc, assignment]
    MonitoringAgent = DeploymentAgent = CloudflareAgent = SecurityAgent = None  # type: ignore[misc, assignment]

try:
    from .device_agents import (
        MycoBrainCoordinatorAgent,
        MycoBrainDeviceAgent,
        BME688SensorAgent,
        BME690SensorAgent,
        LoRaGatewayAgent,
        FirmwareAgent,
        MycoDroneAgent,
        SpectrometerAgent,
    )
except Exception as e:
    _log.warning("v2 device_agents unavailable: %s", e)
    MycoBrainCoordinatorAgent = MycoBrainDeviceAgent = BME688SensorAgent = BME690SensorAgent = None  # type: ignore[misc, assignment]
    LoRaGatewayAgent = FirmwareAgent = MycoDroneAgent = SpectrometerAgent = None  # type: ignore[misc, assignment]

try:
    from .data_agents import (
        MindexAgent,
        ETLAgent,
        SearchAgent,
        RouteMonitorAgent,
    )
except Exception as e:
    _log.warning("v2 data_agents unavailable: %s", e)
    MindexAgent = ETLAgent = SearchAgent = RouteMonitorAgent = None  # type: ignore[misc, assignment]

try:
    from .integration_agents import (
        N8NAgent,
        ElevenLabsAgent,
        ZapierAgent,
        IFTTTAgent,
        OpenAIAgent,
        AnthropicAgent,
        GeminiAgent,
        GrokAgent,
        SupabaseAgent,
        NotionAgent,
        WebsiteAgent,
    )
except Exception as e:
    _log.warning("v2 integration_agents unavailable: %s", e)
    N8NAgent = ElevenLabsAgent = ZapierAgent = IFTTTAgent = None  # type: ignore[misc, assignment]
    OpenAIAgent = AnthropicAgent = GeminiAgent = GrokAgent = None  # type: ignore[misc, assignment]
    SupabaseAgent = NotionAgent = WebsiteAgent = None  # type: ignore[misc, assignment]


__all__ = [
    # Base
    "BaseAgentV2",
    # Corporate
    "CEOAgent",
    "CFOAgent",
    "CTOAgent",
    "COOAgent",
    "LegalAgent",
    "HRAgent",
    "MarketingAgent",
    "SalesAgent",
    "ProcurementAgent",
    # Infrastructure
    "ProxmoxAgent",
    "DockerAgent",
    "NetworkAgent",
    "StorageAgent",
    "MonitoringAgent",
    "DeploymentAgent",
    "CloudflareAgent",
    "SecurityAgent",
    # Device
    "MycoBrainCoordinatorAgent",
    "MycoBrainDeviceAgent",
    "BME688SensorAgent",
    "BME690SensorAgent",
    "LoRaGatewayAgent",
    "FirmwareAgent",
    "MycoDroneAgent",
    "SpectrometerAgent",
    # Data
    "MindexAgent",
    "ETLAgent",
    "SearchAgent",
    "RouteMonitorAgent",
    # Integration
    "N8NAgent",
    "ElevenLabsAgent",
    "ZapierAgent",
    "IFTTTAgent",
    "OpenAIAgent",
    "AnthropicAgent",
    "GeminiAgent",
    "GrokAgent",
    "SupabaseAgent",
    "NotionAgent",
    "WebsiteAgent",
]


# Agent registry for easy lookup (only non-None classes)
def _build_registry():
    reg = {}
    if CEOAgent is not None:
        reg.update({"ceo-agent": CEOAgent, "cfo-agent": CFOAgent, "cto-agent": CTOAgent, "coo-agent": COOAgent, "legal-agent": LegalAgent, "hr-agent": HRAgent, "marketing-agent": MarketingAgent, "sales-agent": SalesAgent, "procurement-agent": ProcurementAgent})
    if ProxmoxAgent is not None:
        reg.update({"proxmox-agent": ProxmoxAgent, "docker-agent": DockerAgent, "network-agent": NetworkAgent, "storage-agent": StorageAgent, "monitoring-agent": MonitoringAgent, "deployment-agent": DeploymentAgent, "cloudflare-agent": CloudflareAgent, "security-agent": SecurityAgent})
    if MycoBrainCoordinatorAgent is not None:
        reg.update({"mycobrain-coordinator": MycoBrainCoordinatorAgent, "bme688-agent": BME688SensorAgent, "bme690-agent": BME690SensorAgent, "lora-gateway-agent": LoRaGatewayAgent, "firmware-agent": FirmwareAgent, "mycodrone-agent": MycoDroneAgent, "spectrometer-agent": SpectrometerAgent})
    if MindexAgent is not None:
        reg.update({"mindex-agent": MindexAgent, "etl-agent": ETLAgent, "search-agent": SearchAgent})
    if N8NAgent is not None:
        reg.update({"n8n-agent": N8NAgent, "elevenlabs-agent": ElevenLabsAgent, "zapier-agent": ZapierAgent, "ifttt-agent": IFTTTAgent, "openai-agent": OpenAIAgent, "anthropic-agent": AnthropicAgent, "gemini-agent": GeminiAgent, "grok-agent": GrokAgent, "supabase-agent": SupabaseAgent, "notion-agent": NotionAgent, "website-agent": WebsiteAgent})
    return reg


AGENT_REGISTRY = _build_registry()


def get_agent_class(agent_id: str):
    """Get agent class by ID"""
    return AGENT_REGISTRY.get(agent_id)


def list_available_agents():
    """List all available agent IDs"""
    return list(AGENT_REGISTRY.keys())


def count_agents_by_category():
    """Count agents by category"""
    return {
        "corporate": 9,
        "infrastructure": 8,
        "device": 7,
        "data": 3,
        "integration": 11,
        "total": 38,
    }
