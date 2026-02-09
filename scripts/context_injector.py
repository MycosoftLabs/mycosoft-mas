"""
Context Injector for PersonaPlex Voice Bridge - February 5, 2026

Injects map and Earth2 context into voice commands to enable
MYCA to understand and respond to spatial and weather queries.

This module should be imported by the PersonaPlex bridge:
    from scripts.context_injector import ContextInjector

The injector maintains current state about:
- Map viewport (center, zoom, bounds)
- Active CREP layers and visible entities
- Earth2 model state and active forecasts
- Recent conversation context
"""

import logging
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


@dataclass
class MapViewport:
    """Current map viewport state."""
    center: Tuple[float, float]  # [lng, lat]
    zoom: float
    bearing: float = 0.0
    pitch: float = 0.0
    bounds: Optional[Tuple[Tuple[float, float], Tuple[float, float]]] = None  # [[sw], [ne]]


@dataclass
class CREPContext:
    """CREP dashboard context."""
    active_layers: List[str] = field(default_factory=list)
    visible_entities: List[Dict[str, Any]] = field(default_factory=list)
    active_filters: Dict[str, Any] = field(default_factory=dict)
    selected_entity: Optional[Dict[str, Any]] = None


@dataclass
class Earth2Context:
    """Earth2 weather model context."""
    active_model: Optional[str] = None
    loaded_models: List[str] = field(default_factory=list)
    active_layers: List[str] = field(default_factory=list)
    last_forecast: Optional[Dict[str, Any]] = None
    gpu_memory_used_gb: float = 0.0
    gpu_memory_total_gb: float = 32.0


@dataclass
class ConversationContext:
    """Recent conversation context."""
    recent_topics: List[str] = field(default_factory=list)
    last_command_domain: Optional[str] = None
    last_command_action: Optional[str] = None
    mentioned_locations: List[str] = field(default_factory=list)
    mentioned_entities: List[str] = field(default_factory=list)


@dataclass
class FullContext:
    """Complete context for voice command processing."""
    map: Optional[MapViewport] = None
    crep: Optional[CREPContext] = None
    earth2: Optional[Earth2Context] = None
    conversation: Optional[ConversationContext] = None
    timestamp: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = {"timestamp": self.timestamp or datetime.utcnow().isoformat()}
        
        if self.map:
            result["map"] = {
                "center": self.map.center,
                "zoom": self.map.zoom,
                "bearing": self.map.bearing,
                "pitch": self.map.pitch,
                "bounds": self.map.bounds,
            }
        
        if self.crep:
            result["crep"] = {
                "active_layers": self.crep.active_layers,
                "visible_entities": self.crep.visible_entities,
                "active_filters": self.crep.active_filters,
                "selected_entity": self.crep.selected_entity,
            }
        
        if self.earth2:
            result["earth2"] = {
                "active_model": self.earth2.active_model,
                "loaded_models": self.earth2.loaded_models,
                "active_layers": self.earth2.active_layers,
                "last_forecast": self.earth2.last_forecast,
                "gpu_memory_used_gb": self.earth2.gpu_memory_used_gb,
                "gpu_memory_total_gb": self.earth2.gpu_memory_total_gb,
            }
        
        if self.conversation:
            result["conversation"] = {
                "recent_topics": self.conversation.recent_topics,
                "last_command_domain": self.conversation.last_command_domain,
                "last_command_action": self.conversation.last_command_action,
                "mentioned_locations": self.conversation.mentioned_locations,
                "mentioned_entities": self.conversation.mentioned_entities,
            }
        
        return result


