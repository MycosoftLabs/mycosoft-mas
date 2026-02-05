"""
Earth2 Voice Command Handler - February 5, 2026
Processes voice commands related to Earth2Studio weather models and forecasts.

Integrates with:
- Earth2Studio API (localhost:8220)
- MYCA Voice Orchestrator
- PersonaPlex Bridge for spoken responses

This file should be imported by the voice pipeline:
    from scripts.earth2_voice_handler import process_earth2_voice, Earth2VoiceHandler
"""

import re
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from enum import Enum

try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False

logger = logging.getLogger(__name__)


class Earth2Intent(Enum):
    """Earth2-specific voice intents."""
    FORECAST = "earth2_forecast"
    NOWCAST = "earth2_nowcast"
    LOAD_MODEL = "earth2_load_model"
    SHOW_LAYER = "earth2_show_layer"
    HIDE_LAYER = "earth2_hide_layer"
    EXPLAIN = "earth2_explain"
    GPU_STATUS = "earth2_gpu_status"
    UNKNOWN = "unknown"


@dataclass
class Earth2Command:
    """Parsed Earth2 voice command."""
    intent: Earth2Intent
    model: Optional[str] = None
    lead_time: Optional[int] = None
    location: Optional[str] = None
    layer: Optional[str] = None
    variables: Optional[List[str]] = None
    raw_text: str = ""
    confidence: float = 0.0


# Intent patterns for Earth2 commands
EARTH2_PATTERNS = {
    Earth2Intent.FORECAST: [
        r"(?:show|run|display|get)\s+(?:me\s+)?(?:a\s+)?(?:(\d+)\s*(?:hour|hr|h))?\s*(?:weather\s+)?forecast",
        r"(?:show|run|display|get)\s+(?:me\s+)?(?:a\s+)?(?:weather\s+)?forecast",
        r"(?:what(?:'s| is| will be))\s+(?:the\s+)?weather\s+(?:in|for|at)?\s*(\d+)?\s*(?:hours?|days?)?",
        r"forecast\s+(?:for\s+)?(?:the\s+)?(?:next\s+)?(\d+)?\s*(?:hours?|days?)?",
        r"(?:will it|is it going to)\s+(?:rain|snow|storm)",
        r"hurricane\s+(?:forecast|path|track)",
        r"storm\s+(?:forecast|prediction|track)",
        r"(\d+)\s*(?:hour|hr|h)\s+(?:weather\s+)?forecast",
    ],
    Earth2Intent.NOWCAST: [
        r"(?:show|run|display|get)\s+(?:a\s+)?nowcast",
        r"current\s+(?:weather|conditions)",
        r"what(?:'s| is)\s+(?:the\s+)?weather\s+(?:right\s+)?now",
        r"real[\s-]?time\s+weather",
    ],
    Earth2Intent.LOAD_MODEL: [
        r"(?:load|use|switch to|activate)\s+(?:the\s+)?(fcn|fourcastnet|pangu|graphcast|sfno|aurora|fuxi)\s*(?:model)?",
        r"(?:use|switch to)\s+(?:the\s+)?(fcn|fourcastnet|pangu|graphcast|sfno)\s+(?:for\s+)?(?:forecast(?:ing)?)?",
    ],
    Earth2Intent.SHOW_LAYER: [
        r"(?:show|display|turn on|enable|activate)\s+(?:the\s+)?(wind|temperature|temp|precipitation|rain|pressure|storm|spore|hurricane)\s*(?:layer|overlay|map)?",
        r"(?:show|display)\s+(?:me\s+)?(?:the\s+)?(storm\s+tracks?|spore\s+dispersal|wind\s+vectors?|weather\s+data)",
    ],
    Earth2Intent.HIDE_LAYER: [
        r"(?:hide|remove|turn off|disable|deactivate)\s+(?:the\s+)?(wind|temperature|temp|precipitation|rain|pressure|storm|spore|hurricane)\s*(?:layer|overlay|map)?",
        r"(?:clear|remove)\s+(?:all\s+)?(?:weather\s+)?(?:layers?|overlays?)",
    ],
    Earth2Intent.EXPLAIN: [
        r"(?:explain|describe|tell me about|what is|what's happening with)\s+(?:this\s+)?(storm|hurricane|weather|forecast|conditions?)",
        r"(?:why|what's causing)\s+(?:the\s+|this\s+)?(storm|rain|weather|temperature|wind)",
        r"(?:analyze|summarize)\s+(?:the\s+)?(?:current\s+)?(weather|conditions|forecast)",
    ],
    Earth2Intent.GPU_STATUS: [
        r"(?:what's|what is|show|check)\s+(?:the\s+)?(?:gpu|cuda|earth2)\s+(?:status|memory|usage)",
        r"(?:how much|how's)\s+(?:gpu|vram|cuda)\s+(?:memory|being used)?",
    ],
}

# Model name normalization
MODEL_ALIASES = {
    "fcn": "fcn",
    "fourcastnet": "fcn",
    "four cast net": "fcn",
    "pangu": "pangu",
    "pangu weather": "pangu",
    "graphcast": "graphcast",
    "graph cast": "graphcast",
    "sfno": "sfno",
    "aurora": "aurora",
    "fuxi": "fuxi",
}

