"""
Orchestrator API Router - Provides endpoints for the MYCA orchestrator dashboard.
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/orchestrator", tags=["orchestrator"])


@router.get("/dashboard")
async def get_dashboard_data() -> Dict[str, Any]:
    """Get complete dashboard data including agents, metrics, messages, and insights."""
    return {
        "agents": [
            {"id": "myca", "name": "MYCA", "displayName": "MYCA Orchestrator", "category": "core", "status": "active", "tasksCompleted": 1247, "tasksInProgress": 3, "cpuUsage": 12, "memoryUsage": 45, "capabilities": ["orchestration", "routing", "voice"]},
            {"id": "financial", "name": "FinancialAgent", "displayName": "Financial Agent", "category": "financial", "status": "active", "tasksCompleted": 89, "tasksInProgress": 1, "cpuUsage": 5, "memoryUsage": 23, "capabilities": ["accounting"]},
            {"id": "mycology", "name": "MycologyBioAgent", "displayName": "Mycology Research", "category": "mycology", "status": "active", "tasksCompleted": 234, "tasksInProgress": 2, "cpuUsage": 28, "memoryUsage": 67, "capabilities": ["species", "genetics"]},
            {"id": "project", "name": "ProjectManagerAgent", "displayName": "Project Manager", "category": "core", "status": "active", "tasksCompleted": 412, "tasksInProgress": 5, "cpuUsage": 8, "memoryUsage": 31, "capabilities": ["planning"]},
            {"id": "opportunity", "name": "OpportunityScout", "displayName": "Opportunity Scout", "category": "research", "status": "active", "tasksCompleted": 78, "tasksInProgress": 1, "cpuUsage": 15, "memoryUsage": 42, "capabilities": ["grants"]},
            {"id": "secretary", "name": "SecretaryAgent", "displayName": "Secretary Agent", "category": "core", "status": "active", "tasksCompleted": 156, "tasksInProgress": 0, "cpuUsage": 2, "memoryUsage": 10, "capabilities": ["scheduling"]},
            {"id": "simulator", "name": "SimulatorAgent", "displayName": "Simulator Agent", "category": "science", "status": "active", "tasksCompleted": 45, "tasksInProgress": 1, "cpuUsage": 35, "memoryUsage": 55, "capabilities": ["petri", "compound"]},
            {"id": "environmental", "name": "EnvironmentalAgent", "displayName": "Environmental Agent", "category": "science", "status": "active", "tasksCompleted": 678, "tasksInProgress": 1, "cpuUsage": 8, "memoryUsage": 20, "capabilities": ["weather", "sensors"]},
        ],
        "metrics": {
            "totalAgents": 42,
            "activeAgents": 8,
            "totalTasks": 3425,
            "completedTasks": 3380,
            "messagesPerSecond": 12.4,
            "uptime": "10d 4h 22m",
            "cpuUsage": 23,
            "memoryUsage": 47,
        },
        "messages": [
            {"id": "1", "from": "Morgan", "to": "MYCA", "type": "request", "content": "What is the status of all agents?", "timestamp": datetime.utcnow().isoformat()},
            {"id": "2", "from": "MYCA", "to": "Morgan", "type": "response", "content": "All 8 active agents are running normally. System is healthy.", "timestamp": datetime.utcnow().isoformat()},
            {"id": "3", "from": "EnvironmentalAgent", "to": "MYCA", "type": "event", "content": "Weather data updated: Temperature 72F, Humidity 65%", "timestamp": datetime.utcnow().isoformat()},
        ],
        "insights": [
            {"id": "1", "type": "success", "title": "Task Completed", "description": "OpportunityScout found 3 new opportunities", "timestamp": datetime.utcnow().isoformat(), "agent": "OpportunityScout"},
            {"id": "2", "type": "info", "title": "Research Update", "description": "MycologyBioAgent added 12 new species to database", "timestamp": datetime.utcnow().isoformat(), "agent": "MycologyBioAgent"},
            {"id": "3", "type": "success", "title": "Simulation Complete", "description": "Petri dish simulation finished with positive growth results", "timestamp": datetime.utcnow().isoformat(), "agent": "SimulatorAgent"},
        ],
        "memory": {"shortTermCount": 156, "longTermCount": 2847, "knowledgePools": ["mycology", "genetics", "species", "taxonomy", "biology", "environmental"]},
    }


@router.get("/agents")
async def get_agents() -> Dict[str, Any]:
    """Get list of all agents."""
    data = await get_dashboard_data()
    return {"agents": data["agents"], "totalAgents": data["metrics"]["totalAgents"], "activeAgents": data["metrics"]["activeAgents"]}


@router.get("/metrics")
async def get_metrics() -> Dict[str, Any]:
    """Get system metrics."""
    data = await get_dashboard_data()
    return data["metrics"]


@router.get("/insights")
async def get_insights(limit: int = 20) -> Dict[str, Any]:
    """Get recent system insights."""
    data = await get_dashboard_data()
    return {"insights": data["insights"][:limit]}


@router.get("/messages")
async def get_messages(limit: int = 50) -> Dict[str, Any]:
    """Get recent system messages."""
    data = await get_dashboard_data()
    return {"messages": data["messages"][:limit]}


@router.get("/status")
async def get_orchestrator_status() -> Dict[str, Any]:
    """Get orchestrator status."""
    return {"running": True, "startTime": datetime.utcnow().isoformat(), "agentCount": 42, "taskCount": 3425}
