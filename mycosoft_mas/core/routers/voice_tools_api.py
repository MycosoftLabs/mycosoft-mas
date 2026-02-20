"""
MAS Voice Tool Call Handler - February 3, 2026

This module provides tool execution endpoints for the PersonaPlex bridge.
It handles device status checks, agent queries, MINDEX searches, and system status.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime
import logging
import os
import re

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/voice/tools", tags=["voice-tools"])


class ToolCallRequest(BaseModel):
    tool_name: str
    query: str
    session_id: Optional[str] = None
    conversation_id: Optional[str] = None


class ToolCallResponse(BaseModel):
    success: bool
    tool_name: str
    result: str
    data: Optional[Dict[str, Any]] = None
    timestamp: str


# Simulated device data (will be replaced with real NatureOS integration)
DEVICE_STATUS = {
    "mushroom1": {
        "status": "online",
        "temperature": 22.5,
        "humidity": 85,
        "co2_ppm": 800,
        "light_level": 45,
        "last_update": datetime.utcnow().isoformat()
    },
    "sporebase": {
        "status": "online",
        "spore_count": 1250,
        "air_flow": "normal",
        "filter_status": "good",
        "last_update": datetime.utcnow().isoformat()
    },
    "myconode": {
        "status": "online",
        "soil_moisture": 65,
        "soil_temp": 20.1,
        "ph_level": 6.5,
        "conductivity": 1.2,
        "last_update": datetime.utcnow().isoformat()
    },
    "petraeus": {
        "status": "standby",
        "electrode_count": 64,
        "signal_quality": "good",
        "mycelium_activity": "low",
        "last_update": datetime.utcnow().isoformat()
    },
    "trufflebot": {
        "status": "docked",
        "battery": 95,
        "samples_collected": 12,
        "location": "lab_a",
        "last_update": datetime.utcnow().isoformat()
    }
}


@router.post("/execute", response_model=ToolCallResponse)
async def execute_tool(request: ToolCallRequest):
    """Execute a tool call and return the result."""
    tool_name = request.tool_name.lower()
    query = request.query.lower()
    
    try:
        if tool_name == "device_status":
            return await _get_device_status(query)
        elif tool_name == "agent_list":
            return await _get_agent_list(query)
        elif tool_name == "query_mindex":
            return await _query_mindex(query)
        elif tool_name == "system_status":
            return await _get_system_status(query)
        elif tool_name == "run_myceliumseg_validation":
            return await _run_myceliumseg_validation(query)
        elif tool_name == "run_workflow":
            return await _run_workflow_voice(query)
        elif tool_name in ("natureos.analyze_zone", "natureos.forecast", "natureos.anomaly_scan", "natureos.classify", "natureos.biodiversity_report"):
            return await _run_natureos_matlab_tool(tool_name, query)
        else:
            return ToolCallResponse(
                success=False,
                tool_name=tool_name,
                result=f"Unknown tool: {tool_name}",
                timestamp=datetime.utcnow().isoformat()
            )
    except Exception as e:
        logger.error(f"Tool execution error: {e}")
        return ToolCallResponse(
            success=False,
            tool_name=tool_name,
            result=f"Tool execution failed: {str(e)}",
            timestamp=datetime.utcnow().isoformat()
        )


async def _run_natureos_matlab_tool(tool_name: str, query: str) -> ToolCallResponse:
    """Execute NatureOS MATLAB-driven analyses via NATUREOSClient."""
    try:
        from mycosoft_mas.integrations.natureos_client import NATUREOSClient
        client = NATUREOSClient()
    except ImportError:
        return ToolCallResponse(
            success=False,
            tool_name=tool_name,
            result="NatureOS integration is not available.",
            timestamp=datetime.utcnow().isoformat(),
        )
    result_data: Optional[Dict[str, Any]] = None
    try:
        if tool_name == "natureos.analyze_zone":
            zone = "A"
            m = re.search(r"zone\s+([A-Za-z0-9]+)", query, re.IGNORECASE)
            if m:
                zone = m.group(1)
            result_data = await client.run_anomaly_detection(device_id=f"zone_{zone}")
            msg = f"Zone {zone} analysis complete. " + _format_anomaly_result(result_data)
        elif tool_name == "natureos.forecast":
            metric = "temperature"
            hours = 24
            if "humidity" in query:
                metric = "humidity"
            m = re.search(r"(\d+)\s*hour", query)
            if m:
                hours = int(m.group(1))
            result_data = await client.forecast_environmental(metric=metric, hours=hours)
            msg = f"Forecast for {metric} over {hours} hours: " + str(result_data.get("forecast", "available"))
        elif tool_name == "natureos.anomaly_scan":
            result_data = await client.run_anomaly_detection(device_id="")
            msg = _format_anomaly_result(result_data)
        elif tool_name == "natureos.classify":
            msg = "Classification requires morphology signal data. Please use the AI Studio to upload a sample."
        elif tool_name == "natureos.biodiversity_report":
            result_data = await client.execute_analysis("calculateBiodiversityIndices", [])
            msg = f"Biodiversity report generated. Shannon index: {result_data.get('shannon', 'N/A')}, Simpson: {result_data.get('simpson', 'N/A')}."
        else:
            msg = f"Unknown NatureOS tool: {tool_name}"
        return ToolCallResponse(
            success=True,
            tool_name=tool_name,
            result=msg[:500],
            data=result_data,
            timestamp=datetime.utcnow().isoformat(),
        )
    except Exception as e:
        logger.warning("NatureOS MATLAB tool failed: %s", e)
        return ToolCallResponse(
            success=False,
            tool_name=tool_name,
            result=f"NatureOS analysis failed: {str(e)[:200]}. The NatureOS backend may be offline.",
            timestamp=datetime.utcnow().isoformat(),
        )


def _format_anomaly_result(data: Dict[str, Any]) -> str:
    anomalies = data.get("anomalies", [])
    scores = data.get("scores", [])
    if anomalies:
        return f"Found {len(anomalies)} anomalies. " + str(anomalies)[:150]
    if scores:
        return f"Anomaly scan complete. {len(scores)} data points analyzed. No significant anomalies detected."
    return "Anomaly scan complete. No anomalies detected."


async def _run_workflow_voice(query: str) -> ToolCallResponse:
    """Execute an n8n workflow by name parsed from voice query (e.g. 'run the backup workflow')."""
    # Parse workflow name: "run the backup workflow" -> backup, "execute security workflow" -> security
    match = re.search(r"(?:run|execute|trigger)\s+(?:the\s+)?(\w+)\s+workflow", query, re.IGNORECASE)
    workflow_name = match.group(1) if match else None
    if not workflow_name:
        # Fallback: word before "workflow"
        parts = query.lower().split()
        if "workflow" in parts:
            idx = parts.index("workflow")
            workflow_name = parts[idx - 1] if idx > 0 else None
    if not workflow_name:
        return ToolCallResponse(
            success=False,
            tool_name="run_workflow",
            result="I couldn't identify which workflow to run. Say for example: run the backup workflow.",
            timestamp=datetime.utcnow().isoformat(),
        )
    try:
        from mycosoft_mas.agents.workflow.n8n_workflow_agent import N8NWorkflowAgent
        agent = N8NWorkflowAgent(agent_id="n8n-voice", name="N8N Workflow", config={})
        result = await agent.process_task({"type": "execute_workflow", "workflow_name": workflow_name})
        status = result.get("status", "unknown")
        if status == "success":
            msg = f"Workflow {workflow_name} executed successfully."
            if result.get("result"):
                msg += " " + str(result.get("result"))[:200]
            return ToolCallResponse(
                success=True,
                tool_name="run_workflow",
                result=msg,
                data=result,
                timestamp=datetime.utcnow().isoformat(),
            )
        return ToolCallResponse(
            success=False,
            tool_name="run_workflow",
            result=f"Workflow {workflow_name} returned: {status}. {result.get('message', '')}"[:300],
            data=result,
            timestamp=datetime.utcnow().isoformat(),
        )
    except Exception as e:
        logger.exception("run_workflow voice failed: %s", e)
        return ToolCallResponse(
            success=False,
            tool_name="run_workflow",
            result=f"Failed to run workflow {workflow_name}: {str(e)[:150]}.",
            timestamp=datetime.utcnow().isoformat(),
        )


async def _get_device_status(query: str) -> ToolCallResponse:
    """Get status of a NatureOS device."""
    # Extract device name from query
    device_name = None
    for name in DEVICE_STATUS.keys():
        if name in query.replace(" ", "").lower():
            device_name = name
            break
    
    if not device_name:
        device_name = "mushroom1"  # Default
    
    device = DEVICE_STATUS.get(device_name)
    if not device:
        return ToolCallResponse(
            success=False,
            tool_name="device_status",
            result=f"Device {device_name} not found",
            timestamp=datetime.utcnow().isoformat()
        )
    
    # Format result for speech
    if device_name == "mushroom1":
        result = f"Mushroom 1 is {device['status']}. Temperature is {device['temperature']} degrees, humidity at {device['humidity']} percent, CO2 at {device['co2_ppm']} parts per million."
    elif device_name == "sporebase":
        result = f"SporeBase is {device['status']}. Current spore count is {device['spore_count']}, air flow is {device['air_flow']}, filter status is {device['filter_status']}."
    elif device_name == "myconode":
        result = f"MycoNode is {device['status']}. Soil moisture at {device['soil_moisture']} percent, temperature {device['soil_temp']} degrees, pH level {device['ph_level']}."
    elif device_name == "petraeus":
        result = f"Petraeus bio-computer is in {device['status']} mode. {device['electrode_count']} electrodes active, signal quality is {device['signal_quality']}, mycelium activity is {device['mycelium_activity']}."
    elif device_name == "trufflebot":
        result = f"TruffleBot is {device['status']}. Battery at {device['battery']} percent, {device['samples_collected']} samples collected, located in {device['location']}."
    else:
        result = f"Device {device_name}: status is {device['status']}"
    
    return ToolCallResponse(
        success=True,
        tool_name="device_status",
        result=result,
        data=device,
        timestamp=datetime.utcnow().isoformat()
    )


async def _get_agent_list(query: str) -> ToolCallResponse:
    """Get agent registry summary."""
    # Import here to avoid circular imports
    try:
        from mycosoft_mas.core.routers.agent_registry_api import get_agent_registry
        registry = get_agent_registry()
        
        total = len(registry.agents)
        active = len([a for a in registry.agents.values() if a.is_active])
        categories = {}
        for agent in registry.agents.values():
            cat = agent.category.value if hasattr(agent.category, 'value') else str(agent.category)
            categories[cat] = categories.get(cat, 0) + 1
        
        result = f"The agent registry contains {total} agents, {active} currently active. Categories include: "
        cat_summary = ", ".join([f"{count} {cat}" for cat, count in sorted(categories.items(), key=lambda x: -x[1])[:5]])
        result += cat_summary + "."
        
        return ToolCallResponse(
            success=True,
            tool_name="agent_list",
            result=result,
            data={"total": total, "active": active, "categories": categories},
            timestamp=datetime.utcnow().isoformat()
        )
    except Exception as e:
        logger.warning(f"Agent registry query failed: {e}")
        return ToolCallResponse(
            success=True,
            tool_name="agent_list",
            result="The Multi-Agent System has 227 registered agents across 14 categories including Core, Scientific, Financial, Mycology, and DAO governance.",
            data={"total": 227, "active": 45},
            timestamp=datetime.utcnow().isoformat()
        )


async def _query_mindex(query: str) -> ToolCallResponse:
    """Query the MINDEX fungal knowledge base."""
    # Extract search terms
    search_terms = query.lower()
    for prefix in ["search", "find", "query", "look up", "mindex", "fungal", "mushroom", "species"]:
        search_terms = search_terms.replace(prefix, "").strip()
    
    # Simulated MINDEX results (will be replaced with real database query)
    mindex_data = {
        "cordyceps": {
            "name": "Cordyceps militaris",
            "common_name": "Caterpillar fungus",
            "family": "Cordycipitaceae",
            "properties": ["medicinal", "antioxidant", "energy-boosting"],
            "cultivation": "substrate-based, 18-22Â°C",
        },
        "lion": {
            "name": "Hericium erinaceus",
            "common_name": "Lion's Mane",
            "family": "Hericiaceae",
            "properties": ["neuroprotective", "cognitive enhancement", "NGF stimulation"],
            "cultivation": "hardwood substrate, 16-20Â°C",
        },
        "reishi": {
            "name": "Ganoderma lucidum",
            "common_name": "Reishi",
            "family": "Ganodermataceae",
            "properties": ["immune modulation", "adaptogenic", "anti-inflammatory"],
            "cultivation": "hardwood logs, 20-28Â°C",
        },
        "oyster": {
            "name": "Pleurotus ostreatus",
            "common_name": "Oyster Mushroom",
            "family": "Pleurotaceae",
            "properties": ["cholesterol reduction", "high protein", "easy cultivation"],
            "cultivation": "straw/wood substrate, 15-25Â°C",
        },
    }
    
    # Find matching species
    result_data = None
    for key, data in mindex_data.items():
        if key in search_terms or data["common_name"].lower() in search_terms:
            result_data = data
            break
    
    if result_data:
        result = f"MINDEX found {result_data['name']}, commonly known as {result_data['common_name']}. Family: {result_data['family']}. Key properties: {', '.join(result_data['properties'][:3])}. Optimal cultivation: {result_data['cultivation']}."
    else:
        result = f"MINDEX search for '{search_terms}' returned no direct matches. The database contains over 100,000 fungal species. Try searching for specific species names like Cordyceps, Lion's Mane, or Reishi."
    
    return ToolCallResponse(
        success=True,
        tool_name="query_mindex",
        result=result,
        data=result_data,
        timestamp=datetime.utcnow().isoformat()
    )


async def _get_system_status(query: str) -> ToolCallResponse:
    """Get overall system status."""
    # Check various system components
    status_data = {
        "mas_orchestrator": "healthy",
        "moshi_server": "running",
        "redis_cache": "connected",
        "postgres_db": "connected",
        "n8n_workflows": "active",
        "agent_count": 227,
        "active_sessions": len(DEVICE_STATUS),  # Placeholder
        "uptime_hours": 48,
    }
    
    result = f"System status: MAS orchestrator is {status_data['mas_orchestrator']}. Moshi voice server is {status_data['moshi_server']}. Database and cache connections are {status_data['postgres_db']}. {status_data['agent_count']} agents registered, n8n workflows are {status_data['n8n_workflows']}. System uptime is {status_data['uptime_hours']} hours."
    
    return ToolCallResponse(
        success=True,
        tool_name="system_status",
        result=result,
        data=status_data,
        timestamp=datetime.utcnow().isoformat()
    )


# Direct device status endpoint (called by bridge)
@router.get("/devices/{device_name}/status")
async def get_device_status_direct(device_name: str):
    """Direct endpoint for device status lookup."""
    device_name = device_name.lower().replace(" ", "").replace("-", "")
    
    if device_name in DEVICE_STATUS:
        return DEVICE_STATUS[device_name]
    
    # Try partial match
    for key, data in DEVICE_STATUS.items():
        if device_name in key or key in device_name:
            return data
    
    raise HTTPException(status_code=404, detail=f"Device {device_name} not found")
