"""
MAS v2 Gap Detector

Detects missing agents and triggers automatic creation.
"""

import asyncio
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

from mycosoft_mas.runtime import (
    AgentConfig,
    AgentCategory,
    AgentStatus,
)


logger = logging.getLogger("GapDetector")


@dataclass
class AgentGap:
    """Represents a detected gap in agent coverage"""
    gap_id: str
    gap_type: str  # category, route, integration, device
    category: Optional[AgentCategory]
    description: str
    severity: str  # critical, high, medium, low
    suggested_agent: Dict[str, Any]
    auto_create: bool
    detected_at: datetime


class GapDetector:
    """
    Detects gaps in agent coverage and suggests/creates agents.
    
    Gap Types:
    - Category: Missing agents in required categories
    - Route: API routes without monitoring agents
    - Integration: External services without agents
    - Device: MycoBrain devices without agents
    """
    
    # Required agents by category
    REQUIRED_AGENTS = {
        AgentCategory.CORE: [
            {"agent_id": "myca-core", "agent_type": "orchestrator", "description": "Central orchestrator"},
            {"agent_id": "task-router", "agent_type": "router", "description": "Task routing"},
            {"agent_id": "event-processor", "agent_type": "processor", "description": "Event processing"},
        ],
        AgentCategory.CORPORATE: [
            {"agent_id": "ceo-agent", "agent_type": "executive", "description": "Strategic decisions"},
            {"agent_id": "cfo-agent", "agent_type": "financial", "description": "Financial oversight"},
            {"agent_id": "cto-agent", "agent_type": "technical", "description": "Technology decisions"},
        ],
        AgentCategory.INFRASTRUCTURE: [
            {"agent_id": "proxmox-agent", "agent_type": "vm-manager", "description": "VM management"},
            {"agent_id": "docker-agent", "agent_type": "container-manager", "description": "Container orchestration"},
            {"agent_id": "network-agent", "agent_type": "network-manager", "description": "Network management"},
            {"agent_id": "storage-agent", "agent_type": "storage-manager", "description": "Storage management"},
            {"agent_id": "monitoring-agent", "agent_type": "monitor", "description": "System monitoring"},
        ],
        AgentCategory.SECURITY: [
            {"agent_id": "soc-agent", "agent_type": "security", "description": "Security operations"},
            {"agent_id": "audit-agent", "agent_type": "audit", "description": "Audit logging"},
        ],
        AgentCategory.DEVICE: [
            {"agent_id": "mycobrain-coordinator", "agent_type": "device-coordinator", "description": "MycoBrain fleet management"},
        ],
        AgentCategory.INTEGRATION: [
            {"agent_id": "n8n-agent", "agent_type": "workflow", "description": "n8n workflow integration"},
            {"agent_id": "zapier-agent", "agent_type": "integration", "description": "Zapier integration"},
            {"agent_id": "elevenlabs-agent", "agent_type": "voice", "description": "Voice synthesis"},
        ],
        AgentCategory.DATA: [
            {"agent_id": "mindex-agent", "agent_type": "database", "description": "MINDEX database operations"},
            {"agent_id": "etl-agent", "agent_type": "etl", "description": "Data ETL processing"},
            {"agent_id": "search-agent", "agent_type": "search", "description": "Search operations"},
        ],
    }
    
    # Routes that should have monitoring agents
    CRITICAL_ROUTES = [
        "/api/auth",
        "/api/mindex",
        "/api/mycobrain",
        "/api/natureos",
        "/api/ai",
        "/api/search",
    ]
    
    def __init__(self, agent_pool, orchestrator=None):
        self.agent_pool = agent_pool
        self.orchestrator = orchestrator
        self.detected_gaps: List[AgentGap] = []
    
    async def scan_for_gaps(self) -> List[AgentGap]:
        """Scan for all types of gaps"""
        self.detected_gaps = []
        
        await self._scan_category_gaps()
        await self._scan_route_gaps()
        await self._scan_integration_gaps()
        
        logger.info(f"Detected {len(self.detected_gaps)} gaps")
        return self.detected_gaps
    
    async def _scan_category_gaps(self):
        """Scan for missing agents by category"""
        for category, required_agents in self.REQUIRED_AGENTS.items():
            existing = await self.agent_pool.get_agents_by_category(category)
            existing_ids = {a.agent_id for a in existing if a.status in [AgentStatus.ACTIVE, AgentStatus.BUSY]}
            
            for agent_spec in required_agents:
                if agent_spec["agent_id"] not in existing_ids:
                    gap = AgentGap(
                        gap_id=f"category-{agent_spec['agent_id']}",
                        gap_type="category",
                        category=category,
                        description=f"Missing {agent_spec['description']} agent",
                        severity="high" if category in [AgentCategory.CORE, AgentCategory.SECURITY] else "medium",
                        suggested_agent={
                            "agent_id": agent_spec["agent_id"],
                            "agent_type": agent_spec["agent_type"],
                            "category": category.value,
                            "display_name": agent_spec["description"],
                            "description": agent_spec["description"],
                        },
                        auto_create=category in [AgentCategory.CORE, AgentCategory.INFRASTRUCTURE],
                        detected_at=datetime.utcnow(),
                    )
                    self.detected_gaps.append(gap)
    
    async def _scan_route_gaps(self):
        """Scan for API routes without monitoring"""
        # This would check which routes have active agents
        for route in self.CRITICAL_ROUTES:
            agent_id = f"route-{route.replace('/', '-').strip('-')}"
            state = await self.agent_pool.get_agent_state(agent_id)
            
            if not state or state.status not in [AgentStatus.ACTIVE, AgentStatus.BUSY]:
                gap = AgentGap(
                    gap_id=f"route-{agent_id}",
                    gap_type="route",
                    category=AgentCategory.DATA,
                    description=f"No monitoring agent for route {route}",
                    severity="medium",
                    suggested_agent={
                        "agent_id": agent_id,
                        "agent_type": "route-monitor",
                        "category": "data",
                        "display_name": f"Route Monitor: {route}",
                        "description": f"Monitors API route {route}",
                    },
                    auto_create=True,
                    detected_at=datetime.utcnow(),
                )
                self.detected_gaps.append(gap)
    
    async def _scan_integration_gaps(self):
        """Scan for integrations without agents"""
        integrations = [
            {"id": "n8n", "agent_type": "workflow", "critical": True},
            {"id": "zapier", "agent_type": "integration", "critical": False},
            {"id": "elevenlabs", "agent_type": "voice", "critical": True},
            {"id": "openai", "agent_type": "ai-provider", "critical": True},
            {"id": "anthropic", "agent_type": "ai-provider", "critical": True},
        ]
        
        for integration in integrations:
            agent_id = f"{integration['id']}-agent"
            state = await self.agent_pool.get_agent_state(agent_id)
            
            if not state or state.status not in [AgentStatus.ACTIVE, AgentStatus.BUSY]:
                gap = AgentGap(
                    gap_id=f"integration-{agent_id}",
                    gap_type="integration",
                    category=AgentCategory.INTEGRATION,
                    description=f"No agent for {integration['id']} integration",
                    severity="high" if integration["critical"] else "low",
                    suggested_agent={
                        "agent_id": agent_id,
                        "agent_type": integration["agent_type"],
                        "category": "integration",
                        "display_name": f"{integration['id'].capitalize()} Integration Agent",
                        "description": f"Manages {integration['id']} integration",
                    },
                    auto_create=integration["critical"],
                    detected_at=datetime.utcnow(),
                )
                self.detected_gaps.append(gap)
    
    async def auto_fill_gaps(self) -> List[str]:
        """Automatically create agents to fill gaps marked for auto-creation"""
        created = []
        
        for gap in self.detected_gaps:
            if not gap.auto_create:
                continue
            
            try:
                config = AgentConfig(
                    agent_id=gap.suggested_agent["agent_id"],
                    agent_type=gap.suggested_agent["agent_type"],
                    category=AgentCategory(gap.suggested_agent["category"]),
                    display_name=gap.suggested_agent["display_name"],
                    description=gap.suggested_agent["description"],
                )
                
                if self.orchestrator:
                    await self.orchestrator.spawn_agent(config)
                    created.append(config.agent_id)
                    logger.info(f"Auto-created agent: {config.agent_id}")
                    
            except Exception as e:
                logger.error(f"Failed to auto-create agent {gap.suggested_agent['agent_id']}: {e}")
        
        return created
    
    def get_gap_report(self) -> Dict[str, Any]:
        """Generate a gap report"""
        by_type = {}
        by_severity = {}
        
        for gap in self.detected_gaps:
            by_type[gap.gap_type] = by_type.get(gap.gap_type, 0) + 1
            by_severity[gap.severity] = by_severity.get(gap.severity, 0) + 1
        
        return {
            "total_gaps": len(self.detected_gaps),
            "by_type": by_type,
            "by_severity": by_severity,
            "auto_fillable": len([g for g in self.detected_gaps if g.auto_create]),
            "gaps": [
                {
                    "gap_id": g.gap_id,
                    "type": g.gap_type,
                    "severity": g.severity,
                    "description": g.description,
                    "auto_create": g.auto_create,
                }
                for g in self.detected_gaps
            ]
        }