class ContextInjector:
    """
    Injects context into voice commands for MYCA.
    
    Maintains state about the current map view, CREP data,
    and Earth2 weather models to provide rich context
    for voice command interpretation.
    """
    
    def __init__(self):
        self.map_viewport: Optional[MapViewport] = None
        self.crep_context: CREPContext = CREPContext()
        self.earth2_context: Earth2Context = Earth2Context()
        self.conversation_context: ConversationContext = ConversationContext()
        
        # History for context window
        self._command_history: List[Dict[str, Any]] = []
        self._max_history = 10
    
    def update_map_context(
        self,
        center: Tuple[float, float],
        zoom: float,
        bearing: float = 0.0,
        pitch: float = 0.0,
        bounds: Optional[Tuple[Tuple[float, float], Tuple[float, float]]] = None
    ) -> None:
        """Update map viewport context."""
        self.map_viewport = MapViewport(
            center=center,
            zoom=zoom,
            bearing=bearing,
            pitch=pitch,
            bounds=bounds
        )
        logger.debug(f"Updated map context: center={center}, zoom={zoom}")
    
    def update_crep_layers(self, layers: List[str]) -> None:
        """Update active CREP layers."""
        self.crep_context.active_layers = layers
    
    def update_crep_entities(self, entities: List[Dict[str, Any]]) -> None:
        """Update visible CREP entities."""
        self.crep_context.visible_entities = entities
    
    def update_crep_filters(self, filters: Dict[str, Any]) -> None:
        """Update active CREP filters."""
        self.crep_context.active_filters = filters
    
    def set_selected_entity(self, entity: Optional[Dict[str, Any]]) -> None:
        """Set the currently selected CREP entity."""
        self.crep_context.selected_entity = entity
        
        # Track mentioned entities
        if entity and "name" in entity:
            self._add_mentioned_entity(entity["name"])
    
    def update_earth2_context(
        self,
        active_model: Optional[str] = None,
        loaded_models: Optional[List[str]] = None,
        active_layers: Optional[List[str]] = None,
        last_forecast: Optional[Dict[str, Any]] = None,
        gpu_memory_used_gb: Optional[float] = None
    ) -> None:
        """Update Earth2 context."""
        if active_model is not None:
            self.earth2_context.active_model = active_model
        if loaded_models is not None:
            self.earth2_context.loaded_models = loaded_models
        if active_layers is not None:
            self.earth2_context.active_layers = active_layers
        if last_forecast is not None:
            self.earth2_context.last_forecast = last_forecast
        if gpu_memory_used_gb is not None:
            self.earth2_context.gpu_memory_used_gb = gpu_memory_used_gb
    
    def record_command(
        self,
        domain: str,
        action: str,
        success: bool,
        raw_text: str
    ) -> None:
        """Record a processed command for conversation context."""
        command = {
            "domain": domain,
            "action": action,
            "success": success,
            "raw_text": raw_text,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        self._command_history.append(command)
        if len(self._command_history) > self._max_history:
            self._command_history.pop(0)
        
        # Update conversation context
        self.conversation_context.last_command_domain = domain
        self.conversation_context.last_command_action = action
        
        # Extract topics from text
        self._extract_topics(raw_text)
    
    def _extract_topics(self, text: str) -> None:
        """Extract topics from voice command text."""
        text_lower = text.lower()
        
        # Weather topics
        weather_topics = ["forecast", "weather", "temperature", "wind", "precipitation", "storm"]
        for topic in weather_topics:
            if topic in text_lower and topic not in self.conversation_context.recent_topics:
                self.conversation_context.recent_topics.append(topic)
        
        # Location detection (basic)
        # In production, this would use NER or geocoding
        location_indicators = ["in ", "at ", "near ", "around ", "to "]
        for indicator in location_indicators:
            if indicator in text_lower:
                idx = text_lower.find(indicator)
                remaining = text[idx + len(indicator):]
                # Take first few words as potential location
                words = remaining.split()[:3]
                potential_location = " ".join(words).strip(".,!?")
                if potential_location and potential_location not in self.conversation_context.mentioned_locations:
                    self.conversation_context.mentioned_locations.append(potential_location)
        
        # Limit recent topics
        self.conversation_context.recent_topics = self.conversation_context.recent_topics[-10:]
        self.conversation_context.mentioned_locations = self.conversation_context.mentioned_locations[-5:]
    
    def _add_mentioned_entity(self, entity_name: str) -> None:
        """Track a mentioned entity."""
        if entity_name not in self.conversation_context.mentioned_entities:
            self.conversation_context.mentioned_entities.append(entity_name)
            self.conversation_context.mentioned_entities = self.conversation_context.mentioned_entities[-5:]
    
    def get_full_context(self) -> FullContext:
        """Get the full context for voice command processing."""
        return FullContext(
            map=self.map_viewport,
            crep=self.crep_context,
            earth2=self.earth2_context,
            conversation=self.conversation_context,
            timestamp=datetime.utcnow().isoformat()
        )
    
    def get_context_dict(self) -> Dict[str, Any]:
        """Get context as a dictionary."""
        return self.get_full_context().to_dict()
    
    def build_system_prompt_context(self) -> str:
        """
        Build a context string for injection into system prompts.
        
        This provides MYCA with awareness of the current state
        when generating responses.
        """
        parts = []
        
        # Map context
        if self.map_viewport:
            lng, lat = self.map_viewport.center
            parts.append(f"Map is currently centered at ({lat:.4f}, {lng:.4f}) at zoom level {self.map_viewport.zoom:.1f}.")
            
            if self.map_viewport.bounds:
                sw, ne = self.map_viewport.bounds
                parts.append(f"Visible area spans from ({sw[1]:.2f}, {sw[0]:.2f}) to ({ne[1]:.2f}, {ne[0]:.2f}).")
        
        # CREP context
        if self.crep_context.active_layers:
            parts.append(f"Active data layers: {', '.join(self.crep_context.active_layers)}.")
        
        if self.crep_context.visible_entities:
            count = len(self.crep_context.visible_entities)
            parts.append(f"Currently showing {count} entities on the map.")
        
        if self.crep_context.selected_entity:
            entity = self.crep_context.selected_entity
            entity_type = entity.get("type", "entity")
            entity_name = entity.get("name", "unknown")
            parts.append(f"User has selected a {entity_type} named '{entity_name}'.")
        
        # Earth2 context
        if self.earth2_context.active_model:
            parts.append(f"Weather model '{self.earth2_context.active_model}' is currently active.")
        
        if self.earth2_context.active_layers:
            parts.append(f"Weather layers visible: {', '.join(self.earth2_context.active_layers)}.")
        
        if self.earth2_context.last_forecast:
            forecast = self.earth2_context.last_forecast
            lead_time = forecast.get("lead_time", "unknown")
            parts.append(f"Last forecast was a {lead_time}-hour prediction.")
        
        # Conversation context
        if self.conversation_context.mentioned_locations:
            locs = self.conversation_context.mentioned_locations[-3:]
            parts.append(f"Recently mentioned locations: {', '.join(locs)}.")
        
        if self.conversation_context.recent_topics:
            topics = self.conversation_context.recent_topics[-5:]
            parts.append(f"Recent topics: {', '.join(topics)}.")
        
        return "\n".join(parts) if parts else ""
    
    def build_context_for_llm(self) -> str:
        """
        Build a complete context block for LLM prompts.
        
        Returns a formatted string suitable for injection into
        the system prompt or as a context message.
        """
        header = "=== Current Context ==="
        context = self.build_system_prompt_context()
        footer = "=== End Context ==="
        
        if context:
            return f"{header}\n{context}\n{footer}"
        return ""
    
    def clear(self) -> None:
        """Clear all context."""
        self.map_viewport = None
        self.crep_context = CREPContext()
        self.earth2_context = Earth2Context()
        self.conversation_context = ConversationContext()
        self._command_history.clear()


# Singleton instance
_injector: Optional[ContextInjector] = None


def get_context_injector() -> ContextInjector:
    """Get or create the context injector singleton."""
    global _injector
    if _injector is None:
        _injector = ContextInjector()
    return _injector


# Convenience functions
def update_map_context(
    center: Tuple[float, float],
    zoom: float,
    **kwargs
) -> None:
    """Update map context on the singleton."""
    get_context_injector().update_map_context(center, zoom, **kwargs)


def update_earth2_context(**kwargs) -> None:
    """Update Earth2 context on the singleton."""
    get_context_injector().update_earth2_context(**kwargs)


def get_llm_context() -> str:
    """Get formatted context for LLM prompts."""
    return get_context_injector().build_context_for_llm()


def get_context_dict() -> Dict[str, Any]:
    """Get context as dictionary."""
    return get_context_injector().get_context_dict()
