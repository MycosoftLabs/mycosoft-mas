from typing import Dict, Any
import os

# Base configuration for all agents
BASE_CONFIG = {
    "timeout": int(os.getenv("AGENT_TIMEOUT", "30")),
    "retry_count": int(os.getenv("MAX_RETRIES", "3")),
    "retry_delay": int(os.getenv("RETRY_INTERVAL", "300")),
    "health_check_interval": int(os.getenv("HEALTH_CHECK_INTERVAL", "60")),
}

# Agent configurations
AGENTS: Dict[str, Dict[str, Any]] = {
    # Protocol Management Cluster
    "protocol_management": {
        "name": "Protocol Management Agent",
        "endpoint": os.getenv("PROTOCOL_MANAGEMENT_ENDPOINT", "http://protocol-management:8000"),
        "type": "protocol",
        **BASE_CONFIG
    },
    "data_flow": {
        "name": "Data Flow Coordinator Agent",
        "endpoint": os.getenv("DATA_FLOW_ENDPOINT", "http://data-flow:8000"),
        "type": "data",
        **BASE_CONFIG
    },
    
    # Research & Development Cluster
    "lab_rd": {
        "name": "Lab R&D Agent",
        "endpoint": os.getenv("LAB_RD_ENDPOINT", "http://lab-rd:8000"),
        "type": "research",
        **BASE_CONFIG
    },
    "software_dev": {
        "name": "Software Dev Agent",
        "endpoint": os.getenv("SOFTWARE_DEV_ENDPOINT", "http://software-dev:8000"),
        "type": "development",
        **BASE_CONFIG
    },
    
    # Financial Cluster
    "financial": {
        "name": "Financial Agent",
        "endpoint": os.getenv("FINANCIAL_ENDPOINT", "http://financial:8000"),
        "type": "financial",
        **BASE_CONFIG
    },
    
    # User Interface Cluster
    "dashboard": {
        "name": "Dashboard Agent",
        "endpoint": os.getenv("DASHBOARD_ENDPOINT", "http://dashboard:8000"),
        "type": "ui",
        **BASE_CONFIG
    },
    
    # Security Cluster
    "immune_system": {
        "name": "Immune System Agent",
        "endpoint": os.getenv("IMMUNE_SYSTEM_ENDPOINT", "http://immune-system:8000"),
        "type": "security",
        **BASE_CONFIG
    },
    
    # Evolution Cluster
    "agent_evolution": {
        "name": "Agent Evolution Agent",
        "endpoint": os.getenv("AGENT_EVOLUTION_ENDPOINT", "http://agent-evolution:8000"),
        "type": "evolution",
        **BASE_CONFIG
    }
}

# Task type to agent mapping
TASK_TYPE_TO_AGENT = {
    "protocol": "protocol_management",
    "data": "data_flow",
    "research": "lab_rd",
    "development": "software_dev",
    "financial": "financial",
    "ui": "dashboard",
    "security": "immune_system",
    "evolution": "agent_evolution"
} 