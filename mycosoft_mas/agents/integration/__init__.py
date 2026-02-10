"""
Integration agents - API gateway, webhook, MCP bridge, database.
Phase 1 AGENT_CATALOG implementation.
"""

from mycosoft_mas.agents.integration.api_gateway_agent import APIGatewayAgent
from mycosoft_mas.agents.integration.webhook_agent import WebhookAgent
from mycosoft_mas.agents.integration.mcp_bridge_agent import MCPBridgeAgent
from mycosoft_mas.agents.integration.database_agent import DatabaseAgent

__all__ = [
    "APIGatewayAgent",
    "WebhookAgent",
    "MCPBridgeAgent",
    "DatabaseAgent",
]
