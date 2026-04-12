"""
CREP Voice Command API - February 6, 2026

Routes voice commands through the VoiceCommandRouter to return
frontend_command objects for map/dashboard control.

This is specifically for CREP map commands like:
- Navigation: "go to Tokyo", "zoom in", "pan left"
- Layers: "show satellites", "hide aircraft"
- Filters: "filter by severity high", "clear filters"
- Earth2: "show 24 hour forecast", "show wind layer"
- CREP: "show seismic events", "tell me about this earthquake"

The response includes:
- frontend_command: JSON object for the map to execute
- speak: What MYCA should say in response
- domain: Which domain handled the command (map, earth2, crep, system)
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from mycosoft_mas.agents.clusters.taco.ocean_predictor_agent import OceanPredictorAgent
from mycosoft_mas.agents.clusters.taco.signal_classifier_agent import SignalClassifierAgent
from mycosoft_mas.integrations.zeetachec_client import MaritimeSensorNetworkClient

logger = logging.getLogger("VoiceCommandAPI")

router = APIRouter(prefix="/voice", tags=["voice"])
sensor_network_client = MaritimeSensorNetworkClient()
signal_classifier_agent = SignalClassifierAgent(config={})
ocean_predictor_agent = OceanPredictorAgent(config={})


# ============================================================================
# Request/Response Models
# ============================================================================


class VoiceCommandRequest(BaseModel):
    """Request to route a voice command."""

    text: str = Field(..., description="Transcribed voice command text")
    session_id: Optional[str] = Field(None, description="Voice session ID")
    user_id: Optional[str] = Field(None, description="User ID for memory")
    source: str = Field("personaplex", description="Command source")
    context: Optional[Dict[str, Any]] = Field(
        None, description="Additional context (map viewport, etc.)"
    )


class FrontendCommand(BaseModel):
    """Command to be executed by the frontend."""

    type: str = Field(..., description="Command type: flyTo, setZoom, showLayer, etc.")
    params: Dict[str, Any] = Field(default_factory=dict, description="Command parameters")


class VoiceCommandResponse(BaseModel):
    """Response from voice command routing."""

    success: bool = Field(..., description="Whether command was processed")
    domain: str = Field(
        ..., description="Domain that handled command: earth2, map, crep, system, general"
    )
    action: Optional[str] = Field(None, description="Action taken")
    speak: Optional[str] = Field(None, description="Text for MYCA to speak")
    frontend_command: Optional[Dict[str, Any]] = Field(
        None, description="Command for frontend to execute"
    )
    needs_llm_response: bool = Field(
        False, description="Whether LLM should generate additional response"
    )
    error: Optional[str] = Field(None, description="Error message if failed")
    raw_text: str = Field(..., description="Original command text")
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


# ============================================================================
# Voice Command Router Integration
# ============================================================================

_router_instance = None


async def get_voice_command_router():
    """Get the VoiceCommandRouter singleton."""
    global _router_instance
    if _router_instance is None:
        try:
            from scripts.voice_command_router import VoiceCommandRouter

            _router_instance = VoiceCommandRouter()
            logger.info("VoiceCommandRouter initialized")
        except ImportError as e:
            logger.error(f"Failed to import VoiceCommandRouter: {e}")
            raise
    return _router_instance


# ============================================================================
# API Endpoints
# ============================================================================


@router.post("/command", response_model=VoiceCommandResponse)
async def route_voice_command(request: VoiceCommandRequest):
    """
    Route a voice command and return frontend_command.

    This is the main endpoint for CREP voice control.
    """
    try:
        voice_router = await get_voice_command_router()
        result = await voice_router.route(request.text)

        response = VoiceCommandResponse(
            success=result.success,
            domain=result.domain.value,
            action=result.action,
            speak=result.speak,
            frontend_command=result.frontend_command,
            needs_llm_response=result.needs_llm_response,
            error=result.error,
            raw_text=result.raw_text,
        )

        logger.info(
            f"Voice command routed: '{request.text}' -> {result.domain.value}/{result.action}"
        )

        return response

    except ImportError:
        return VoiceCommandResponse(
            success=False,
            domain="unknown",
            error="VoiceCommandRouter not available",
            needs_llm_response=True,
            raw_text=request.text,
        )
    except Exception as e:
        logger.error(f"Voice command routing failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/command/batch")
async def route_voice_commands_batch(commands: List[VoiceCommandRequest]):
    """Route multiple voice commands in batch."""
    results = []
    voice_router = await get_voice_command_router()

    for cmd in commands:
        try:
            result = await voice_router.route(cmd.text)
            results.append(
                {
                    "success": result.success,
                    "domain": result.domain.value,
                    "action": result.action,
                    "frontend_command": result.frontend_command,
                    "raw_text": result.raw_text,
                }
            )
        except Exception as e:
            results.append(
                {
                    "success": False,
                    "error": str(e),
                    "raw_text": cmd.text,
                }
            )

    return {"results": results, "count": len(results)}


@router.get("/command/domains")
async def get_command_domains():
    """Get available voice command domains and their capabilities."""
    return {
        "domains": {
            "earth2": {
                "description": "Weather forecasts and Earth2Studio models",
                "examples": [
                    "show me a 24 hour forecast",
                    "load the pangu model",
                    "show wind layer",
                ],
            },
            "map": {
                "description": "Map navigation and visualization",
                "examples": [
                    "go to Tokyo",
                    "zoom in",
                    "pan left",
                    "reset view",
                ],
            },
            "crep": {
                "description": "CREP entities and layers",
                "examples": [
                    "show satellites",
                    "hide aircraft",
                    "show seismic events",
                    "filter by high severity",
                ],
            },
            "system": {
                "description": "System control",
                "examples": ["system status", "mute audio"],
            },
            "general": {
                "description": "General queries (routed to LLM)",
                "examples": ["what time is it"],
            },
        }
    }


@router.get("/command/help")
async def get_command_help():
    """Get voice command help text."""
    return {
        "help": """
