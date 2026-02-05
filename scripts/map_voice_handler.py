"""
Map Voice Command Handler - February 5, 2026
Processes voice commands related to map navigation and manipulation.

Integrates with:
- CREP Dashboard MapLibre GL component
- MYCA Voice Orchestrator
- PersonaPlex Bridge for spoken responses

This file should be imported by the voice pipeline:
    from scripts.map_voice_handler import process_map_voice, MapVoiceHandler
"""

import re
import logging
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class MapIntent(Enum):
    """Map-specific voice intents."""
    NAVIGATE = "map_navigate"
    ZOOM = "map_zoom"
    PAN = "map_pan"
    LAYER = "map_layer"
    RESET = "map_reset"
    CREP_FILTER = "crep_filter"
    CREP_ENTITY = "crep_entity"
    WHAT_HERE = "map_what_here"
    UNKNOWN = "unknown"


@dataclass
class MapCommand:
    """Parsed map voice command."""
    intent: MapIntent
    location: Optional[str] = None
    coordinates: Optional[Tuple[float, float]] = None
    zoom_level: Optional[int] = None
    zoom_direction: Optional[str] = None  # "in" or "out"
    pan_direction: Optional[str] = None  # "left", "right", "up", "down"
    layer: Optional[str] = None
    layer_action: Optional[str] = None  # "show" or "hide"
    filter_type: Optional[str] = None
    filter_value: Optional[str] = None
    entity_name: Optional[str] = None
    raw_text: str = ""
    confidence: float = 0.0


# Intent patterns for map commands
MAP_PATTERNS = {
    # ZOOM patterns checked before NAVIGATE to prevent "zoom to level X" matching navigate
    MapIntent.ZOOM: [
        r"zoom\s+(in|out)(?:\s+(?:a\s+)?(?:little|bit|more|lot|fully))?",
        r"zoom\s+to\s+(?:level\s+)?(\d+)",
        r"zoom\s+(?:level\s+)?(\d+)",
        r"set\s+zoom\s+(?:to\s+)?(?:level\s+)?(\d+)",
        r"(?:get\s+)?closer",
        r"(?:pull|move)\s+(back|away)",
        r"(?:magnify|enlarge)",
    ],
    MapIntent.NAVIGATE: [
        r"(?:go to|navigate to|fly to|show me|take me to|move to|center on)\s+(.+?)(?:\s*$|\s+and|\s+then)",
        r"(?:where is|find|locate|search for)\s+(.+?)(?:\s*$|\s+and|\s+then)",
        r"(?:focus on)\s+(.+?)(?:\s*$|\s+and|\s+then)",
    ],
    MapIntent.PAN: [
        r"(?:pan|move|scroll|shift)\s+(left|right|up|down|north|south|east|west)",
        r"(?:go|move)\s+(left|right|up|down|north|south|east|west)(?:\s+a\s+(?:little|bit))?",
    ],
    MapIntent.LAYER: [
        r"(?:show|display|turn on|enable|activate)\s+(?:the\s+)?(satellites?|aircraft|vessels?|ships?|seismic|volcanic|weather|grid|terrain)\s*(?:layer)?",
        r"(?:hide|remove|turn off|disable|deactivate)\s+(?:the\s+)?(satellites?|aircraft|vessels?|ships?|seismic|volcanic|weather|grid|terrain)\s*(?:layer)?",
        r"(?:toggle)\s+(?:the\s+)?(satellites?|aircraft|vessels?|ships?|seismic|volcanic|weather|grid|terrain)\s*(?:layer)?",
    ],
    MapIntent.RESET: [
        r"(?:reset|clear|default)\s+(?:the\s+)?(?:view|map)",
        r"(?:show|display)\s+(?:the\s+)?(?:whole\s+)?world",
        r"(?:zoom|go)\s+(?:all the way\s+)?out",
        r"global\s+view",
    ],
    MapIntent.CREP_FILTER: [
        r"(?:filter|show only|display only)\s+(?:by\s+)?(severity|type|date|source)\s+(.+)",
        r"show\s+only\s+(seismic|volcanic|storm|high severity|low severity|critical)\s*(?:events?)?",
        r"(?:only\s+)?(?:show|display)\s+(seismic|volcanic|storm|high severity|low severity|critical)\s*(?:events?)?",
        r"(?:filter|show)\s+events?\s+(?:from|since|after|before)\s+(.+)",
        r"clear\s+(?:all\s+)?filters?",
    ],
    MapIntent.CREP_ENTITY: [
        r"(?:tell me about|what is|describe|explain|details (?:on|for)|info (?:on|about))\s+(?:this\s+)?(volcano|earthquake|aircraft|vessel|satellite|event|entity)",
        r"(?:tell me about|what is|describe|explain)\s+(.+?)(?:\s*$|\s+and|\s+then)",
        r"(?:click on|select|focus on)\s+(?:this\s+)?(?:event|entity|marker)",
    ],
    MapIntent.WHAT_HERE: [
        r"what(?:'s| is)\s+(?:happening\s+)?(?:here|at this location|in this area)",
        r"what\s+(?:am I|are we)\s+looking at",
        r"describe\s+(?:this\s+)?(?:area|location|view)",
        r"summarize\s+(?:this\s+)?(?:area|view|region)",
    ],
}

