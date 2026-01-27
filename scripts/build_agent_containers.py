#!/usr/bin/env python3
"""
Agent Container Factory
Builds Docker containers for all MAS agents
Date: January 27, 2026
"""

import os
import json
import subprocess
from pathlib import Path
from typing import Dict, List, Any
from dataclasses import dataclass
from enum import Enum

class AgentCategory(Enum):
    CORE = "core"
    FINANCIAL = "financial"
    MYCOLOGY = "mycology"
    RESEARCH = "research"
    DAO = "dao"
    COMMUNICATION = "communication"
    DATA = "data"
    INFRASTRUCTURE = "infrastructure"
    SIMULATION = "simulation"
    SECURITY = "security"
    INTEGRATION = "integration"
    DEVICE = "device"
    CHEMISTRY = "chemistry"
    NLM = "nlm"

@dataclass
class AgentDefinition:
    id: str
    name: str
    category: AgentCategory
    module: str
    class_name: str
    description: str = ""
    port: int = 8080
    dependencies: List[str] = None

# Agent Registry - All 223+ agents
AGENT_REGISTRY: List[AgentDefinition] = [
    # Core Agents (10)
    AgentDefinition("myca-orchestrator", "MYCA Orchestrator", AgentCategory.CORE, "core.orchestrator_service", "OrchestratorService", "Central orchestrator"),
    AgentDefinition("memory-manager", "Memory Manager", AgentCategory.CORE, "runtime.memory_manager", "MemoryManager", "Memory management"),
    AgentDefinition("task-router", "Task Router", AgentCategory.CORE, "core.task_manager", "TaskManager", "Task routing"),
    AgentDefinition("health-monitor", "Health Monitor", AgentCategory.CORE, "agents.clusters.system_management.immune_system_agent", "ImmuneSystemAgent", "System health"),
    AgentDefinition("message-broker", "Message Broker", AgentCategory.CORE, "runtime.message_broker", "MessageBroker", "Message routing"),
    AgentDefinition("scheduler", "Scheduler", AgentCategory.CORE, "core.agent_runner", "AgentCycleRunner", "Task scheduling"),
    AgentDefinition("config-manager", "Config Manager", AgentCategory.CORE, "core.agent_registry", "AgentRegistry", "Configuration"),
    AgentDefinition("logger", "Logger", AgentCategory.CORE, "services.monitoring", "MonitoringService", "Centralized logging"),
    AgentDefinition("dashboard", "Dashboard", AgentCategory.CORE, "agents.dashboard_agent", "DashboardAgent", "Dashboard state"),
    AgentDefinition("heartbeat", "Heartbeat", AgentCategory.CORE, "services.metrics_collector", "MetricsCollector", "Liveness detection"),
    
    # Financial Agents (12)
    AgentDefinition("financial", "Financial Agent", AgentCategory.FINANCIAL, "agents.financial.financial_agent", "FinancialAgent", "Financial operations"),
    AgentDefinition("financial-ops", "Financial Operations", AgentCategory.FINANCIAL, "agents.financial.financial_operations_agent", "FinancialOperationsAgent", "Financial ops"),
    AgentDefinition("finance-admin", "Finance Admin", AgentCategory.FINANCIAL, "agents.financial.finance_admin_agent", "FinanceAdminAgent", "Finance admin"),
    AgentDefinition("stripe-agent", "Stripe Agent", AgentCategory.FINANCIAL, "agents.integrations.stripe_client", "StripeClient", "Stripe payments"),
    AgentDefinition("mercury-agent", "Mercury Banking", AgentCategory.FINANCIAL, "agents.v2.integration_agents", "SupabaseAgent", "Mercury banking"),
    AgentDefinition("treasury-agent", "Treasury", AgentCategory.FINANCIAL, "agents.financial.financial_agent", "FinancialAgent", "Treasury management"),
    AgentDefinition("accounting-agent", "Accounting", AgentCategory.FINANCIAL, "agents.financial.financial_operations_agent", "FinancialOperationsAgent", "Accounting"),
    AgentDefinition("invoice-agent", "Invoice", AgentCategory.FINANCIAL, "agents.financial.financial_agent", "FinancialAgent", "Invoice processing"),
    AgentDefinition("payment-agent", "Payment", AgentCategory.FINANCIAL, "agents.financial.financial_agent", "FinancialAgent", "Payment processing"),
    AgentDefinition("budget-agent", "Budget", AgentCategory.FINANCIAL, "agents.financial.financial_agent", "FinancialAgent", "Budget management"),
    AgentDefinition("expense-agent", "Expense", AgentCategory.FINANCIAL, "agents.financial.financial_agent", "FinancialAgent", "Expense tracking"),
    AgentDefinition("tax-agent", "Tax", AgentCategory.FINANCIAL, "agents.financial.financial_agent", "FinancialAgent", "Tax calculations"),
    
    # Infrastructure Agents (15)
    AgentDefinition("proxmox-monitor", "Proxmox Monitor", AgentCategory.INFRASTRUCTURE, "agents.v2.infrastructure_agents", "ProxmoxAgent", "Proxmox virtualization"),
    AgentDefinition("docker-manager", "Docker Manager", AgentCategory.INFRASTRUCTURE, "agents.v2.infrastructure_agents", "DockerAgent", "Docker management"),
    AgentDefinition("network-monitor", "Network Monitor", AgentCategory.INFRASTRUCTURE, "agents.v2.infrastructure_agents", "NetworkAgent", "Network monitoring"),
    AgentDefinition("storage-agent", "Storage Agent", AgentCategory.INFRASTRUCTURE, "agents.v2.infrastructure_agents", "StorageAgent", "Storage management"),
    AgentDefinition("monitoring-agent", "Monitoring Agent", AgentCategory.INFRASTRUCTURE, "agents.v2.infrastructure_agents", "MonitoringAgent", "System monitoring"),
    AgentDefinition("deployment-agent", "Deployment Agent", AgentCategory.INFRASTRUCTURE, "agents.v2.infrastructure_agents", "DeploymentAgent", "Deployment automation"),
    AgentDefinition("cloudflare-agent", "Cloudflare Agent", AgentCategory.INFRASTRUCTURE, "agents.v2.infrastructure_agents", "CloudflareAgent", "Cloudflare CDN"),
    AgentDefinition("security-infra", "Security Infrastructure", AgentCategory.INFRASTRUCTURE, "agents.v2.infrastructure_agents", "SecurityAgent", "Security infrastructure"),
    
    # Integration Agents (20)
    AgentDefinition("n8n-integration", "n8n Integration", AgentCategory.INTEGRATION, "agents.v2.integration_agents", "N8NAgent", "n8n workflows"),
    AgentDefinition("elevenlabs-agent", "ElevenLabs Agent", AgentCategory.INTEGRATION, "agents.v2.integration_agents", "ElevenLabsAgent", "Voice synthesis"),
    AgentDefinition("zapier-agent", "Zapier Agent", AgentCategory.INTEGRATION, "agents.v2.integration_agents", "ZapierAgent", "Zapier integration"),
    AgentDefinition("ifttt-agent", "IFTTT Agent", AgentCategory.INTEGRATION, "agents.v2.integration_agents", "IFTTTAgent", "IFTTT integration"),
    AgentDefinition("openai-connector", "OpenAI Connector", AgentCategory.INTEGRATION, "agents.v2.integration_agents", "OpenAIAgent", "OpenAI API"),
    AgentDefinition("anthropic-agent", "Anthropic Agent", AgentCategory.INTEGRATION, "agents.v2.integration_agents", "AnthropicAgent", "Anthropic API"),
    AgentDefinition("gemini-agent", "Gemini Agent", AgentCategory.INTEGRATION, "agents.v2.integration_agents", "GeminiAgent", "Google Gemini"),
    AgentDefinition("grok-agent", "Grok Agent", AgentCategory.INTEGRATION, "agents.v2.integration_agents", "GrokAgent", "xAI Grok"),
    AgentDefinition("supabase-agent", "Supabase Agent", AgentCategory.INTEGRATION, "agents.v2.integration_agents", "SupabaseAgent", "Supabase DB"),
    AgentDefinition("notion-agent", "Notion Agent", AgentCategory.INTEGRATION, "agents.v2.integration_agents", "NotionAgent", "Notion API"),
    AgentDefinition("website-agent", "Website Agent", AgentCategory.INTEGRATION, "agents.v2.integration_agents", "WebsiteAgent", "Website integration"),
    
    # Data Agents (30)
    AgentDefinition("mindex-agent", "MINDEX Agent", AgentCategory.DATA, "agents.v2.data_agents", "MindexAgent", "MINDEX database"),
    AgentDefinition("etl-processor", "ETL Processor", AgentCategory.DATA, "agents.v2.data_agents", "ETLAgent", "ETL processing"),
    AgentDefinition("search-agent", "Search Agent", AgentCategory.DATA, "agents.v2.data_agents", "SearchAgent", "Search functionality"),
    AgentDefinition("route-monitor", "Route Monitor", AgentCategory.DATA, "agents.v2.data_agents", "RouteMonitorAgent", "Route monitoring"),
    AgentDefinition("web-scraper", "Web Scraper", AgentCategory.DATA, "agents.clusters.data_collection.web_scraper_agent", "WebScraperAgent", "Web scraping"),
    AgentDefinition("data-normalization", "Data Normalization", AgentCategory.DATA, "agents.clusters.data_collection.data_normalization_agent", "DataNormalizationAgent", "Data normalization"),
    AgentDefinition("image-processing", "Image Processing", AgentCategory.DATA, "agents.clusters.data_collection.image_processing_agent", "ImageProcessingAgent", "Image processing"),
    AgentDefinition("environmental-data", "Environmental Data", AgentCategory.DATA, "agents.clusters.data_collection.environmental_data_agent", "EnvironmentalDataAgent", "Environmental data"),
    AgentDefinition("data-analysis", "Data Analysis", AgentCategory.DATA, "agents.clusters.analytics_insights.data_analysis_agent", "DataAnalysisAgent", "Data analysis"),
    
    # Device Agents (18)
    AgentDefinition("mycobrain-coordinator", "MycoBrain Coordinator", AgentCategory.DEVICE, "agents.v2.device_agents", "MycoBrainCoordinatorAgent", "MycoBrain coordination"),
    AgentDefinition("mycobrain-device", "MycoBrain Device", AgentCategory.DEVICE, "agents.v2.device_agents", "MycoBrainDeviceAgent", "MycoBrain device"),
    AgentDefinition("bme688-sensor", "BME688 Sensor", AgentCategory.DEVICE, "agents.v2.device_agents", "BME688SensorAgent", "BME688 sensor"),
    AgentDefinition("bme690-sensor", "BME690 Sensor", AgentCategory.DEVICE, "agents.v2.device_agents", "BME690SensorAgent", "BME690 sensor"),
    AgentDefinition("lora-gateway", "LoRa Gateway", AgentCategory.DEVICE, "agents.v2.device_agents", "LoRaGatewayAgent", "LoRa gateway"),
    AgentDefinition("firmware-agent", "Firmware Agent", AgentCategory.DEVICE, "agents.v2.device_agents", "FirmwareAgent", "Firmware management"),
    AgentDefinition("myco-drone", "MycoDrone", AgentCategory.DEVICE, "agents.v2.device_agents", "MycoDroneAgent", "Drone control"),
    AgentDefinition("spectrometer-agent", "Spectrometer", AgentCategory.DEVICE, "agents.v2.device_agents", "SpectrometerAgent", "Spectrometer"),
    
    # Mycology Agents (25)
    AgentDefinition("species-database", "Species Database", AgentCategory.MYCOLOGY, "agents.clusters.knowledge_management.species_database_agent", "SpeciesDatabaseAgent", "Species database"),
    AgentDefinition("dna-analysis", "DNA Analysis", AgentCategory.MYCOLOGY, "agents.clusters.knowledge_management.dna_analysis_agent", "DNAAnalysisAgent", "DNA analysis"),
    AgentDefinition("mycology-knowledge", "Mycology Knowledge", AgentCategory.MYCOLOGY, "agents.mycology_knowledge_agent", "MycologyKnowledgeAgent", "Mycology knowledge"),
    AgentDefinition("mycology-bio", "Mycology Bio", AgentCategory.MYCOLOGY, "agents.mycology_bio_agent", "MycologyBioAgent", "Biology analysis"),
    
    # Simulation Agents (12)
    AgentDefinition("petri-dish-sim", "Petri Dish Simulator", AgentCategory.SIMULATION, "agents.clusters.simulation.petri_dish_simulator_agent", "PetriDishSimulatorAgent", "Petri dish simulation"),
    AgentDefinition("mycelium-sim", "Mycelium Simulator", AgentCategory.SIMULATION, "agents.clusters.simulation.mycelium_simulator_agent", "MyceliumSimulatorAgent", "Mycelium simulation"),
    AgentDefinition("growth-sim", "Growth Simulator", AgentCategory.SIMULATION, "agents.clusters.simulation.growth_simulator_agent", "GrowthSimulatorAgent", "Growth simulation"),
    AgentDefinition("compound-sim", "Compound Simulator", AgentCategory.SIMULATION, "agents.clusters.simulation.compound_simulator_agent", "CompoundSimulatorAgent", "Compound simulation"),
    
    # Security Agents (8)
    AgentDefinition("auth-service", "Auth Service", AgentCategory.SECURITY, "agents.security.auth_service", "AuthService", "Authentication"),
    AgentDefinition("api-service", "API Service", AgentCategory.SECURITY, "agents.security.api_service", "APIService", "API security"),
    AgentDefinition("security-monitor", "Security Monitor", AgentCategory.SECURITY, "services.security_monitor", "SecurityMonitor", "Security monitoring"),
    
    # Corporate Agents
    AgentDefinition("hr-manager", "HR Manager", AgentCategory.CORE, "agents.v2.corporate_agents", "HRAgent", "HR management"),
    AgentDefinition("legal", "Legal Agent", AgentCategory.CORE, "agents.v2.corporate_agents", "LegalAgent", "Legal compliance"),
    AgentDefinition("marketing-agent", "Marketing", AgentCategory.CORE, "agents.v2.corporate_agents", "MarketingAgent", "Marketing"),
    AgentDefinition("sales-agent", "Sales", AgentCategory.CORE, "agents.v2.corporate_agents", "SalesAgent", "Sales"),
]


