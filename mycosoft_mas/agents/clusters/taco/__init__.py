"""TAC-O Agent Cluster — Tactical Oceanography for NUWC CSO

Five specialized agents for contractor-agnostic maritime integration:
- SignalClassifierAgent: NLM acoustic/magnetic classification
- AnomalyInvestigatorAgent: Baseline deviation monitoring
- OceanPredictorAgent: Environmental condition forecasting
- PolicyComplianceAgent: Real-time NIST 800-171 monitoring
- DataCuratorAgent: Training data lifecycle management
"""

from mycosoft_mas.agents.clusters.taco.signal_classifier_agent import SignalClassifierAgent
from mycosoft_mas.agents.clusters.taco.anomaly_investigator_agent import AnomalyInvestigatorAgent
from mycosoft_mas.agents.clusters.taco.ocean_predictor_agent import OceanPredictorAgent
from mycosoft_mas.agents.clusters.taco.policy_compliance_agent import PolicyComplianceAgent
from mycosoft_mas.agents.clusters.taco.data_curator_agent import DataCuratorAgent

__all__ = [
    "SignalClassifierAgent",
    "AnomalyInvestigatorAgent",
    "OceanPredictorAgent",
    "PolicyComplianceAgent",
    "DataCuratorAgent",
]