# Known location aliases for quick lookup
KNOWN_LOCATIONS = {
    "tokyo": (35.6762, 139.6503),
    "new york": (40.7128, -74.0060),
    "new york city": (40.7128, -74.0060),
    "nyc": (40.7128, -74.0060),
    "london": (51.5074, -0.1278),
    "paris": (48.8566, 2.3522),
    "sydney": (33.8688, 151.2093),
    "los angeles": (34.0522, -118.2437),
    "la": (34.0522, -118.2437),
    "san francisco": (37.7749, -122.4194),
    "sf": (37.7749, -122.4194),
    "miami": (25.7617, -80.1918),
    "florida": (27.6648, -81.5158),
    "california": (36.7783, -119.4179),
    "texas": (31.9686, -99.9018),
    "hawaii": (19.8968, -155.5828),
    "alaska": (64.2008, -152.4937),
    "china": (35.8617, 104.1954),
    "japan": (36.2048, 138.2529),
    "india": (20.5937, 78.9629),
    "australia": (-25.2744, 133.7751),
    "brazil": (-14.2350, -51.9253),
    "russia": (61.5240, 105.3188),
    "canada": (56.1304, -106.3468),
    "mexico": (23.6345, -102.5528),
    "germany": (51.1657, 10.4515),
    "france": (46.2276, 2.2137),
    "uk": (55.3781, -3.4360),
    "united kingdom": (55.3781, -3.4360),
    "atlantic ocean": (28.5, -41.5),
    "pacific ocean": (0.0, -160.0),
    "caribbean": (18.0, -75.0),
    "gulf of mexico": (25.0, -90.0),
}

# Layer name normalization
CREP_LAYER_ALIASES = {
    "satellite": "satellites",
    "satellites": "satellites",
    "sat": "satellites",
    "aircraft": "aircraft",
    "planes": "aircraft",
    "flights": "aircraft",
    "vessel": "vessels",
    "vessels": "vessels",
    "ship": "vessels",
    "ships": "vessels",
    "seismic": "seismic",
    "earthquakes": "seismic",
    "quakes": "seismic",
    "volcanic": "volcanic",
    "volcanoes": "volcanic",
    "weather": "weather",
    "grid": "grid",
    "terrain": "terrain",
}

# Direction normalization
DIRECTION_MAP = {
    "left": "left",
    "right": "right",
    "up": "up",
    "down": "down",
    "north": "up",
    "south": "down",
    "east": "right",
    "west": "left",
}


