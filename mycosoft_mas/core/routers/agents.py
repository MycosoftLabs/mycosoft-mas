from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any
from datetime import datetime
from ..security import get_current_user
import logging

router = APIRouter(prefix="/agents", tags=["agents"])
logger = logging.getLogger(__name__)

@router.get("/")
async def get_agents(current_user: Dict = Depends(get_current_user)) -> List[Dict[str, Any]]:
    """Get all registered agents from the agent registry."""
    try:
        from mycosoft_mas.registry.agent_registry import AgentRegistry
        registry = AgentRegistry()
        agents = registry.list_agents()
        
        # Convert to dict format for API response
        return [
            {
                "id": str(agent.id),
                "name": agent.name,
                "category": agent.category.value,
                "description": agent.description,
                "status": agent.status.value,
                "capabilities": len(agent.capabilities),
                "version": agent.version,
                "registered_at": agent.registered_at.isoformat(),
                "last_heartbeat": agent.last_heartbeat.isoformat() if agent.last_heartbeat else None
            }
            for agent in agents
        ]
    except Exception as e:
        logger.error(f"Error fetching agents: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching agents: {str(e)}")

@router.get("/{agent_id}")
async def get_agent(agent_id: str, current_user: Dict = Depends(get_current_user)) -> Dict[str, Any]:
    """Get agent by ID from the agent registry."""
    try:
        from mycosoft_mas.registry.agent_registry import AgentRegistry
        registry = AgentRegistry()
        agent = registry.get_agent(agent_id)
        
        if not agent:
            raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")
        
        return {
            "id": str(agent.id),
            "name": agent.name,
            "category": agent.category.value,
            "description": agent.description,
            "module_path": agent.module_path,
            "class_name": agent.class_name,
            "status": agent.status.value,
            "version": agent.version,
            "capabilities": [
                {
                    "name": cap.name,
                    "description": cap.description,
                    "requires_auth": cap.requires_auth,
                    "rate_limited": cap.rate_limited
                }
                for cap in agent.capabilities
            ],
            "dependencies": agent.dependencies,
            "metadata": agent.metadata,
            "registered_at": agent.registered_at.isoformat(),
            "last_heartbeat": agent.last_heartbeat.isoformat() if agent.last_heartbeat else None
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching agent {agent_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching agent: {str(e)}")

@router.post("/{agent_id}/restart")
async def restart_agent(agent_id: str, current_user: Dict = Depends(get_current_user)) -> Dict[str, str]:
    """Restart an agent - triggers agent lifecycle management."""
    try:
        from mycosoft_mas.registry.agent_registry import AgentRegistry
        registry = AgentRegistry()
        agent = registry.get_agent(agent_id)
        
        if not agent:
            raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")
        
        # Update agent status to initializing
        registry.update_agent_status(agent_id, "initializing")
        
        logger.info(f"Restart requested for agent: {agent.name} ({agent_id})")
        
        # Agent lifecycle management requires:
        # 1. Process supervisor to track agent processes
        # 2. Graceful shutdown with state saving
        # 3. Process restart with state restoration
        # 4. Health check verification after restart
        # 5. Registry update during lifecycle changes
        # Current status: Request logged, state updated to initializing
        
        return {
            "status": "accepted",
            "message": f"Agent {agent.name} restart request logged. Full lifecycle management implementation in progress.",
            "agent_id": agent_id,
            "agent_name": agent.name,
            "current_status": agent.status.value,
            "implementation_note": "Agent process supervision system under development. See docs/CODE_AUDIT_FEB13_2026.md for details."
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error restarting agent {agent_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error restarting agent: {str(e)}")

@router.get("/anomalies")
async def get_anomalies(
    limit: int = 50,
    severity: str = None,
    current_user: Dict = Depends(get_current_user)
) -> List[Dict[str, Any]]:
    """
    Get detected anomalies from all anomaly detection agents.
    
    Queries:
    - ImmuneSystemAgent for security threats and vulnerabilities
    - DataAnalysisAgent for data anomalies
    - EnvironmentalPatternAgent for environmental anomalies
    - MyceliumPatternAgent for pattern anomalies
    
    Args:
        limit: Maximum number of anomalies to return (default 50)
        severity: Filter by severity level (critical, high, medium, low)
    
    Returns:
        List of anomaly detection results
    """
    anomalies = []
    
    try:
        # Query agent registry for anomaly detection agents
        from mycosoft_mas.registry.agent_registry import AgentRegistry
        registry = AgentRegistry()
        
        # Get agents that might have anomaly detection capabilities
        all_agents = registry.list_agents()
        anomaly_agents = [
            agent for agent in all_agents 
            if any(cap in ["anomaly_detection", "threat_detection", "security_monitoring", "pattern_analysis"]
                   for cap in agent.capabilities)
        ]
        
        logger.info(f"Found {len(anomaly_agents)} anomaly detection agents")
        
        # For each agent, query their status/metrics for anomalies
        for agent in anomaly_agents:
            try:
                # Get agent metrics which may include anomaly data
                agent_metrics = agent.metadata.get("recent_anomalies", [])
                if isinstance(agent_metrics, list):
                    anomalies.extend(agent_metrics)
            except Exception as e:
                logger.warning(f"Could not fetch anomalies from {agent.name}: {e}")
        
        # Filter by severity if specified
        if severity:
            anomalies = [a for a in anomalies if a.get("severity") == severity.lower()]
        
        # Sort by timestamp (most recent first) and limit
        anomalies.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        anomalies = anomalies[:limit]
        
        logger.info(f"Returning {len(anomalies)} anomalies (limit={limit}, severity={severity})")
        
        return {
            "anomalies": anomalies,
            "count": len(anomalies),
            "total_agents_queried": len(anomaly_agents),
            "timestamp": datetime.utcnow().isoformat(),
            "status": "active",
            "message": f"Queried {len(anomaly_agents)} anomaly detection agents"
        }
        
    except Exception as e:
        logger.error(f"Error fetching anomalies: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching anomalies: {str(e)}") 