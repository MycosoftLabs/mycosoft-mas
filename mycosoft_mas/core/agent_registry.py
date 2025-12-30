"""
MYCA Agent Registry - Comprehensive catalog of all MAS agents

This module provides a centralized registry of all agents in the Mycosoft MAS,
enabling MYCA to discover, route to, and manage agents via voice commands.
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class AgentCategory(str, Enum):
    """Categories of agents in the MAS."""
    CORE = "core"
    FINANCIAL = "financial"
    CORPORATE = "corporate"
    MYCOLOGY = "mycology"
    RESEARCH = "research"
    DATA = "data"
    INFRASTRUCTURE = "infrastructure"
    SIMULATION = "simulation"
    COMMUNICATION = "communication"
    SECURITY = "security"
    DAO = "dao"
    INTEGRATION = "integration"


class AgentCapability(str, Enum):
    """Capabilities that agents can have."""
    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"
    ANALYZE = "analyze"
    NOTIFY = "notify"
    MANAGE = "manage"
    CONTROL = "control"


@dataclass
class AgentDefinition:
    """Definition of an agent in the registry."""
    agent_id: str
    name: str
    display_name: str
    description: str
    category: AgentCategory
    capabilities: List[AgentCapability]
    module_path: str
    class_name: str
    keywords: List[str] = field(default_factory=list)
    voice_triggers: List[str] = field(default_factory=list)
    requires_confirmation: bool = False
    is_active: bool = False
    config_key: Optional[str] = None


class AgentRegistry:
    """
    Central registry of all MAS agents.
    
    Used by MYCA orchestrator for:
    - Agent discovery and routing
    - Voice command matching
    - Agent lifecycle management
    - Capability checking
    """
    
    def __init__(self):
        self._agents: Dict[str, AgentDefinition] = {}
        self._load_builtin_agents()
        
    def _load_builtin_agents(self):
        """Load all built-in agent definitions."""
        
        # ========== CORE AGENTS ==========
        self.register(AgentDefinition(
            agent_id="mycology_bio",
            name="MycologyBioAgent",
            display_name="Mycology Bio Agent",
            description="Handles mycology research, species identification, and biological data",
            category=AgentCategory.MYCOLOGY,
            capabilities=[AgentCapability.READ, AgentCapability.ANALYZE],
            module_path="mycosoft_mas.agents.mycology_bio_agent",
            class_name="MycologyBioAgent",
            keywords=["mycology", "mushroom", "fungi", "species", "biology", "research"],
            voice_triggers=["mycology", "mushroom research", "fungi", "species database"],
            config_key="mycology"
        ))
        
        self.register(AgentDefinition(
            agent_id="mycology_knowledge",
            name="MycologyKnowledgeAgent",
            display_name="Mycology Knowledge Agent",
            description="Manages mycology knowledge base and scientific literature",
            category=AgentCategory.MYCOLOGY,
            capabilities=[AgentCapability.READ, AgentCapability.ANALYZE],
            module_path="mycosoft_mas.agents.mycology_knowledge_agent",
            class_name="MycologyKnowledgeAgent",
            keywords=["knowledge", "literature", "scientific", "papers", "mycology"],
            voice_triggers=["mycology knowledge", "scientific papers", "research papers"]
        ))
        
        self.register(AgentDefinition(
            agent_id="financial",
            name="FinancialAgent",
            display_name="Financial Agent",
            description="Handles financial operations, budgeting, and accounting",
            category=AgentCategory.FINANCIAL,
            capabilities=[AgentCapability.READ, AgentCapability.WRITE, AgentCapability.ANALYZE],
            module_path="mycosoft_mas.agents.financial.financial_agent",
            class_name="FinancialAgent",
            keywords=["financial", "budget", "money", "accounting", "expenses", "revenue"],
            voice_triggers=["financial", "budget", "money", "accounting", "expenses"],
            config_key="financial"
        ))
        
        self.register(AgentDefinition(
            agent_id="finance_admin",
            name="FinanceAdminAgent",
            display_name="Finance Admin Agent",
            description="Administrative financial operations and approvals",
            category=AgentCategory.FINANCIAL,
            capabilities=[AgentCapability.READ, AgentCapability.WRITE, AgentCapability.MANAGE],
            module_path="mycosoft_mas.agents.finance_admin_agent",
            class_name="FinanceAdminAgent",
            keywords=["finance", "admin", "approval", "payments"],
            voice_triggers=["finance admin", "payment approval"],
            requires_confirmation=True
        ))
        
        self.register(AgentDefinition(
            agent_id="corporate_ops",
            name="CorporateOperationsAgent",
            display_name="Corporate Operations Agent",
            description="Manages corporate operations, compliance, and governance",
            category=AgentCategory.CORPORATE,
            capabilities=[AgentCapability.READ, AgentCapability.WRITE, AgentCapability.MANAGE],
            module_path="mycosoft_mas.agents.corporate.corporate_operations_agent",
            class_name="CorporateOperationsAgent",
            keywords=["corporate", "operations", "compliance", "governance"],
            voice_triggers=["corporate", "operations", "compliance"],
            config_key="corporate"
        ))
        
        self.register(AgentDefinition(
            agent_id="board_ops",
            name="BoardOperationsAgent",
            display_name="Board Operations Agent",
            description="Manages board meetings, resolutions, and governance",
            category=AgentCategory.CORPORATE,
            capabilities=[AgentCapability.READ, AgentCapability.WRITE],
            module_path="mycosoft_mas.agents.corporate.board_operations_agent",
            class_name="BoardOperationsAgent",
            keywords=["board", "meetings", "resolutions", "governance"],
            voice_triggers=["board", "board meeting", "resolution"]
        ))
        
        self.register(AgentDefinition(
            agent_id="legal_compliance",
            name="LegalComplianceAgent",
            display_name="Legal Compliance Agent",
            description="Handles legal compliance and regulatory requirements",
            category=AgentCategory.CORPORATE,
            capabilities=[AgentCapability.READ, AgentCapability.ANALYZE],
            module_path="mycosoft_mas.agents.corporate.legal_compliance_agent",
            class_name="LegalComplianceAgent",
            keywords=["legal", "compliance", "regulatory", "laws"],
            voice_triggers=["legal", "compliance", "regulatory"]
        ))
        
        self.register(AgentDefinition(
            agent_id="marketing",
            name="MarketingAgent",
            display_name="Marketing Agent",
            description="Manages marketing campaigns, content, and analytics",
            category=AgentCategory.COMMUNICATION,
            capabilities=[AgentCapability.READ, AgentCapability.WRITE, AgentCapability.ANALYZE],
            module_path="mycosoft_mas.agents.marketing_agent",
            class_name="MarketingAgent",
            keywords=["marketing", "campaign", "content", "social media", "analytics"],
            voice_triggers=["marketing", "campaign", "social media"],
            config_key="marketing"
        ))
        
        self.register(AgentDefinition(
            agent_id="sales",
            name="SalesAgent",
            display_name="Sales Agent",
            description="Manages sales pipeline, leads, and customer relationships",
            category=AgentCategory.COMMUNICATION,
            capabilities=[AgentCapability.READ, AgentCapability.WRITE],
            module_path="mycosoft_mas.agents.sales_agent",
            class_name="SalesAgent",
            keywords=["sales", "leads", "customers", "pipeline", "deals"],
            voice_triggers=["sales", "leads", "customers", "deals"]
        ))
        
        self.register(AgentDefinition(
            agent_id="project_manager",
            name="ProjectManagerAgent",
            display_name="Project Manager Agent",
            description="Manages projects, tasks, and team coordination",
            category=AgentCategory.CORE,
            capabilities=[AgentCapability.READ, AgentCapability.WRITE, AgentCapability.MANAGE],
            module_path="mycosoft_mas.agents.project_manager_agent",
            class_name="ProjectManagerAgent",
            keywords=["project", "task", "milestone", "deadline", "team"],
            voice_triggers=["project", "task", "milestone", "deadline"],
            config_key="project"
        ))
        
        self.register(AgentDefinition(
            agent_id="myco_dao",
            name="MycoDAOAgent",
            display_name="MycoDAO Agent",
            description="Manages DAO governance, voting, and token operations",
            category=AgentCategory.DAO,
            capabilities=[AgentCapability.READ, AgentCapability.WRITE, AgentCapability.EXECUTE],
            module_path="mycosoft_mas.agents.myco_dao_agent",
            class_name="MycoDAOAgent",
            keywords=["dao", "voting", "governance", "tokens", "proposals"],
            voice_triggers=["dao", "voting", "governance", "token", "proposal"],
            config_key="mycodao",
            requires_confirmation=True
        ))
        
        self.register(AgentDefinition(
            agent_id="ip_tokenization",
            name="IPTokenizationAgent",
            display_name="IP Tokenization Agent",
            description="Manages intellectual property tokenization and licensing",
            category=AgentCategory.DAO,
            capabilities=[AgentCapability.READ, AgentCapability.WRITE],
            module_path="mycosoft_mas.agents.ip_tokenization_agent",
            class_name="IPTokenizationAgent",
            keywords=["ip", "intellectual property", "tokenization", "licensing", "patents"],
            voice_triggers=["ip", "intellectual property", "tokenization", "patent"],
            config_key="ip"
        ))
        
        self.register(AgentDefinition(
            agent_id="ip_agent",
            name="IPAgent",
            display_name="IP Agent",
            description="Core IP management and tracking",
            category=AgentCategory.DAO,
            capabilities=[AgentCapability.READ, AgentCapability.WRITE],
            module_path="mycosoft_mas.agents.ip_agent",
            class_name="IPAgent",
            keywords=["ip", "intellectual property", "patents", "trademarks"],
            voice_triggers=["ip management", "patent tracking"]
        ))
        
        self.register(AgentDefinition(
            agent_id="dashboard",
            name="DashboardAgent",
            display_name="Dashboard Agent",
            description="Provides system dashboards and visualizations",
            category=AgentCategory.CORE,
            capabilities=[AgentCapability.READ, AgentCapability.ANALYZE],
            module_path="mycosoft_mas.agents.dashboard_agent",
            class_name="DashboardAgent",
            keywords=["dashboard", "visualization", "metrics", "status", "overview"],
            voice_triggers=["dashboard", "status", "overview", "metrics"],
            config_key="dashboard"
        ))
        
        self.register(AgentDefinition(
            agent_id="opportunity_scout",
            name="OpportunityScout",
            display_name="Opportunity Scout Agent",
            description="Identifies business opportunities and market trends",
            category=AgentCategory.RESEARCH,
            capabilities=[AgentCapability.READ, AgentCapability.ANALYZE],
            module_path="mycosoft_mas.agents.opportunity_scout",
            class_name="OpportunityScout",
            keywords=["opportunity", "market", "trends", "analysis", "business"],
            voice_triggers=["opportunity", "market trends", "business opportunity"],
            config_key="opportunity_scout"
        ))
        
        self.register(AgentDefinition(
            agent_id="research",
            name="ResearchAgent",
            display_name="Research Agent",
            description="Conducts research and analysis",
            category=AgentCategory.RESEARCH,
            capabilities=[AgentCapability.READ, AgentCapability.ANALYZE],
            module_path="mycosoft_mas.agents.research_agent",
            class_name="ResearchAgent",
            keywords=["research", "analysis", "study", "investigation"],
            voice_triggers=["research", "analyze", "study"]
        ))
        
        self.register(AgentDefinition(
            agent_id="experiment",
            name="ExperimentAgent",
            display_name="Experiment Agent",
            description="Manages laboratory experiments and trials",
            category=AgentCategory.RESEARCH,
            capabilities=[AgentCapability.READ, AgentCapability.WRITE, AgentCapability.EXECUTE],
            module_path="mycosoft_mas.agents.experiment_agent",
            class_name="ExperimentAgent",
            keywords=["experiment", "lab", "trial", "test"],
            voice_triggers=["experiment", "lab", "trial"],
            requires_confirmation=True
        ))
        
        self.register(AgentDefinition(
            agent_id="token_economics",
            name="TokenEconomicsAgent",
            display_name="Token Economics Agent",
            description="Analyzes token economics and cryptocurrency markets",
            category=AgentCategory.FINANCIAL,
            capabilities=[AgentCapability.READ, AgentCapability.ANALYZE],
            module_path="mycosoft_mas.agents.token_economics_agent",
            class_name="TokenEconomicsAgent",
            keywords=["token", "crypto", "economics", "market", "trading"],
            voice_triggers=["token economics", "crypto market", "token price"]
        ))
        
        self.register(AgentDefinition(
            agent_id="secretary",
            name="SecretaryAgent",
            display_name="Secretary Agent",
            description="Manages scheduling, notifications, and reminders",
            category=AgentCategory.CORE,
            capabilities=[AgentCapability.READ, AgentCapability.WRITE, AgentCapability.NOTIFY],
            module_path="mycosoft_mas.agents.secretary_agent",
            class_name="SecretaryAgent",
            keywords=["schedule", "calendar", "reminder", "notification", "meeting"],
            voice_triggers=["schedule", "calendar", "reminder", "meeting"]
        ))
        
        self.register(AgentDefinition(
            agent_id="desktop_automation",
            name="DesktopAutomationAgent",
            display_name="Desktop Automation Agent",
            description="Automates desktop tasks and UI interactions",
            category=AgentCategory.INTEGRATION,
            capabilities=[AgentCapability.EXECUTE, AgentCapability.CONTROL],
            module_path="mycosoft_mas.agents.desktop_automation_agent",
            class_name="DesktopAutomationAgent",
            keywords=["desktop", "automation", "ui", "click", "type"],
            voice_triggers=["desktop automation", "automate", "click", "type"],
            requires_confirmation=True
        ))
        
        # ========== MYCOBRAIN AGENTS ==========
        self.register(AgentDefinition(
            agent_id="mycobrain_device",
            name="DeviceAgent",
            display_name="MycoBrain Device Agent",
            description="Manages MycoBrain hardware devices and sensors",
            category=AgentCategory.INFRASTRUCTURE,
            capabilities=[AgentCapability.READ, AgentCapability.CONTROL],
            module_path="mycosoft_mas.agents.mycobrain.device_agent",
            class_name="DeviceAgent",
            keywords=["mycobrain", "device", "sensor", "hardware", "uart"],
            voice_triggers=["mycobrain device", "sensor", "hardware"]
        ))
        
        self.register(AgentDefinition(
            agent_id="mycobrain_ingestion",
            name="IngestionAgent",
            display_name="MycoBrain Ingestion Agent",
            description="Ingests and processes MycoBrain sensor data",
            category=AgentCategory.DATA,
            capabilities=[AgentCapability.READ, AgentCapability.WRITE],
            module_path="mycosoft_mas.agents.mycobrain.ingestion_agent",
            class_name="IngestionAgent",
            keywords=["ingestion", "data", "sensor", "stream"],
            voice_triggers=["data ingestion", "sensor data"]
        ))
        
        # ========== DATA COLLECTION CLUSTER ==========
        self.register(AgentDefinition(
            agent_id="web_scraper",
            name="WebScraperAgent",
            display_name="Web Scraper Agent",
            description="Scrapes web data and extracts information",
            category=AgentCategory.DATA,
            capabilities=[AgentCapability.READ, AgentCapability.EXECUTE],
            module_path="mycosoft_mas.agents.clusters.data_collection.web_scraper_agent",
            class_name="WebScraperAgent",
            keywords=["scraper", "web", "crawl", "extract"],
            voice_triggers=["scrape", "web scraper", "crawl website"]
        ))
        
        self.register(AgentDefinition(
            agent_id="data_normalization",
            name="DataNormalizationAgent",
            display_name="Data Normalization Agent",
            description="Normalizes and cleans data from various sources",
            category=AgentCategory.DATA,
            capabilities=[AgentCapability.READ, AgentCapability.WRITE],
            module_path="mycosoft_mas.agents.clusters.data_collection.data_normalization_agent",
            class_name="DataNormalizationAgent",
            keywords=["normalization", "clean", "data", "transform"],
            voice_triggers=["normalize data", "clean data"]
        ))
        
        self.register(AgentDefinition(
            agent_id="environmental_data",
            name="EnvironmentalDataAgent",
            display_name="Environmental Data Agent",
            description="Collects and processes environmental sensor data",
            category=AgentCategory.DATA,
            capabilities=[AgentCapability.READ],
            module_path="mycosoft_mas.agents.clusters.data_collection.environmental_data_agent",
            class_name="EnvironmentalDataAgent",
            keywords=["environment", "temperature", "humidity", "sensors"],
            voice_triggers=["environmental data", "temperature", "humidity"]
        ))
        
        self.register(AgentDefinition(
            agent_id="image_processing",
            name="ImageProcessingAgent",
            display_name="Image Processing Agent",
            description="Processes and analyzes images",
            category=AgentCategory.DATA,
            capabilities=[AgentCapability.READ, AgentCapability.ANALYZE],
            module_path="mycosoft_mas.agents.clusters.data_collection.image_processing_agent",
            class_name="ImageProcessingAgent",
            keywords=["image", "photo", "processing", "analysis", "vision"],
            voice_triggers=["image processing", "analyze image", "photo analysis"]
        ))
        
        # ========== SIMULATION CLUSTER ==========
        self.register(AgentDefinition(
            agent_id="growth_simulator",
            name="GrowthSimulatorAgent",
            display_name="Growth Simulator Agent",
            description="Simulates fungal growth patterns",
            category=AgentCategory.SIMULATION,
            capabilities=[AgentCapability.EXECUTE, AgentCapability.ANALYZE],
            module_path="mycosoft_mas.agents.clusters.simulation.growth_simulator_agent",
            class_name="GrowthSimulatorAgent",
            keywords=["simulation", "growth", "model", "predict"],
            voice_triggers=["growth simulation", "simulate growth"]
        ))
        
        self.register(AgentDefinition(
            agent_id="mycelium_simulator",
            name="MyceliumSimulatorAgent",
            display_name="Mycelium Simulator Agent",
            description="Simulates mycelium network behavior",
            category=AgentCategory.SIMULATION,
            capabilities=[AgentCapability.EXECUTE, AgentCapability.ANALYZE],
            module_path="mycosoft_mas.agents.clusters.simulation.mycelium_simulator_agent",
            class_name="MyceliumSimulatorAgent",
            keywords=["mycelium", "network", "simulation"],
            voice_triggers=["mycelium simulation", "network simulation"]
        ))
        
        self.register(AgentDefinition(
            agent_id="compound_simulator",
            name="CompoundSimulatorAgent",
            display_name="Compound Simulator Agent",
            description="Simulates compound synthesis and reactions",
            category=AgentCategory.SIMULATION,
            capabilities=[AgentCapability.EXECUTE, AgentCapability.ANALYZE],
            module_path="mycosoft_mas.agents.clusters.simulation.compound_simulator_agent",
            class_name="CompoundSimulatorAgent",
            keywords=["compound", "chemistry", "synthesis", "reaction"],
            voice_triggers=["compound simulation", "chemistry simulation"]
        ))
        
        self.register(AgentDefinition(
            agent_id="petri_dish_simulator",
            name="PetriDishSimulatorAgent",
            display_name="Petri Dish Simulator Agent",
            description="Simulates petri dish cultures and experiments",
            category=AgentCategory.SIMULATION,
            capabilities=[AgentCapability.EXECUTE, AgentCapability.ANALYZE],
            module_path="mycosoft_mas.agents.clusters.simulation.petri_dish_simulator_agent",
            class_name="PetriDishSimulatorAgent",
            keywords=["petri", "culture", "experiment"],
            voice_triggers=["petri dish", "culture simulation"]
        ))
        
        # ========== KNOWLEDGE MANAGEMENT CLUSTER ==========
        self.register(AgentDefinition(
            agent_id="species_database",
            name="SpeciesDatabaseAgent",
            display_name="Species Database Agent",
            description="Manages fungal species database and taxonomy",
            category=AgentCategory.MYCOLOGY,
            capabilities=[AgentCapability.READ, AgentCapability.WRITE],
            module_path="mycosoft_mas.agents.clusters.knowledge_management.species_database_agent",
            class_name="SpeciesDatabaseAgent",
            keywords=["species", "database", "taxonomy", "classification"],
            voice_triggers=["species database", "taxonomy", "species lookup"]
        ))
        
        self.register(AgentDefinition(
            agent_id="dna_analysis",
            name="DNAAnalysisAgent",
            display_name="DNA Analysis Agent",
            description="Analyzes DNA sequences and genetic data",
            category=AgentCategory.RESEARCH,
            capabilities=[AgentCapability.READ, AgentCapability.ANALYZE],
            module_path="mycosoft_mas.agents.clusters.knowledge_management.dna_analysis_agent",
            class_name="DNAAnalysisAgent",
            keywords=["dna", "genetic", "sequence", "genome"],
            voice_triggers=["dna analysis", "genetic analysis", "sequence"]
        ))
        
        # ========== PATTERN RECOGNITION CLUSTER ==========
        self.register(AgentDefinition(
            agent_id="mycelium_pattern",
            name="MyceliumPatternAgent",
            display_name="Mycelium Pattern Agent",
            description="Recognizes patterns in mycelium growth",
            category=AgentCategory.DATA,
            capabilities=[AgentCapability.READ, AgentCapability.ANALYZE],
            module_path="mycosoft_mas.agents.clusters.pattern_recognition.mycelium_pattern_agent",
            class_name="MyceliumPatternAgent",
            keywords=["pattern", "mycelium", "recognition"],
            voice_triggers=["mycelium pattern", "pattern recognition"]
        ))
        
        self.register(AgentDefinition(
            agent_id="environmental_pattern",
            name="EnvironmentalPatternAgent",
            display_name="Environmental Pattern Agent",
            description="Recognizes environmental patterns and trends",
            category=AgentCategory.DATA,
            capabilities=[AgentCapability.READ, AgentCapability.ANALYZE],
            module_path="mycosoft_mas.agents.clusters.pattern_recognition.environmental_pattern_agent",
            class_name="EnvironmentalPatternAgent",
            keywords=["pattern", "environment", "trends"],
            voice_triggers=["environmental pattern", "environmental trends"]
        ))
        
        # ========== PROTOCOL MANAGEMENT CLUSTER ==========
        self.register(AgentDefinition(
            agent_id="mycorrhizae_protocol",
            name="MycorrhizaeProtocolAgent",
            display_name="Mycorrhizae Protocol Agent",
            description="Manages mycorrhizae cultivation protocols",
            category=AgentCategory.MYCOLOGY,
            capabilities=[AgentCapability.READ, AgentCapability.WRITE],
            module_path="mycosoft_mas.agents.clusters.protocol_management.mycorrhizae_protocol_agent",
            class_name="MycorrhizaeProtocolAgent",
            keywords=["protocol", "mycorrhizae", "cultivation"],
            voice_triggers=["mycorrhizae protocol", "cultivation protocol"]
        ))
        
        self.register(AgentDefinition(
            agent_id="data_flow_coordinator",
            name="DataFlowCoordinatorAgent",
            display_name="Data Flow Coordinator Agent",
            description="Coordinates data flow between systems",
            category=AgentCategory.INFRASTRUCTURE,
            capabilities=[AgentCapability.MANAGE, AgentCapability.CONTROL],
            module_path="mycosoft_mas.agents.clusters.protocol_management.data_flow_coordinator_agent",
            class_name="DataFlowCoordinatorAgent",
            keywords=["data flow", "coordinator", "pipeline"],
            voice_triggers=["data flow", "pipeline status"]
        ))
        
        # ========== DEVICE MANAGEMENT CLUSTER ==========
        self.register(AgentDefinition(
            agent_id="device_coordinator",
            name="DeviceCoordinatorAgent",
            display_name="Device Coordinator Agent",
            description="Coordinates multiple hardware devices",
            category=AgentCategory.INFRASTRUCTURE,
            capabilities=[AgentCapability.MANAGE, AgentCapability.CONTROL],
            module_path="mycosoft_mas.agents.clusters.device_management.device_coordinator_agent",
            class_name="DeviceCoordinatorAgent",
            keywords=["device", "coordinator", "hardware"],
            voice_triggers=["device coordinator", "hardware status"]
        ))
        
        # ========== SYSTEM MANAGEMENT CLUSTER ==========
        self.register(AgentDefinition(
            agent_id="agent_evolution",
            name="AgentEvolutionAgent",
            display_name="Agent Evolution Agent",
            description="Manages agent evolution and upgrades",
            category=AgentCategory.INFRASTRUCTURE,
            capabilities=[AgentCapability.MANAGE, AgentCapability.EXECUTE],
            module_path="mycosoft_mas.agents.clusters.system_management.agent_evolution_agent",
            class_name="AgentEvolutionAgent",
            keywords=["evolution", "upgrade", "agent", "improve"],
            voice_triggers=["agent evolution", "upgrade agent"],
            requires_confirmation=True
        ))
        
        self.register(AgentDefinition(
            agent_id="immune_system",
            name="ImmuneSystemAgent",
            display_name="Immune System Agent",
            description="Monitors and protects system health",
            category=AgentCategory.SECURITY,
            capabilities=[AgentCapability.READ, AgentCapability.ANALYZE, AgentCapability.EXECUTE],
            module_path="mycosoft_mas.agents.clusters.system_management.immune_system_agent",
            class_name="ImmuneSystemAgent",
            keywords=["security", "immune", "health", "protection"],
            voice_triggers=["system health", "security status"]
        ))
        
        # ========== USER INTERFACE CLUSTER ==========
        self.register(AgentDefinition(
            agent_id="visualization",
            name="VisualizationAgent",
            display_name="Visualization Agent",
            description="Creates data visualizations and charts",
            category=AgentCategory.CORE,
            capabilities=[AgentCapability.READ, AgentCapability.EXECUTE],
            module_path="mycosoft_mas.agents.clusters.user_interface.visualization_agent",
            class_name="VisualizationAgent",
            keywords=["visualization", "chart", "graph", "display"],
            voice_triggers=["visualization", "chart", "graph"]
        ))
        
        # ========== SEARCH & DISCOVERY CLUSTER ==========
        self.register(AgentDefinition(
            agent_id="search",
            name="SearchAgent",
            display_name="Search Agent",
            description="Searches across all data sources",
            category=AgentCategory.DATA,
            capabilities=[AgentCapability.READ],
            module_path="mycosoft_mas.agents.clusters.search_discovery.search_agent",
            class_name="SearchAgent",
            keywords=["search", "find", "lookup", "query"],
            voice_triggers=["search", "find", "lookup"]
        ))
        
        # ========== ANALYTICS CLUSTER ==========
        self.register(AgentDefinition(
            agent_id="data_analysis",
            name="DataAnalysisAgent",
            display_name="Data Analysis Agent",
            description="Performs advanced data analysis",
            category=AgentCategory.DATA,
            capabilities=[AgentCapability.READ, AgentCapability.ANALYZE],
            module_path="mycosoft_mas.agents.clusters.analytics_insights.data_analysis_agent",
            class_name="DataAnalysisAgent",
            keywords=["analysis", "data", "statistics", "insights"],
            voice_triggers=["data analysis", "analyze data", "statistics"]
        ))
        
        logger.info(f"Loaded {len(self._agents)} agent definitions into registry")
    
    def register(self, agent_def: AgentDefinition) -> None:
        """Register an agent definition."""
        self._agents[agent_def.agent_id] = agent_def
        
    def get(self, agent_id: str) -> Optional[AgentDefinition]:
        """Get an agent definition by ID."""
        return self._agents.get(agent_id)
    
    def get_by_name(self, name: str) -> Optional[AgentDefinition]:
        """Get an agent definition by class name."""
        for agent in self._agents.values():
            if agent.name == name or agent.display_name == name:
                return agent
        return None
    
    def list_all(self) -> List[AgentDefinition]:
        """List all registered agents."""
        return list(self._agents.values())
    
    def list_by_category(self, category: AgentCategory) -> List[AgentDefinition]:
        """List agents by category."""
        return [a for a in self._agents.values() if a.category == category]
    
    def list_active(self) -> List[AgentDefinition]:
        """List only active agents."""
        return [a for a in self._agents.values() if a.is_active]
    
    def find_by_keyword(self, keyword: str) -> List[AgentDefinition]:
        """Find agents matching a keyword."""
        keyword = keyword.lower()
        return [
            a for a in self._agents.values()
            if keyword in a.name.lower()
            or keyword in a.display_name.lower()
            or keyword in a.description.lower()
            or any(keyword in kw.lower() for kw in a.keywords)
        ]
    
    def find_by_voice_trigger(self, phrase: str) -> List[AgentDefinition]:
        """Find agents matching a voice trigger phrase."""
        phrase = phrase.lower()
        matches = []
        for agent in self._agents.values():
            for trigger in agent.voice_triggers:
                if trigger.lower() in phrase or phrase in trigger.lower():
                    matches.append(agent)
                    break
        return matches
    
    def mark_active(self, agent_id: str, active: bool = True) -> None:
        """Mark an agent as active/inactive."""
        if agent_id in self._agents:
            self._agents[agent_id].is_active = active
    
    def to_dict(self) -> Dict[str, Any]:
        """Export registry as dictionary (for API/n8n)."""
        return {
            "agents": [
                {
                    "agent_id": a.agent_id,
                    "name": a.name,
                    "display_name": a.display_name,
                    "description": a.description,
                    "category": a.category.value,
                    "capabilities": [c.value for c in a.capabilities],
                    "keywords": a.keywords,
                    "voice_triggers": a.voice_triggers,
                    "requires_confirmation": a.requires_confirmation,
                    "is_active": a.is_active,
                }
                for a in self._agents.values()
            ],
            "categories": [c.value for c in AgentCategory],
            "capabilities": [c.value for c in AgentCapability],
            "total_agents": len(self._agents),
            "active_agents": len([a for a in self._agents.values() if a.is_active]),
        }
    
    def get_voice_routing_prompt(self) -> str:
        """Generate a prompt snippet for voice routing."""
        lines = ["Available agents for voice routing:"]
        for agent in sorted(self._agents.values(), key=lambda a: a.category.value):
            triggers = ", ".join(agent.voice_triggers[:3]) if agent.voice_triggers else "none"
            confirm = " [CONFIRMATION REQUIRED]" if agent.requires_confirmation else ""
            lines.append(f"- {agent.display_name} ({agent.category.value}): triggers=[{triggers}]{confirm}")
        return "\n".join(lines)


# Singleton instance
_registry: Optional[AgentRegistry] = None


def get_agent_registry() -> AgentRegistry:
    """Get the global agent registry singleton."""
    global _registry
    if _registry is None:
        _registry = AgentRegistry()
    return _registry
