CREP Voice Commands:

NAVIGATION:
- "Go to [location]" - Navigate to a location
- "Zoom in/out" - Adjust zoom level
- "Pan left/right/up/down" - Pan the map
- "Reset view" - Return to global view

LAYERS:
- "Show [layer]" - Enable a layer
- "Hide [layer]" - Disable a layer

FILTERS:
- "Filter by [type] [value]" - Apply filter
- "Clear filters" - Remove all filters

EARTH2:
- "Show me a [X] hour forecast" - Run weather forecast
- "Load [model] model" - Load weather model
        """.strip()
    }


@router.get("/health")
async def voice_command_health():
    """Health check for voice command API."""
    try:
        voice_router = await get_voice_command_router()
        router_available = voice_router is not None
    except Exception:
        router_available = False

    return {
        "status": "healthy" if router_available else "degraded",
        "service": "voice-command-api",
        "version": "1.0.0",
        "router_available": router_available,
    }


# ============================================================================
# TAC-O MARITIME VOICE COMMANDS
# ============================================================================

TACO_VOICE_INTENTS = {
    "classify_contact": "Run classification on bearing {bearing} range {range}",
    "sonar_prediction": "What is current sonar performance prediction",
    "sensor_status": "Report sensor network status",
    "threat_summary": "Give me current threat summary",
    "deploy_sensor": "Deploy sensor at depth {depth}",
    "environmental_report": "Report current ocean environment",
}


@router.post("/taco")
async def taco_voice_command(command: dict):
    """Process TAC-O maritime voice commands.
    
    Accepts natural language maritime commands and routes them
    to the appropriate TAC-O agent or FUSARIUM maritime endpoint.
    """
    intent = command.get("intent", "")
    params = command.get("params", {})

    if intent not in TACO_VOICE_INTENTS:
        return {
            "status": "unrecognized",
            "available_intents": list(TACO_VOICE_INTENTS.keys()),
        }
    try:
        if intent == "sensor_status":
            sensors = await sensor_network_client.get_sensor_status()
            return {
                "status": "routed",
                "intent": intent,
                "params": params,
                "result": {"sensors": sensors, "total": len(sensors)},
                "speak": f"Maritime sensor network status loaded for {len(sensors)} sensors",
            }

        if intent == "deploy_sensor":
            sensor_id = params.get("sensor_id")
            if not sensor_id:
                raise HTTPException(status_code=400, detail="sensor_id_required")
            result = await sensor_network_client.send_command(sensor_id, "deploy", params)
            return {
                "status": "routed",
                "intent": intent,
                "params": params,
                "result": result,
                "speak": f"Deploy command sent for sensor {sensor_id}",
            }

        if intent == "classify_contact":
            result = await signal_classifier_agent.process_task(
                {"type": "classify_acoustic", "sensor_data": params.get("sensor_data", params)}
            )
            return {
                "status": "routed",
                "intent": intent,
                "params": params,
                "result": result.get("result"),
                "speak": "Contact classification completed" if result.get("status") == "success" else "Contact classification failed",
            }

        if intent == "sonar_prediction":
            result = await ocean_predictor_agent.process_task(
                {"type": "predict_sonar_performance", "environment": params}
            )
            return {
                "status": "routed",
                "intent": intent,
                "params": params,
                "result": result.get("result"),
                "speak": "Sonar performance prediction ready" if result.get("status") == "success" else "Sonar prediction failed",
            }

        if intent == "environmental_report":
            result = await ocean_predictor_agent.process_task(
                {"type": "forecast_environment", "location": params}
            )
            return {
                "status": "routed",
                "intent": intent,
                "params": params,
                "result": result.get("result"),
                "speak": "Environmental report ready" if result.get("status") == "success" else "Environmental report failed",
            }

        if intent == "threat_summary":
            assessments = await sensor_network_client._get_json(f"{sensor_network_client.mindex_url}/taco/assessments?limit=10&offset=0")
            items = assessments.get("assessments", [])
            return {
                "status": "routed",
                "intent": intent,
                "params": params,
                "result": {"assessments": items, "total": len(items)},
                "speak": f"Loaded {len(items)} recent tactical assessments",
            }

        return {
            "status": "routed",
            "intent": intent,
            "params": params,
            "template": TACO_VOICE_INTENTS[intent],
            "speak": f"Processing {intent.replace('_', ' ')} command",
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "status": "error",
            "intent": intent,
            "params": params,
            "error": str(exc),
            "speak": f"Unable to process {intent.replace('_', ' ')} command",
        }