class MapVoiceHandler:
    """Handles map-related voice commands."""
    
    def __init__(self):
        self._compiled_patterns = self._compile_patterns()
    
    def _compile_patterns(self) -> Dict[MapIntent, List[re.Pattern]]:
        """Pre-compile regex patterns."""
        compiled = {}
        for intent, patterns in MAP_PATTERNS.items():
            compiled[intent] = [re.compile(p, re.IGNORECASE) for p in patterns]
        return compiled
    
    def parse_command(self, text: str) -> MapCommand:
        """Parse voice text into a map command."""
        text = text.strip().lower()
        
        for intent, patterns in self._compiled_patterns.items():
            for pattern in patterns:
                match = pattern.search(text)
                if match:
                    return self._build_command(intent, text, match)
        
        return MapCommand(
            intent=MapIntent.UNKNOWN,
            raw_text=text,
            confidence=0.0
        )
    
    def _build_command(self, intent: MapIntent, text: str, match: re.Match) -> MapCommand:
        """Build a command from matched pattern."""
        cmd = MapCommand(
            intent=intent,
            raw_text=text,
            confidence=0.85
        )
        
        if intent == MapIntent.NAVIGATE:
            location = match.group(1).strip() if match.groups() else None
            if location:
                cmd.location = location
                # Check known locations
                loc_lower = location.lower()
                if loc_lower in KNOWN_LOCATIONS:
                    cmd.coordinates = KNOWN_LOCATIONS[loc_lower]
        
        elif intent == MapIntent.ZOOM:
            groups = match.groups()
            if groups:
                first_group = groups[0]
                if first_group:
                    if first_group.isdigit():
                        cmd.zoom_level = int(first_group)
                    elif first_group in ("in", "out"):
                        cmd.zoom_direction = first_group
                    elif first_group in ("back", "away"):
                        cmd.zoom_direction = "out"
            
            # Check for zoom modifiers
            if "closer" in text or "magnify" in text or "enlarge" in text:
                cmd.zoom_direction = "in"
        
        elif intent == MapIntent.PAN:
            groups = match.groups()
            if groups and groups[0]:
                direction = groups[0].lower()
                cmd.pan_direction = DIRECTION_MAP.get(direction, direction)
        
        elif intent == MapIntent.LAYER:
            groups = match.groups()
            if groups and groups[0]:
                layer_raw = groups[0].lower()
                cmd.layer = CREP_LAYER_ALIASES.get(layer_raw, layer_raw)
            
            # Determine action
            if any(word in text for word in ["show", "display", "turn on", "enable", "activate"]):
                cmd.layer_action = "show"
            elif any(word in text for word in ["hide", "remove", "turn off", "disable", "deactivate"]):
                cmd.layer_action = "hide"
            elif "toggle" in text:
                cmd.layer_action = "toggle"
        
        elif intent == MapIntent.CREP_FILTER:
            if "clear" in text:
                cmd.filter_type = "clear"
            else:
                groups = match.groups()
                if len(groups) >= 2:
                    cmd.filter_type = groups[0]
                    cmd.filter_value = groups[1]
                elif len(groups) >= 1:
                    # Handle "show only seismic events" pattern
                    cmd.filter_value = groups[0]
        
        elif intent == MapIntent.CREP_ENTITY:
            groups = match.groups()
            if groups and groups[0]:
                cmd.entity_name = groups[0].strip()
        
        return cmd
    
    def execute_command(self, cmd: MapCommand) -> Dict[str, Any]:
        """Execute a map command and return frontend instructions."""
        try:
            if cmd.intent == MapIntent.NAVIGATE:
                return self._navigate(cmd)
            elif cmd.intent == MapIntent.ZOOM:
                return self._zoom(cmd)
            elif cmd.intent == MapIntent.PAN:
                return self._pan(cmd)
            elif cmd.intent == MapIntent.LAYER:
                return self._toggle_layer(cmd)
            elif cmd.intent == MapIntent.RESET:
                return self._reset_view(cmd)
            elif cmd.intent == MapIntent.CREP_FILTER:
                return self._apply_filter(cmd)
            elif cmd.intent == MapIntent.CREP_ENTITY:
                return self._query_entity(cmd)
            elif cmd.intent == MapIntent.WHAT_HERE:
                return self._describe_view(cmd)
            else:
                return {"success": False, "error": "Unknown intent"}
        except Exception as e:
            logger.error(f"Map command execution failed: {e}")
            return {"success": False, "error": str(e)}
    
    def _navigate(self, cmd: MapCommand) -> Dict[str, Any]:
        """Navigate to a location."""
        if cmd.coordinates:
            lat, lng = cmd.coordinates
            return {
                "success": True,
                "action": "navigate",
                "location": cmd.location,
                "frontend_command": {
                    "type": "flyTo",
                    "center": [lng, lat],
                    "zoom": 8,
                    "duration": 2000
                },
                "speak": f"Flying to {cmd.location}."
            }
        elif cmd.location:
            # Need geocoding - pass to frontend
            return {
                "success": True,
                "action": "navigate",
                "location": cmd.location,
                "frontend_command": {
                    "type": "geocodeAndFlyTo",
                    "query": cmd.location,
                    "zoom": 8,
                    "duration": 2000
                },
                "speak": f"Navigating to {cmd.location}."
            }
        else:
            return {"success": False, "error": "No location specified"}
    
    def _zoom(self, cmd: MapCommand) -> Dict[str, Any]:
        """Zoom in or out."""
        if cmd.zoom_level:
            return {
                "success": True,
                "action": "zoom",
                "frontend_command": {
                    "type": "setZoom",
                    "zoom": cmd.zoom_level,
                    "duration": 500
                },
                "speak": f"Setting zoom level to {cmd.zoom_level}."
            }
        elif cmd.zoom_direction:
            delta = 2 if cmd.zoom_direction == "in" else -2
            action_word = "in" if delta > 0 else "out"
            return {
                "success": True,
                "action": "zoom",
                "frontend_command": {
                    "type": "zoomBy",
                    "delta": delta,
                    "duration": 500
                },
                "speak": f"Zooming {action_word}."
            }
        else:
            return {"success": False, "error": "No zoom direction specified"}
    
    def _pan(self, cmd: MapCommand) -> Dict[str, Any]:
        """Pan the map."""
        direction = cmd.pan_direction
        if not direction:
            return {"success": False, "error": "No pan direction specified"}
        
        # Convert direction to pixel offset
        offsets = {
            "left": [-200, 0],
            "right": [200, 0],
            "up": [0, -200],
            "down": [0, 200],
        }
        
        offset = offsets.get(direction, [0, 0])
        
        return {
            "success": True,
            "action": "pan",
            "frontend_command": {
                "type": "panBy",
                "offset": offset,
                "duration": 300
            },
            "speak": f"Panning {direction}."
        }
    
    def _toggle_layer(self, cmd: MapCommand) -> Dict[str, Any]:
        """Toggle a map layer."""
        layer = cmd.layer or "unknown"
        action = cmd.layer_action or "toggle"
        
        return {
            "success": True,
            "action": f"{action}_layer",
            "layer": layer,
            "frontend_command": {
                "type": f"{action}Layer",
                "layer": layer
            },
            "speak": f"{'Showing' if action == 'show' else 'Hiding' if action == 'hide' else 'Toggling'} {layer} layer."
        }
    
    def _reset_view(self, cmd: MapCommand) -> Dict[str, Any]:
        """Reset to global view."""
        return {
            "success": True,
            "action": "reset",
            "frontend_command": {
                "type": "flyTo",
                "center": [0, 20],
                "zoom": 2,
                "duration": 2000
            },
            "speak": "Resetting to global view."
        }
    
    def _apply_filter(self, cmd: MapCommand) -> Dict[str, Any]:
        """Apply CREP data filter."""
        if cmd.filter_type == "clear":
            return {
                "success": True,
                "action": "clear_filters",
                "frontend_command": {
                    "type": "clearFilters"
                },
                "speak": "Clearing all filters."
            }
        else:
            return {
                "success": True,
                "action": "apply_filter",
                "filter_type": cmd.filter_type,
                "filter_value": cmd.filter_value,
                "frontend_command": {
                    "type": "applyFilter",
                    "filterType": cmd.filter_type,
                    "filterValue": cmd.filter_value
                },
                "speak": f"Filtering by {cmd.filter_type}: {cmd.filter_value}."
            }
    
    def _query_entity(self, cmd: MapCommand) -> Dict[str, Any]:
        """Query information about an entity."""
        return {
            "success": True,
            "action": "query_entity",
            "entity": cmd.entity_name,
            "needs_context": True,
            "frontend_command": {
                "type": "getEntityDetails",
                "entity": cmd.entity_name
            },
            "speak": f"Let me look up information about {cmd.entity_name or 'that'}."
        }
    
    def _describe_view(self, cmd: MapCommand) -> Dict[str, Any]:
        """Describe the current map view."""
        return {
            "success": True,
            "action": "describe_view",
            "needs_context": True,
            "frontend_command": {
                "type": "getViewContext"
            },
            "speak": "Let me describe what's currently visible on the map."
        }


# Singleton instance
_handler: Optional[MapVoiceHandler] = None


def get_map_handler() -> MapVoiceHandler:
    """Get or create the map voice handler singleton."""
    global _handler
    if _handler is None:
        _handler = MapVoiceHandler()
    return _handler


def process_map_voice(text: str) -> Dict[str, Any]:
    """
    Process a voice command for map navigation.
    
    Returns:
        Dict with:
        - success: bool
        - action: str (the action taken)
        - speak: str (what MYCA should say)
        - frontend_command: dict (command for frontend)
    """
    handler = get_map_handler()
    cmd = handler.parse_command(text)
    
    if cmd.intent == MapIntent.UNKNOWN:
        return {
            "success": False,
            "matched": False,
            "error": "Not a map command"
        }
    
    result = handler.execute_command(cmd)
    result["matched"] = True
    result["intent"] = cmd.intent.value
    return result


def is_map_command(text: str) -> bool:
    """Quick check if text might be a map command."""
    handler = get_map_handler()
    cmd = handler.parse_command(text)
    return cmd.intent != MapIntent.UNKNOWN
