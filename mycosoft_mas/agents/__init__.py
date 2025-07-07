"""
Mycosoft Multi-Agent System (MAS) - Agent Package

This package contains all agent implementations and related components for the Mycosoft MAS.
"""

from .base_agent import BaseAgent
import os

if not os.environ.get("MAS_LIGHT_IMPORT"):
    from .mycology_bio_agent import MycologyBioAgent
    from .mycology_knowledge_agent import MycologyKnowledgeAgent
    from .ip_tokenization_agent import IPTokenizationAgent
    from .myco_dao_agent import MycoDAOAgent
    from .token_economics_agent import TokenEconomicsAgent
    from .finance_admin_agent import FinanceAdminAgent
    from .project_management_agent import ProjectManagementAgent
    from .marketing_agent import MarketingAgent
    from .experiment_agent import ExperimentAgent
    from .ip_agent import IPAgent
    from .secretary_agent import SecretaryAgent
    from .dashboard_agent import DashboardAgent
    from .opportunity_scout import OpportunityScout

    # Corporate Agents
    from .corporate.corporate_operations_agent import CorporateOperationsAgent
    from .corporate.board_operations_agent import BoardOperationsAgent
    from .corporate.legal_compliance_agent import LegalComplianceAgent

    # Financial Agents
    from .financial.financial_agent import FinancialAgent

    # Integrations
    from .integrations.camera_integration import CameraIntegration
    from .integrations.speech_integration import SpeechIntegration

# Initialize __all__ before dynamic stubs to avoid NameError
__all__: list[str] = ['BaseAgent']
if not os.environ.get("MAS_LIGHT_IMPORT"):
    __all__.extend([
        'MycologyBioAgent',
        'MycologyKnowledgeAgent',
        'IPTokenizationAgent',
        'MycoDAOAgent',
        'TokenEconomicsAgent',
        'FinanceAdminAgent',
        'ProjectManagementAgent',
        'MarketingAgent',
        'ExperimentAgent',
        'IPAgent',
        'SecretaryAgent',
        'DashboardAgent',
        'OpportunityScout',
        'CorporateOperationsAgent',
        'BoardOperationsAgent',
        'LegalComplianceAgent',
        'FinancialAgent',
        'CameraIntegration',
        'SpeechIntegration',
    ])

# Dynamically create stub agent modules/classes for testing compatibility
import sys, types

_missing_stubs = {
    'contract_agent': 'ContractAgent',
    'legal_agent': 'LegalAgent',
    'technical_agent': 'TechnicalAgent',
    'qa_agent': 'QAAgent',
    'verification_agent': 'VerificationAgent',
    'audit_agent': 'AuditAgent',
    'registry_agent': 'RegistryAgent',
    'analytics_agent': 'AnalyticsAgent',
    'risk_agent': 'RiskAgent',
    'compliance_agent': 'ComplianceAgent',
    'operations_agent': 'OperationsAgent',
}

for module_suffix, class_name in _missing_stubs.items():
    full_module_name = f"{__name__}.{module_suffix}"
    if full_module_name in sys.modules:
        # Module already exists (implemented elsewhere)
        continue

    # Create a new module object for import machinery
    module = types.ModuleType(full_module_name)
    # Define a simple subclass of BaseAgent
    def _init(self, agent_id: str, name: str, config: dict):
        BaseAgent.__init__(self, agent_id=agent_id, name=name, config=config)
    StubClass = type(class_name, (BaseAgent,), {"__init__": _init})
    setattr(module, class_name, StubClass)
    # Register the module so import machinery can find it
    sys.modules[full_module_name] = module
    # Also expose class at package level for direct import
    globals()[class_name] = StubClass
    __all__.append(class_name) 