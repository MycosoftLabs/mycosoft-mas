"""
Unified Voice Command Router - February 5, 2026
Central router for all voice command types including Earth2, Map, and CREP.

This router integrates:
- Earth2 voice commands (weather forecasts, model control)
- Map voice commands (navigation, zoom, layers)
- CREP voice commands (entity queries, filters)
- General MYCA commands (system control, queries)

Usage:
    from scripts.voice_command_router import route_voice_command, VoiceCommandRouter
    
    result = await route_voice_command("show me a 24 hour forecast")
    # Returns: {"success": True, "domain": "earth2", "action": "forecast", ...}
"""

import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from enum import Enum

# Import the specialized handlers
from scripts.earth2_voice_handler import (
    process_earth2_voice,
    is_earth2_command,
    Earth2Intent,
)
from scripts.map_voice_handler import (
    process_map_voice,
    is_map_command,
    MapIntent,
)

logger = logging.getLogger(__name__)


class VoiceDomain(Enum):
    """Voice command domains."""
    EARTH2 = "earth2"
    MAP = "map"
    CREP = "crep"
    SYSTEM = "system"
    GENERAL = "general"
    UNKNOWN = "unknown"


@dataclass
class RouteResult:
    """Result of routing a voice command."""
    domain: VoiceDomain
    success: bool
    action: Optional[str] = None
    speak: Optional[str] = None
    frontend_command: Optional[Dict[str, Any]] = None
    needs_llm_response: bool = False
    error: Optional[str] = None
    raw_text: str = ""


# Keywords for quick domain detection (higher score = more priority)
DOMAIN_KEYWORDS = {
    VoiceDomain.EARTH2: [
        "forecast", "weather forecast", "nowcast", "hurricane", "storm track",
        "fcn", "fourcastnet", "pangu", "graphcast", "sfno", "aurora", "fuxi",
        "precipitation", "wind speed", "temperature", "pressure",
        "earth2", "earth 2", "weather model", "climate",
        "hour forecast", "day forecast", "weather prediction",
    ],
    VoiceDomain.MAP: [
        "zoom", "pan", "navigate", "go to", "fly to",
        "map", "terrain", "satellite view", "center on",
        "north", "south", "east", "west", "left", "right",
    ],
    VoiceDomain.CREP: [
        "seismic", "volcanic", "earthquake", "vessel", "aircraft",
        "satellite", "ais", "ads-b", "tracking", "entity",
        "filter", "severity", "crep", "event", "show seismic",
        "seismic events", "volcanic events", "earthquake events",
    ],
    VoiceDomain.SYSTEM: [
        "myca", "system", "status", "shutdown", "restart",
        "volume", "mute", "unmute", "settings", "config",
    ],
}


