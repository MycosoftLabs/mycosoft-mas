"""
MAS v2 Agents

All priority agents for the MAS v2 system.
"""

from .base_agent_v2 import BaseAgentV2

# Corporate Agents
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

# Infrastructure Agents
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

# Device Agents
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

# Data Agents
from .data_agents import (
    MindexAgent,
    ETLAgent,
    SearchAgent,
    RouteMonitorAgent,
)

# Integration Agents
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


# Agent registry for easy lookup
AGENT_REGISTRY = {
    # Corporate (9)
    "ceo-agent": CEOAgent,
    "cfo-agent": CFOAgent,
    "cto-agent": CTOAgent,
    "coo-agent": COOAgent,
    "legal-agent": LegalAgent,
    "hr-agent": HRAgent,
    "marketing-agent": MarketingAgent,
    "sales-agent": SalesAgent,
    "procurement-agent": ProcurementAgent,
    # Infrastructure (8)
    "proxmox-agent": ProxmoxAgent,
    "docker-agent": DockerAgent,
    "network-agent": NetworkAgent,
    "storage-agent": StorageAgent,
    "monitoring-agent": MonitoringAgent,
    "deployment-agent": DeploymentAgent,
    "cloudflare-agent": CloudflareAgent,
    "security-agent": SecurityAgent,
    # Device (8)
    "mycobrain-coordinator": MycoBrainCoordinatorAgent,
    "bme688-agent": BME688SensorAgent,
    "bme690-agent": BME690SensorAgent,
    "lora-gateway-agent": LoRaGatewayAgent,
    "firmware-agent": FirmwareAgent,
    "mycodrone-agent": MycoDroneAgent,
    "spectrometer-agent": SpectrometerAgent,
    # Data (4)
    "mindex-agent": MindexAgent,
    "etl-agent": ETLAgent,
    "search-agent": SearchAgent,
    # Integration (11)
    "n8n-agent": N8NAgent,
    "elevenlabs-agent": ElevenLabsAgent,
    "zapier-agent": ZapierAgent,
    "ifttt-agent": IFTTTAgent,
    "openai-agent": OpenAIAgent,
    "anthropic-agent": AnthropicAgent,
    "gemini-agent": GeminiAgent,
    "grok-agent": GrokAgent,
    "supabase-agent": SupabaseAgent,
    "notion-agent": NotionAgent,
    "website-agent": WebsiteAgent,
}


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