# Layer name normalization
LAYER_ALIASES = {
    "wind": "wind_vectors",
    "temperature": "temperature",
    "temp": "temperature",
    "precipitation": "precipitation",
    "rain": "precipitation",
    "pressure": "pressure",
    "storm": "storm_tracks",
    "storms": "storm_tracks",
    "storm tracks": "storm_tracks",
    "spore": "spore_dispersal",
    "spores": "spore_dispersal",
    "spore dispersal": "spore_dispersal",
    "hurricane": "hurricane_track",
    "hurricanes": "hurricane_track",
}


class Earth2VoiceHandler:
    """Handles Earth2-related voice commands."""
    
    def __init__(self, earth2_url: str = "http://localhost:8220"):
        self.earth2_url = earth2_url
        self.client = None
        if HTTPX_AVAILABLE:
            self.client = httpx.AsyncClient(timeout=30.0)
        self._compiled_patterns = self._compile_patterns()
    
    def _compile_patterns(self) -> Dict[Earth2Intent, List[re.Pattern]]:
        """Pre-compile regex patterns."""
        compiled = {}
        for intent, patterns in EARTH2_PATTERNS.items():
            compiled[intent] = [re.compile(p, re.IGNORECASE) for p in patterns]
        return compiled
    
    def parse_command(self, text: str) -> Earth2Command:
        """Parse voice text into an Earth2 command."""
        text = text.strip().lower()
        
        for intent, patterns in self._compiled_patterns.items():
            for pattern in patterns:
                match = pattern.search(text)
                if match:
                    return self._build_command(intent, text, match)
        
        return Earth2Command(
            intent=Earth2Intent.UNKNOWN,
            raw_text=text,
            confidence=0.0
        )
    
    def _build_command(self, intent: Earth2Intent, text: str, match: re.Match) -> Earth2Command:
        """Build a command from matched pattern."""
        cmd = Earth2Command(
            intent=intent,
            raw_text=text,
            confidence=0.85
        )
        
        # Extract model name
        for alias, model in MODEL_ALIASES.items():
            if alias in text:
                cmd.model = model
                break
        
        # Extract lead time
        lead_match = re.search(r"(\d+)\s*(?:hour|hr|h)", text)
        if lead_match:
            cmd.lead_time = int(lead_match.group(1))
        else:
            day_match = re.search(r"(\d+)\s*day", text)
            if day_match:
                cmd.lead_time = int(day_match.group(1)) * 24
            else:
                if intent == Earth2Intent.FORECAST:
                    cmd.lead_time = 24
                elif intent == Earth2Intent.NOWCAST:
                    cmd.lead_time = 6
        
        # Extract layer name
        for alias, layer in LAYER_ALIASES.items():
            if alias in text:
                cmd.layer = layer
                break
        
        # Extract location
        loc_match = re.search(r"(?:for|in|at|over)\s+([a-zA-Z\s]+?)(?:\s+(?:in|for|at|over|\d|$))", text)
        if loc_match:
            cmd.location = loc_match.group(1).strip()
        
        return cmd
    
    async def execute_command(self, cmd: Earth2Command) -> Dict[str, Any]:
        """Execute an Earth2 command and return results."""
        try:
            if cmd.intent == Earth2Intent.FORECAST:
                return await self._run_forecast(cmd)
            elif cmd.intent == Earth2Intent.NOWCAST:
                return await self._run_nowcast(cmd)
            elif cmd.intent == Earth2Intent.LOAD_MODEL:
                return await self._load_model(cmd)
            elif cmd.intent == Earth2Intent.SHOW_LAYER:
                return self._show_layer(cmd)
            elif cmd.intent == Earth2Intent.HIDE_LAYER:
                return self._hide_layer(cmd)
            elif cmd.intent == Earth2Intent.EXPLAIN:
                return self._explain_weather(cmd)
            elif cmd.intent == Earth2Intent.GPU_STATUS:
                return await self._get_gpu_status()
            else:
                return {"success": False, "error": "Unknown intent"}
        except Exception as e:
            logger.error(f"Earth2 command execution failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def _run_forecast(self, cmd: Earth2Command) -> Dict[str, Any]:
        """Run a weather forecast."""
        model = cmd.model or "fcn"
        lead_time = cmd.lead_time or 24
        
        # Return frontend command (works with or without API)
        base_result = {
            "success": True,
            "action": "forecast",
            "model": model,
            "lead_time": lead_time,
            "frontend_command": {"type": "run_forecast", "model": model, "lead_time": lead_time},
            "speak": f"I'm preparing a {lead_time} hour forecast using the {model.upper()} model."
        }
        
        if not self.client:
            return base_result
        
        # Try to call the actual API
        try:
            await self.client.post(f"{self.earth2_url}/models/{model}/load")
            response = await self.client.post(
                f"{self.earth2_url}/inference",
                json={"model": model, "lead_time": lead_time}
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "success": True,
                    "action": "forecast",
                    "model": model,
                    "lead_time": lead_time,
                    "forecast_id": data.get("forecast_id"),
                    "frontend_command": {"type": "show_forecast", "forecast_id": data.get("forecast_id")},
                    "speak": f"I'm running a {lead_time} hour forecast using the {model.upper()} model. The results will appear on the map shortly."
                }
            else:
                # API responded but with error - still return command for frontend
                base_result["api_status"] = response.status_code
                return base_result
        except Exception as e:
            # API unavailable - still return command for frontend to handle
            logger.warning(f"Earth2 API unavailable: {e}")
            base_result["api_error"] = str(e)
            return base_result
    
    async def _run_nowcast(self, cmd: Earth2Command) -> Dict[str, Any]:
        """Run a nowcast."""
        return {
            "success": True,
            "action": "nowcast",
            "lead_time": 6,
            "frontend_command": {"type": "run_nowcast"},
            "speak": "I'm generating a 6-hour nowcast showing current weather conditions."
        }
    
    async def _load_model(self, cmd: Earth2Command) -> Dict[str, Any]:
        """Load a specific Earth2 model."""
        model = cmd.model
        if not model:
            return {"success": False, "error": "No model specified"}
        
        if self.client:
            try:
                response = await self.client.post(f"{self.earth2_url}/models/{model}/load")
                if response.status_code == 200:
                    return {
                        "success": True,
                        "action": "load_model",
                        "model": model,
                        "speak": f"I've loaded the {model.upper()} weather model. It's ready for forecasting."
                    }
            except Exception as e:
                pass
        
        return {
            "success": True,
            "action": "load_model",
            "model": model,
            "frontend_command": {"type": "load_model", "model": model},
            "speak": f"Loading the {model.upper()} model."
        }
    
    def _show_layer(self, cmd: Earth2Command) -> Dict[str, Any]:
        """Show a weather layer on the map."""
        layer = cmd.layer or "temperature"
        
        return {
            "success": True,
            "action": "show_layer",
            "layer": layer,
            "frontend_command": {"type": "show_layer", "layer": layer},
            "speak": f"I'm displaying the {layer.replace('_', ' ')} layer on the map."
        }
    
    def _hide_layer(self, cmd: Earth2Command) -> Dict[str, Any]:
        """Hide a weather layer."""
        layer = cmd.layer
        
        return {
            "success": True,
            "action": "hide_layer",
            "layer": layer,
            "frontend_command": {"type": "hide_layer", "layer": layer},
            "speak": f"I've hidden the {layer.replace('_', ' ') if layer else 'weather'} layer."
        }
    
    def _explain_weather(self, cmd: Earth2Command) -> Dict[str, Any]:
        """Generate explanation of current weather data."""
        return {
            "success": True,
            "action": "explain",
            "needs_context": True,
            "frontend_command": {"type": "get_context"},
            "speak": "Based on the current forecast data, let me analyze what's happening..."
        }
    
    async def _get_gpu_status(self) -> Dict[str, Any]:
        """Get GPU status from Earth2 API."""
        if not self.client:
            return {
                "success": True,
                "action": "gpu_status",
                "speak": "GPU status requires the Earth2 API to be running."
            }
        
        try:
            response = await self.client.get(f"{self.earth2_url}/gpu/status")
            if response.status_code == 200:
                data = response.json()
                if data.get("available"):
                    speak = (
                        f"The GPU is operational. "
                        f"Using {data.get('allocated_memory_gb', 0):.1f} gigabytes "
                        f"of {data.get('total_memory_gb', 0):.1f} available."
                    )
                else:
                    speak = "The GPU is not available."
                
                return {
                    "success": True,
                    "action": "gpu_status",
                    "gpu": data,
                    "speak": speak
                }
        except Exception as e:
            pass
        
        return {"success": False, "error": "GPU status unavailable"}
    
    async def close(self):
        """Close HTTP client."""
        if self.client:
            await self.client.aclose()


# Singleton instance
_handler: Optional[Earth2VoiceHandler] = None


def get_earth2_handler() -> Earth2VoiceHandler:
    """Get or create the Earth2 voice handler singleton."""
    global _handler
    if _handler is None:
        _handler = Earth2VoiceHandler()
    return _handler


async def process_earth2_voice(text: str) -> Dict[str, Any]:
    """
    Process a voice command for Earth2.
    
    Returns:
        Dict with:
        - success: bool
        - action: str (the action taken)
        - speak: str (what MYCA should say)
        - frontend_command: dict (command for frontend, if any)
    """
    handler = get_earth2_handler()
    cmd = handler.parse_command(text)
    
    if cmd.intent == Earth2Intent.UNKNOWN:
        return {
            "success": False,
            "matched": False,
            "error": "Not an Earth2 command"
        }
    
    result = await handler.execute_command(cmd)
    result["matched"] = True
    result["intent"] = cmd.intent.value
    return result


def is_earth2_command(text: str) -> bool:
    """Quick check if text might be an Earth2 command."""
    handler = get_earth2_handler()
    cmd = handler.parse_command(text)
    return cmd.intent != Earth2Intent.UNKNOWN
