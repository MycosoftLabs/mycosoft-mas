"""
MAS Voice Tool Call Handler - February 3, 2026

This module provides tool execution endpoints for the PersonaPlex bridge.
It handles device status checks, agent queries, MINDEX searches, and system status.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import logging
import os
import re

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/voice/tools", tags=["voice-tools"])


def _normalize_text(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower()) if value else ""


def _get_mas_base_url() -> str:
    return os.getenv("MAS_API_URL", "http://localhost:8001").rstrip("/")


def _get_mindex_base_url() -> str:
    return (
        os.getenv("MINDEX_API_URL")
        or os.getenv("MINDEX_API_BASE_URL")
        or "http://192.168.0.189:8000"
    ).rstrip("/")


def _get_n8n_base_url() -> str:
    return os.getenv("N8N_URL", "http://192.168.0.188:5678").rstrip("/")


def _pick_device_match(devices: List[Dict[str, Any]], query: str) -> Optional[Dict[str, Any]]:
    normalized_query = _normalize_text(query)
    if not normalized_query:
        return devices[0] if len(devices) == 1 else None
    for device in devices:
        candidates = [
            device.get("device_id", ""),
            device.get("device_name", ""),
            device.get("device_display_name", ""),
            device.get("device_role", ""),
            device.get("location", ""),
        ]
        for value in candidates:
            normalized_value = _normalize_text(str(value))
            if normalized_value and (normalized_value in normalized_query or normalized_query in normalized_value):
                return device
    return None


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
        elif tool_name in ("petri.monitor", "petri.adjust_env", "petri.contamination_response", "petri.multi_run"):
            return await _run_petri_agent_tool(tool_name, query)
        elif tool_name in (
            "natureos.analyze_zone",
            "natureos.forecast",
            "natureos.anomaly_scan",
            "natureos.classify",
            "natureos.biodiversity_report",
            "natureos.earth_forecast",
            "natureos.simulate_petri",
            "natureos.simulate_mushroom",
            "natureos.simulate_compound",
            "natureos.simulate_genetic_circuit",
            "natureos.simulate_lifecycle",
            "natureos.simulate_physics",
            "natureos.growth_analytics",
            "natureos.retrosynthesis",
            "natureos.alchemy_lab",
            "natureos.sync_twin",
            "natureos.symbiosis_network",
            "natureos.track_spores",
        ):
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


async def _run_petri_agent_tool(tool_name: str, query: str) -> ToolCallResponse:
    """Execute Petri agent control via MAS petri API."""
    import httpx
    base = os.getenv("MAS_API_URL", "http://localhost:8001")
    url = f"{base.rstrip('/')}/api/simulation/petri/agent/control"
    action = tool_name.replace("petri.", "")
    params: Dict[str, Any] = {}
    if action == "monitor":
        pass
    elif action == "adjust_env":
        m = re.search(r"temp(?:erature)?\s*(?:to\s+)?(\d+(?:\.\d+)?)", query, re.I)
        if m:
            params["temperature"] = float(m.group(1))
        m = re.search(r"humidity\s*(?:to\s+)?(\d+(?:\.\d+)?)", query, re.I)
        if m:
            params["humidity"] = float(m.group(1))
        m = re.search(r"ph\s*(?:to\s+)?(\d+(?:\.\d+)?)", query, re.I)
        if m:
            params["ph"] = float(m.group(1))
    elif action == "contamination_response":
        params["strategy"] = "reduce_speed"
        if "isolate" in query.lower():
            params["strategy"] = "isolate"
        elif "ph" in query.lower() or "adjust" in query.lower():
            params["strategy"] = "adjust_ph"
    elif action == "multi_run":
        m = re.search(r"(\d+)\s*iterations?", query, re.I) or re.search(r"batch\s+(\d+)", query, re.I)
        params["iterations"] = int(m.group(1)) if m else 10
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.post(url, json={"action": action, "source": "voice", "params": params})
            r.raise_for_status()
            data = r.json()
        msg = data.get("message", str(data.get("status", "ok")))
        if action == "monitor":
            msg = f"Petri status: {data.get('petridishsim_reachable', False) and 'reachable' or 'offline'}. Sessions: {data.get('sessions_count', 0)}."
        return ToolCallResponse(success=True, tool_name=tool_name, result=msg[:500], data=data, timestamp=datetime.utcnow().isoformat())
    except Exception as e:
        logger.warning("Petri agent tool failed: %s", e)
        return ToolCallResponse(success=False, tool_name=tool_name, result=f"Petri control failed: {str(e)[:200]}", timestamp=datetime.utcnow().isoformat())


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
        elif tool_name == "natureos.earth_forecast":
            hours = 24
            m = re.search(r"(\d+)\s*hour", query)
            if m:
                hours = int(m.group(1))
            payload = {"hours": hours, "query": query}
            result_data = await client.get_earth2_forecast(payload)
            msg = "Earth-2 forecast requested."
        elif tool_name in (
            "natureos.simulate_petri",
            "natureos.simulate_mushroom",
            "natureos.simulate_compound",
            "natureos.simulate_genetic_circuit",
            "natureos.simulate_lifecycle",
            "natureos.simulate_physics",
            "natureos.growth_analytics",
            "natureos.retrosynthesis",
            "natureos.alchemy_lab",
        ):
            simulation_type = tool_name.replace("natureos.", "")
            result_data = await client.run_simulation(simulation_type=simulation_type, params={"query": query})
            msg = f"NatureOS {simulation_type.replace('_', ' ')} run started."
        elif tool_name == "natureos.sync_twin":
            m = re.search(r"device\s+([A-Za-z0-9_-]+)", query)
            device_id = m.group(1) if m else ""
            if not device_id:
                return ToolCallResponse(
                    success=False,
                    tool_name=tool_name,
                    result="Please specify a device id to sync.",
                    timestamp=datetime.utcnow().isoformat(),
                )
            result_data = await client.sync_digital_twin(device_id)
            msg = f"Digital twin sync complete for {device_id}."
        elif tool_name == "natureos.symbiosis_network":
            coords = _parse_lat_lon(query)
            if not coords:
                return ToolCallResponse(
                    success=False,
                    tool_name=tool_name,
                    result="Please include latitude and longitude for symbiosis analysis.",
                    timestamp=datetime.utcnow().isoformat(),
                )
            latitude, longitude = coords
            radius_match = re.search(r"radius\s+(\d+)", query)
            radius_meters = int(radius_match.group(1)) if radius_match else 1000
            result_data = await client.analyze_symbiosis_network(latitude, longitude, radius_meters)
            msg = "Symbiosis network analysis complete."
        elif tool_name == "natureos.track_spores":
            coords = _parse_lat_lon(query)
            if not coords:
                return ToolCallResponse(
                    success=False,
                    tool_name=tool_name,
                    result="Please include latitude and longitude to track spores.",
                    timestamp=datetime.utcnow().isoformat(),
                )
            latitude, longitude = coords
            iso_times = re.findall(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z?", query)
            if len(iso_times) >= 2:
                start_time, end_time = iso_times[0], iso_times[1]
            else:
                now = datetime.utcnow()
                end_time = now.isoformat()
                start_time = (now - timedelta(hours=24)).isoformat()
            result_data = await client.track_spores(latitude, longitude, start_time, end_time)
            msg = "Spore tracking request submitted."
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


def _parse_lat_lon(query: str) -> Optional[tuple[float, float]]:
    lat_match = re.search(r"(?:lat|latitude)\s*[:=]?\s*(-?\d+(?:\.\d+)?)", query)
    lon_match = re.search(r"(?:lon|long|longitude)\s*[:=]?\s*(-?\d+(?:\.\d+)?)", query)
    if lat_match and lon_match:
        return float(lat_match.group(1)), float(lon_match.group(1))
    pair_match = re.search(r"(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)", query)
    if pair_match:
        return float(pair_match.group(1)), float(pair_match.group(2))
    return None


async def _run_workflow_voice(query: str) -> ToolCallResponse:
    """Execute an n8n workflow by name parsed from voice query (e.g. 'run the backup workflow')."""
    stopwords = {"run", "execute", "trigger", "workflow", "the", "a", "an", "please"}
    tokens = [t for t in re.findall(r"[a-z0-9]+", query.lower()) if t not in stopwords]
    if not tokens:
        return ToolCallResponse(
            success=False,
            tool_name="run_workflow",
            result="I couldn't identify which workflow to run. Say for example: run the backup workflow.",
            timestamp=datetime.utcnow().isoformat(),
        )
    try:
        from mycosoft_mas.agents.workflow.n8n_workflow_agent import N8NWorkflowAgent
        agent = N8NWorkflowAgent(agent_id="n8n-voice", name="N8N Workflow", config={})
        workflows = await agent.process_task({"type": "list_workflows"})
        names = [w.get("name") for w in workflows.get("result", {}).get("workflows", []) if w.get("name")]
        selected = None
        if names:
            query_lower = query.lower()

            def score(name: str) -> int:
                name_lower = name.lower()
                if name_lower == query_lower:
                    return 100
                if query_lower in name_lower:
                    return 90
                if all(token in name_lower for token in tokens):
                    return 80
                if any(token in name_lower for token in tokens):
                    return 60
                return 0

            ranked = sorted(((score(name), name) for name in names), reverse=True)
            if ranked and ranked[0][0] >= 60:
                selected = ranked[0][1]
        if not selected:
            suggestions = ", ".join(names[:3]) if names else "none"
            return ToolCallResponse(
                success=False,
                tool_name="run_workflow",
                result=f"Workflow not found. Try one of: {suggestions}",
                data={"available": names[:10]},
                timestamp=datetime.utcnow().isoformat(),
            )
        result = await agent.process_task({"type": "execute_workflow", "workflow_name": selected})
        status = result.get("status", "unknown")
        if status == "success":
            msg = f"Workflow {selected} executed successfully."
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
            result=f"Workflow {selected} returned: {status}. {result.get('message', '')}"[:300],
            data=result,
            timestamp=datetime.utcnow().isoformat(),
        )
    except Exception as e:
        logger.exception("run_workflow voice failed: %s", e)
        return ToolCallResponse(
            success=False,
            tool_name="run_workflow",
            result=f"Failed to run workflow: {str(e)[:150]}.",
            timestamp=datetime.utcnow().isoformat(),
        )


async def _get_device_status(query: str) -> ToolCallResponse:
    """Get status of a NatureOS device."""
    import httpx
    mas_base = _get_mas_base_url()
    try:
        async with httpx.AsyncClient(timeout=6.0) as client:
            response = await client.get(f"{mas_base}/api/devices", params={"include_offline": True})
            response.raise_for_status()
            devices_payload = response.json()
        devices = devices_payload.get("devices", [])
        if not devices:
            return ToolCallResponse(
                success=False,
                tool_name="device_status",
                result="No devices are registered in the MAS device registry.",
                data=devices_payload,
                timestamp=datetime.utcnow().isoformat(),
            )
        matched = _pick_device_match(devices, query)
        if not matched:
            available = [d.get("device_name") or d.get("device_id") for d in devices][:5]
            return ToolCallResponse(
                success=False,
                tool_name="device_status",
                result="No matching device found. Try a device name like: " + ", ".join([a for a in available if a]),
                data={"available": available},
                timestamp=datetime.utcnow().isoformat(),
            )
        name = matched.get("device_display_name") or matched.get("device_name") or matched.get("device_id", "device")
        status = matched.get("status", "unknown")
        last_seen = matched.get("last_seen")
        role = matched.get("device_role")
        sensors = matched.get("sensors")
        result = f"{name} is {status}."
        if role:
            result += f" Role: {role}."
        if last_seen:
            result += f" Last seen at {last_seen}."
        if sensors:
            result += f" Sensors: {', '.join(sensors[:4])}."
        return ToolCallResponse(
            success=True,
            tool_name="device_status",
            result=result,
            data=matched,
            timestamp=datetime.utcnow().isoformat(),
        )
    except Exception as e:
        logger.warning("Device registry lookup failed: %s", e)
        return ToolCallResponse(
            success=False,
            tool_name="device_status",
            result="Device registry lookup failed. Check MAS device registry status.",
            data={"error": str(e)[:200]},
            timestamp=datetime.utcnow().isoformat(),
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
            success=False,
            tool_name="agent_list",
            result="Agent registry unavailable. Check MAS registry health.",
            data={"error": str(e)[:200]},
            timestamp=datetime.utcnow().isoformat()
        )


async def _query_mindex(query: str) -> ToolCallResponse:
    """Query the MINDEX fungal knowledge base."""
    import httpx
    # Extract search terms
    search_terms = query.lower()
    for prefix in ["search", "find", "query", "look up", "mindex", "fungal", "mushroom", "species"]:
        search_terms = search_terms.replace(prefix, "").strip()
    if not search_terms:
        return ToolCallResponse(
            success=False,
            tool_name="query_mindex",
            result="Provide a search term for MINDEX.",
            timestamp=datetime.utcnow().isoformat(),
        )

    mindex_base = _get_mindex_base_url()
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            response = await client.get(
                f"{mindex_base}/unified-search",
                params={"q": search_terms, "limit": 5},
            )
            response.raise_for_status()
            payload = response.json()
        results = payload.get("results", {})
        taxa = results.get("taxa") or []
        compounds = results.get("compounds") or []
        if taxa:
            taxon = taxa[0]
            name = taxon.get("scientific_name") or "Unknown taxon"
            common = taxon.get("common_name")
            rank = taxon.get("rank")
            toxicity = taxon.get("toxicity")
            edibility = taxon.get("edibility")
            result = f"MINDEX found {name}."
            if common:
                result += f" Common name: {common}."
            if rank:
                result += f" Rank: {rank}."
            if toxicity:
                result += f" Toxicity: {toxicity}."
            if edibility:
                result += f" Edibility: {edibility}."
            return ToolCallResponse(
                success=True,
                tool_name="query_mindex",
                result=result,
                data=taxon,
                timestamp=datetime.utcnow().isoformat(),
            )
        if compounds:
            compound = compounds[0]
            name = compound.get("name") or "Unknown compound"
            formula = compound.get("formula")
            mw = compound.get("molecular_weight")
            result = f"MINDEX found compound {name}."
            if formula:
                result += f" Formula: {formula}."
            if mw:
                result += f" Molecular weight: {mw}."
            return ToolCallResponse(
                success=True,
                tool_name="query_mindex",
                result=result,
                data=compound,
                timestamp=datetime.utcnow().isoformat(),
            )
        return ToolCallResponse(
            success=False,
            tool_name="query_mindex",
            result=f"No data available for '{search_terms}'.",
            data={"query": search_terms, "results": results},
            timestamp=datetime.utcnow().isoformat(),
        )
    except Exception as e:
        logger.warning("MINDEX query failed: %s", e)
        return ToolCallResponse(
            success=False,
            tool_name="query_mindex",
            result="MINDEX query failed. Check MINDEX API health.",
            data={"error": str(e)[:200]},
            timestamp=datetime.utcnow().isoformat(),
        )


async def _get_system_status(query: str) -> ToolCallResponse:
    """Get overall system status."""
    import httpx
    mas_base = _get_mas_base_url()
    mindex_base = _get_mindex_base_url()
    n8n_base = _get_n8n_base_url()
    status_data: Dict[str, Any] = {
        "mas": "unknown",
        "mindex": "unknown",
        "n8n": "unknown",
        "devices": "unknown",
        "workflows": "unknown",
    }
    async with httpx.AsyncClient(timeout=6.0) as client:
        try:
            mas_health = await client.get(f"{mas_base}/health")
            status_data["mas"] = "healthy" if mas_health.status_code == 200 else f"unhealthy:{mas_health.status_code}"
        except Exception as e:
            status_data["mas"] = f"unavailable:{str(e)[:120]}"
        try:
            mindex_health = await client.get(f"{mindex_base}/api/mindex/health")
            status_data["mindex"] = "healthy" if mindex_health.status_code == 200 else f"unhealthy:{mindex_health.status_code}"
        except Exception as e:
            status_data["mindex"] = f"unavailable:{str(e)[:120]}"
        try:
            n8n_health = await client.get(f"{n8n_base}/healthz")
            status_data["n8n"] = "healthy" if n8n_health.status_code == 200 else f"unhealthy:{n8n_health.status_code}"
        except Exception as e:
            status_data["n8n"] = f"unavailable:{str(e)[:120]}"
        try:
            devices_health = await client.get(f"{mas_base}/api/devices/health")
            if devices_health.status_code == 200:
                payload = devices_health.json()
                status_data["devices"] = payload
            else:
                status_data["devices"] = f"unhealthy:{devices_health.status_code}"
        except Exception as e:
            status_data["devices"] = f"unavailable:{str(e)[:120]}"
        try:
            workflows_health = await client.get(f"{mas_base}/api/workflows/health")
            status_data["workflows"] = workflows_health.json() if workflows_health.status_code == 200 else f"unhealthy:{workflows_health.status_code}"
        except Exception as e:
            status_data["workflows"] = f"unavailable:{str(e)[:120]}"

    device_summary = ""
    if isinstance(status_data["devices"], dict):
        online = status_data["devices"].get("online_devices")
        total = status_data["devices"].get("total_devices")
        if online is not None and total is not None:
            device_summary = f" Devices online: {online}/{total}."
    result = (
        f"System status: MAS is {status_data['mas']}. MINDEX is {status_data['mindex']}. "
        f"n8n is {status_data['n8n']}.{device_summary}"
    )
    return ToolCallResponse(
        success=True,
        tool_name="system_status",
        result=result,
        data=status_data,
        timestamp=datetime.utcnow().isoformat(),
    )


# Direct device status endpoint (called by bridge)
@router.get("/devices/{device_name}/status")
async def get_device_status_direct(device_name: str):
    """Direct endpoint for device status lookup."""
    import httpx
    mas_base = _get_mas_base_url()
    normalized = device_name.lower().replace(" ", "").replace("-", "")
    try:
        async with httpx.AsyncClient(timeout=6.0) as client:
            response = await client.get(f"{mas_base}/api/devices", params={"include_offline": True})
            response.raise_for_status()
            devices_payload = response.json()
        devices = devices_payload.get("devices", [])
        if not devices:
            raise HTTPException(status_code=404, detail="No devices registered")
        matched = _pick_device_match(devices, normalized)
        if matched:
            return matched
        raise HTTPException(status_code=404, detail=f"Device {device_name} not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Device registry unavailable: {str(e)[:120]}")