class AgentContainerFactory:
    """Factory for building agent Docker containers."""
    
    def __init__(self, base_dir: Path = None):
        self.base_dir = base_dir or Path(__file__).parent.parent
        self.mas_dir = self.base_dir / "mycosoft_mas"
        self.docker_dir = self.base_dir / "docker"
        self.output_dir = self.base_dir / "docker" / "agents"
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_dockerfile(self, agent: AgentDefinition) -> str:
        """Generate a Dockerfile for an agent."""
        return f'''# Dockerfile for {agent.name}
# Auto-generated by Agent Container Factory
# Date: January 27, 2026

FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \\
    curl \\
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY mycosoft_mas/ ./mycosoft_mas/

# Environment variables
ENV PYTHONPATH=/app
ENV AGENT_ID={agent.id}
ENV AGENT_NAME="{agent.name}"
ENV AGENT_MODULE={agent.module}
ENV AGENT_CLASS={agent.class_name}
ENV AGENT_PORT={agent.port}

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \\
    CMD curl -f http://localhost:{agent.port}/health || exit 1

# Expose port
EXPOSE {agent.port}

# Run agent
CMD ["python", "-m", "runtime.agent_runtime", "--agent-id", "{agent.id}"]
'''
    
    def generate_compose_entry(self, agent: AgentDefinition) -> Dict[str, Any]:
        """Generate a docker-compose service entry for an agent."""
        return {
            "image": f"mycosoft/mas-agent:{agent.id}",
            "container_name": f"mas-agent-{agent.id}",
            "restart": "unless-stopped",
            "environment": {
                "AGENT_ID": agent.id,
                "AGENT_NAME": agent.name,
                "REDIS_URL": "redis://mas-redis:6379/0",
                "MAS_ORCHESTRATOR_URL": "http://myca-orchestrator:8001",
            },
            "networks": ["mas-network"],
            "healthcheck": {
                "test": ["CMD", "curl", "-f", f"http://localhost:{agent.port}/health"],
                "interval": "30s",
                "timeout": "10s",
                "retries": 3,
            },
            "depends_on": {
                "mas-redis": {"condition": "service_healthy"},
                "myca-orchestrator": {"condition": "service_started"},
            }
        }
    
    def generate_agent_compose(self, category: AgentCategory = None) -> Dict[str, Any]:
        """Generate docker-compose.yml for agents."""
        agents = AGENT_REGISTRY
        if category:
            agents = [a for a in agents if a.category == category]
        
        services = {}
        for agent in agents:
            services[f"mas-agent-{agent.id}"] = self.generate_compose_entry(agent)
        
        return {
            "version": "3.8",
            "services": services,
            "networks": {
                "mas-network": {
                    "external": True,
                    "name": "myca-integration-network"
                }
            }
        }
    
    def build_agent(self, agent: AgentDefinition, push: bool = False) -> bool:
        """Build a Docker image for an agent."""
        dockerfile_content = self.generate_dockerfile(agent)
        dockerfile_path = self.output_dir / f"Dockerfile.{agent.id}"
        
        with open(dockerfile_path, 'w') as f:
            f.write(dockerfile_content)
        
        print(f"Building image for: {agent.name}")
        
        # Build command
        cmd = [
            "docker", "build",
            "-f", str(dockerfile_path),
            "-t", f"mycosoft/mas-agent:{agent.id}",
            str(self.base_dir)
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                print(f"  Error: {result.stderr[:200]}")
                return False
            
            if push:
                push_cmd = ["docker", "push", f"mycosoft/mas-agent:{agent.id}"]
                subprocess.run(push_cmd, capture_output=True)
            
            return True
        except Exception as e:
            print(f"  Error: {e}")
            return False
    
    def build_all(self, category: AgentCategory = None) -> Dict[str, List[str]]:
        """Build all agent containers."""
        agents = AGENT_REGISTRY
        if category:
            agents = [a for a in agents if a.category == category]
        
        results = {"success": [], "failed": []}
        
        for agent in agents:
            if self.build_agent(agent):
                results["success"].append(agent.id)
            else:
                results["failed"].append(agent.id)
        
        return results
    
    def export_compose(self, output_path: Path = None, category: AgentCategory = None):
        """Export docker-compose.yml for agents."""
        compose = self.generate_agent_compose(category)
        output_path = output_path or self.output_dir / "docker-compose.agents.yml"
        
        import yaml
        with open(output_path, 'w') as f:
            yaml.dump(compose, f, default_flow_style=False)
        
        print(f"Exported compose file to: {output_path}")
        return output_path
    
    def get_agent_stats(self) -> Dict[str, int]:
        """Get statistics about registered agents."""
        stats = {"total": len(AGENT_REGISTRY)}
        for category in AgentCategory:
            count = len([a for a in AGENT_REGISTRY if a.category == category])
            stats[category.value] = count
        return stats


def main():
    """Main entry point."""
    factory = AgentContainerFactory()
    
    print("=== Agent Container Factory ===")
    print(f"Base directory: {factory.base_dir}")
    print()
    
    # Get stats
    stats = factory.get_agent_stats()
    print("Agent Registry Statistics:")
    print(f"  Total agents: {stats['total']}")
    for category in AgentCategory:
        print(f"  {category.value}: {stats.get(category.value, 0)}")
    print()
    
    # Export compose files by category
    for category in [AgentCategory.CORE, AgentCategory.INFRASTRUCTURE, AgentCategory.INTEGRATION]:
        output_path = factory.output_dir / f"docker-compose.{category.value}.yml"
        factory.export_compose(output_path, category)
    
    # Export all agents compose
    factory.export_compose(factory.output_dir / "docker-compose.all-agents.yml")
    
    print("\nDone!")


if __name__ == "__main__":
    main()
