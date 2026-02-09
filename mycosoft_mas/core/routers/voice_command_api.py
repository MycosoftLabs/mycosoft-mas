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

logger = logging.getLogger("VoiceCommandAPI")

router = APIRouter(prefix="/voice", tags=["voice"])


# ============================================================================
# Request/Response Models
# ============================================================================

class VoiceCommandRequest(BaseModel):
    """Request to route a voice command."""
    text: str = Field(..., description="Transcribed voice command text")
    session_id: Optional[str] = Field(None, description="Voice session ID")
    user_id: Optional[str] = Field(None, description="User ID for memory")
    source: str = Field("personaplex", description="Command source")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context (map viewport, etc.)")


class FrontendCommand(BaseModel):
    """Command to be executed by the frontend."""
    type: str = Field(..., description="Command type: flyTo, setZoom, showLayer, etc.")
    params: Dict[str, Any] = Field(default_factory=dict, description="Command parameters")


class VoiceCommandResponse(BaseModel):
    """Response from voice command routing."""
    success: bool = Field(..., description="Whether command was processed")
    domain: str = Field(..., description="Domain that handled command: earth2, map, crep, system, general")
    action: Optional[str] = Field(None, description="Action taken")
    speak: Optional[str] = Field(None, description="Text for MYCA to speak")
    frontend_command: Optional[Dict[str, Any]] = Field(None, description="Command for frontend to execute")
    needs_llm_response: bool = Field(False, description="Whether LLM should generate additional response")
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
        
        logger.info(f"Voice command routed: '{request.text}' -> {result.domain.value}/{result.action}")
        
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
            results.append({
                "success": result.success,
                "domain": result.domain.value,
                "action": result.action,
                "frontend_command": result.frontend_command,
                "raw_text": result.raw_text,
            })
        except Exception as e:
            results.append({
                "success": False,
                "error": str(e),
                "raw_text": cmd.text,
            })
    
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