class VoiceCommandRouter:
    """Routes voice commands to appropriate handlers."""
    
    def __init__(self):
        self.handlers = {
            VoiceDomain.EARTH2: self._handle_earth2,
            VoiceDomain.MAP: self._handle_map,
            VoiceDomain.CREP: self._handle_crep,
            VoiceDomain.SYSTEM: self._handle_system,
            VoiceDomain.GENERAL: self._handle_general,
        }
    
    def detect_domain(self, text: str) -> VoiceDomain:
        """Detect the domain of a voice command using keywords and handlers."""
        text_lower = text.lower()
        
        # Quick CREP check - if it contains CREP-specific keywords, prioritize CREP
        crep_specific = ["seismic", "volcanic", "earthquake", "vessel", "aircraft", "satellite", "ais"]
        for kw in crep_specific:
            if kw in text_lower:
                return VoiceDomain.CREP
        
        # Try specialized handlers (most accurate)
        if is_earth2_command(text):
            return VoiceDomain.EARTH2
        if is_map_command(text):
            return VoiceDomain.MAP
        
        # Fallback to keyword matching
        domain_scores = {domain: 0 for domain in VoiceDomain}
        
        for domain, keywords in DOMAIN_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text_lower:
                    # Multi-word keywords get higher score
                    domain_scores[domain] += len(keyword.split())
        
        # Get highest scoring domain
        max_score = max(domain_scores.values())
        
        if max_score > 0:
            # Return highest scoring domain
            for domain, score in sorted(domain_scores.items(), key=lambda x: -x[1]):
                if score == max_score:
                    return domain
        
        return VoiceDomain.GENERAL
    
    async def route(self, text: str) -> RouteResult:
        """Route a voice command to the appropriate handler."""
        domain = self.detect_domain(text)
        handler = self.handlers.get(domain, self._handle_general)
        
        try:
            result = await handler(text)
            result.domain = domain
            result.raw_text = text
            return result
        except Exception as e:
            logger.error(f"Voice command routing failed: {e}")
            return RouteResult(
                domain=domain,
                success=False,
                error=str(e),
                raw_text=text,
                needs_llm_response=True
            )
    
    async def _handle_earth2(self, text: str) -> RouteResult:
        """Handle Earth2 voice commands."""
        result = await process_earth2_voice(text)
        
        return RouteResult(
            domain=VoiceDomain.EARTH2,
            success=result.get("success", False),
            action=result.get("action"),
            speak=result.get("speak"),
            frontend_command=result.get("frontend_command"),
            error=result.get("error"),
            needs_llm_response=not result.get("matched", False)
        )
    
    async def _handle_map(self, text: str) -> RouteResult:
        """Handle map voice commands."""
        result = process_map_voice(text)
        
        return RouteResult(
            domain=VoiceDomain.MAP,
            success=result.get("success", False),
            action=result.get("action"),
            speak=result.get("speak"),
            frontend_command=result.get("frontend_command"),
            error=result.get("error"),
            needs_llm_response=result.get("needs_context", False)
        )
    
    async def _handle_crep(self, text: str) -> RouteResult:
        """Handle CREP-specific commands."""
        # CREP commands often overlap with map commands for layers/filters
        # Try map handler first
        map_result = process_map_voice(text)
        
        if map_result.get("matched"):
            return RouteResult(
                domain=VoiceDomain.CREP,
                success=map_result.get("success", False),
                action=map_result.get("action"),
                speak=map_result.get("speak"),
                frontend_command=map_result.get("frontend_command"),
                error=map_result.get("error"),
                needs_llm_response=map_result.get("needs_context", False)
            )
        
        # Generic CREP query - needs LLM
        return RouteResult(
            domain=VoiceDomain.CREP,
            success=True,
            action="crep_query",
            needs_llm_response=True,
            speak="Let me look that up in the CREP database."
        )
    
    async def _handle_system(self, text: str) -> RouteResult:
        """Handle system commands."""
        text_lower = text.lower()
        
        if "status" in text_lower:
            return RouteResult(
                domain=VoiceDomain.SYSTEM,
                success=True,
                action="get_status",
                frontend_command={"type": "getSystemStatus"},
                speak="Checking system status."
            )
        elif "mute" in text_lower:
            is_unmute = "unmute" in text_lower
            return RouteResult(
                domain=VoiceDomain.SYSTEM,
                success=True,
                action="unmute" if is_unmute else "mute",
                frontend_command={"type": "setMute", "muted": not is_unmute},
                speak="Unmuting audio." if is_unmute else "Muting audio."
            )
        
        # General system command - needs LLM
        return RouteResult(
            domain=VoiceDomain.SYSTEM,
            success=True,
            action="system_query",
            needs_llm_response=True
        )
    
    async def _handle_general(self, text: str) -> RouteResult:
        """Handle general queries that need LLM response."""
        return RouteResult(
            domain=VoiceDomain.GENERAL,
            success=True,
            action="general_query",
            needs_llm_response=True
        )


# Singleton router instance
_router: Optional[VoiceCommandRouter] = None


def get_router() -> VoiceCommandRouter:
    """Get or create the voice command router singleton."""
    global _router
    if _router is None:
        _router = VoiceCommandRouter()
    return _router


async def route_voice_command(text: str) -> Dict[str, Any]:
    """
    Route a voice command to the appropriate handler.
    
    This is the main entry point for voice command processing.
    
    Args:
        text: The transcribed voice command text.
    
    Returns:
        Dict containing:
        - domain: str (earth2, map, crep, system, general)
        - success: bool
        - action: str (the action to take)
        - speak: str (what MYCA should say)
        - frontend_command: dict (command for frontend)
        - needs_llm_response: bool (if LLM should generate response)
    """
    router = get_router()
    result = await router.route(text)
    
    return {
        "domain": result.domain.value,
        "success": result.success,
        "action": result.action,
        "speak": result.speak,
        "frontend_command": result.frontend_command,
        "needs_llm_response": result.needs_llm_response,
        "error": result.error,
        "raw_text": result.raw_text,
    }


def classify_intent_quick(text: str) -> str:
    """
    Quick intent classification without full processing.
    Returns the domain as a string.
    """
    router = get_router()
    domain = router.detect_domain(text)
    return domain.value


# Export all intents for compatibility
__all__ = [
    "route_voice_command",
    "classify_intent_quick",
    "VoiceCommandRouter",
    "VoiceDomain",
    "RouteResult",
    "get_router",
    # Re-export from handlers
    "Earth2Intent",
    "MapIntent",
    "is_earth2_command",
    "is_map_command",
]
