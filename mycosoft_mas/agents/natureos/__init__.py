"""
NatureOS agents - device registry, environment, data pipeline, edge compute.
Phase 1 AGENT_CATALOG implementation.
"""

from mycosoft_mas.agents.natureos.device_registry_agent import DeviceRegistryAgent
from mycosoft_mas.agents.natureos.environment_agent import EnvironmentAgent
from mycosoft_mas.agents.natureos.data_pipeline_agent import DataPipelineAgent
from mycosoft_mas.agents.natureos.edge_compute_agent import EdgeComputeAgent

__all__ = [
    "DeviceRegistryAgent",
    "EnvironmentAgent",
    "DataPipelineAgent",
    "EdgeComputeAgent",
]
