"""
Mycosoft Multi-Agent System (MAS) - Agent Package

This package contains all agent implementations and related components for the Mycosoft MAS.
"""

from .base_agent import BaseAgent
import importlib

_lazy_modules = {
    'MycologyBioAgent': '.mycology_bio_agent',
    'MycologyKnowledgeAgent': '.mycology_knowledge_agent',
    'IPTokenizationAgent': '.ip_tokenization_agent',
    'MycoDAOAgent': '.myco_dao_agent',
    'TokenEconomicsAgent': '.token_economics_agent',
    'FinanceAdminAgent': '.finance_admin_agent',
    'ProjectManagementAgent': '.project_management_agent',
    'MarketingAgent': '.marketing_agent',
    'ExperimentAgent': '.experiment_agent',
    'IPAgent': '.ip_agent',
    'SecretaryAgent': '.secretary_agent',
    'DashboardAgent': '.dashboard_agent',
    'OpportunityScout': '.opportunity_scout',
    'CorporateOperationsAgent': '.corporate.corporate_operations_agent',
    'BoardOperationsAgent': '.corporate.board_operations_agent',
    'LegalComplianceAgent': '.corporate.legal_compliance_agent',
    'FinancialAgent': '.financial.financial_agent',
    'CameraIntegration': '.integrations.camera_integration',
    'SpeechIntegration': '.integrations.speech_integration',
}

# Initialize __all__ before dynamic stubs to avoid NameError
__all__: list[str] = [
    'BaseAgent',
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
]


def __getattr__(name: str):
    """Lazily import agent modules when accessed."""
    if name in _lazy_modules:
        module = importlib.import_module(_lazy_modules[name], __name__)
        obj = getattr(module, name)
        globals()[name] = obj
        return obj
    raise AttributeError(f"module {__name__} has no attribute {name}")

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