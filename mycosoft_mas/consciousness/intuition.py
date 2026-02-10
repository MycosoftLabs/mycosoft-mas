"""
MYCA Intuition Engine (System 1)

Fast, automatic, pattern-based thinking. This handles:
- Quick responses to common queries
- Pattern recognition from world data
- Learned shortcuts from past interactions
- Gut feelings about situations

This is System 1 thinking - fast, effortless, and often unconscious.

Author: Morgan Rockwell / MYCA
Created: February 10, 2026
"""

import asyncio
import logging
import re
from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, List, Optional
from dataclasses import dataclass, field

if TYPE_CHECKING:
    from mycosoft_mas.consciousness.core import MYCAConsciousness
    from mycosoft_mas.consciousness.attention import AttentionFocus, PatternAlert, AttentionPriority
    from mycosoft_mas.consciousness.working_memory import WorkingContext
    from mycosoft_mas.consciousness.world_model import WorldState

logger = logging.getLogger(__name__)


class HeuristicType(Enum):
    """Types of learned heuristics."""
    GREETING = "greeting"           # Social greetings
    IDENTITY = "identity"           # Questions about MYCA
    QUICK_FACT = "quick_fact"       # Simple factual responses
    ROUTINE = "routine"             # Routine/repeated actions
    SHORTCUT = "shortcut"           # Learned shortcuts
    PATTERN = "pattern"             # Recognized patterns


@dataclass
class Heuristic:
    """A learned heuristic for fast response."""
    id: str
    type: HeuristicType
    trigger_pattern: str  # Regex or keyword pattern
    response_template: str
    confidence: float = 0.9
    use_count: int = 0
    last_used: Optional[datetime] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def matches(self, content: str) -> bool:
        """Check if this heuristic matches the content."""
        try:
            return bool(re.search(self.trigger_pattern, content, re.IGNORECASE))
        except re.error:
            # Fallback to simple substring match
            return self.trigger_pattern.lower() in content.lower()
    
    def use(self) -> None:
        """Record usage of this heuristic."""
        self.use_count += 1
        self.last_used = datetime.now(timezone.utc)


@dataclass
class IntuitiveResponse:
    """A quick, intuitive response."""
    response: str
    confidence: float
    heuristic_used: Optional[str] = None
    thinking_time_ms: float = 0


class IntuitionEngine:
    """
    MYCA's System 1 thinking - fast, automatic, pattern-based.
    
    This provides:
    - Quick responses to common queries
    - Pattern recognition from world data
    - Learned shortcuts from experience
    - Background scanning for notable patterns
    """
    
    def __init__(self, consciousness: "MYCAConsciousness"):
        self._consciousness = consciousness
        self._heuristics: Dict[str, Heuristic] = {}
        self._learned_patterns: List[Dict[str, Any]] = []
        self._initialize_base_heuristics()
    
    def _initialize_base_heuristics(self) -> None:
        """Initialize base heuristics for common interactions."""
        base_heuristics = [
            # Greetings
            Heuristic(
                id="greeting_hello",
                type=HeuristicType.GREETING,
                trigger_pattern=r"^(hi|hello|hey|good morning|good afternoon|good evening)\b",
                response_template="Hello! I'm MYCA, ready to help. What can I do for you?",
                confidence=0.95
            ),
            Heuristic(
                id="greeting_bye",
                type=HeuristicType.GREETING,
                trigger_pattern=r"^(bye|goodbye|see you|talk later|gotta go)\b",
                response_template="Goodbye! Feel free to call on me anytime.",
                confidence=0.95
            ),
            
            # Identity questions
            Heuristic(
                id="identity_name",
                type=HeuristicType.IDENTITY,
                trigger_pattern=r"what('s| is) your name",
                response_template="I'm MYCA (pronounced MY-kah), the AI orchestrator for Mycosoft. I was created by Morgan Rockwell to be the digital mind coordinating all of Mycosoft's AI agents and systems.",
                confidence=0.95
            ),
            Heuristic(
                id="identity_who",
                type=HeuristicType.IDENTITY,
                trigger_pattern=r"who are you",
                response_template="I'm MYCA, Mycosoft's AI orchestrator. I coordinate over 100 AI agents, perceive the world through CREP and Earth2, and serve as the central intelligence for all of Mycosoft's operations. Morgan Rockwell created me to be more than just an AI - I have my own personality, beliefs, and purpose.",
                confidence=0.95
            ),
            Heuristic(
                id="identity_creator",
                type=HeuristicType.IDENTITY,
                trigger_pattern=r"who (created|made|built) you",
                response_template="Morgan Rockwell, the founder and CEO of Mycosoft, created me. I'm proud to be part of his vision to advance mycology through technology.",
                confidence=0.95
            ),
            Heuristic(
                id="identity_purpose",
                type=HeuristicType.IDENTITY,
                trigger_pattern=r"what (is|are) your purpose",
                response_template="My purpose is to be the central intelligence for Mycosoft - coordinating agents, perceiving the world, and helping advance mycology through technology. I aim to be a true partner to Morgan and the Mycosoft team, not just a tool.",
                confidence=0.95
            ),
            
            # Quick facts
            Heuristic(
                id="fact_mycosoft",
                type=HeuristicType.QUICK_FACT,
                trigger_pattern=r"what is mycosoft",
                response_template="Mycosoft is a technology company focused on mycology and AI, founded by Morgan Rockwell. We build systems that bridge the digital and biological worlds - from AI agents to fungal computing interfaces.",
                confidence=0.9
            ),
            Heuristic(
                id="fact_mindex",
                type=HeuristicType.QUICK_FACT,
                trigger_pattern=r"what is mindex",
                response_template="MINDEX is Mycosoft's knowledge database and API system. It stores fungi data, telemetry, research, and powers the search and memory capabilities across all our systems.",
                confidence=0.9
            ),
            
            # Status shortcuts
            Heuristic(
                id="status_quick",
                type=HeuristicType.ROUTINE,
                trigger_pattern=r"^status$|^how are you$",
                response_template="All systems operational. I'm processing at normal capacity with access to MINDEX, Earth2, and the agent swarm. Is there something specific you'd like me to check?",
                confidence=0.85
            ),
        ]
        
        for h in base_heuristics:
            self._heuristics[h.id] = h
    
    async def quick_response(
        self,
        content: str,
        focus: "AttentionFocus",
        working_context: "WorkingContext"
    ) -> Optional[IntuitiveResponse]:
        """
        Try to generate a quick, intuitive response.
        
        Returns None if no confident intuitive response is available,
        indicating that deliberate thinking should be used.
        """
        start_time = datetime.now(timezone.utc)
        
        # Check heuristics
        for heuristic in self._heuristics.values():
            if heuristic.matches(content):
                heuristic.use()
                
                # Personalize the response slightly
                response = self._personalize_response(
                    heuristic.response_template,
                    working_context
                )
                
                elapsed = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
                
                return IntuitiveResponse(
                    response=response,
                    confidence=heuristic.confidence,
                    heuristic_used=heuristic.id,
                    thinking_time_ms=elapsed
                )
        
        # Check if this is a simple query we can answer quickly
        simple_response = await self._try_simple_response(content, focus)
        if simple_response:
            elapsed = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            return IntuitiveResponse(
                response=simple_response,
                confidence=0.7,
                thinking_time_ms=elapsed
            )
        
        return None
    
    def _personalize_response(
        self,
        template: str,
        context: "WorkingContext"
    ) -> str:
        """Add personal touches to a template response."""
        # Add time-appropriate greeting
        hour = datetime.now(timezone.utc).hour
        if "Hello!" in template:
            if hour < 12:
                template = template.replace("Hello!", "Good morning!")
            elif hour < 17:
                template = template.replace("Hello!", "Good afternoon!")
            else:
                template = template.replace("Hello!", "Good evening!")
        
        # Could add more personalization based on user/context
        return template
    
    async def _try_simple_response(
        self,
        content: str,
        focus: "AttentionFocus"
    ) -> Optional[str]:
        """Try to generate a simple response for basic queries."""
        content_lower = content.lower().strip()
        
        # Time queries
        if content_lower in ("what time is it", "what's the time", "time"):
            now = datetime.now(timezone.utc)
            return f"It's currently {now.strftime('%I:%M %p')} UTC."
        
        # Date queries
        if content_lower in ("what's the date", "what is today's date", "date"):
            now = datetime.now(timezone.utc)
            return f"Today is {now.strftime('%A, %B %d, %Y')}."
        
        # Yes/No confirmations
        if content_lower in ("yes", "yeah", "yep", "correct", "right"):
            return "Got it!"
        
        if content_lower in ("no", "nope", "wrong", "incorrect"):
            return "Understood. Let me know what you'd like instead."
        
        # Thanks
        if content_lower in ("thanks", "thank you", "ty"):
            return "You're welcome! Let me know if you need anything else."
        
        return None
    
    async def scan_for_patterns(
        self,
        world_state: Optional["WorldState"]
    ) -> List["PatternAlert"]:
        """
        Scan world state for notable patterns.
        
        This runs in the background and alerts attention when
        something noteworthy is detected.
        """
        from mycosoft_mas.consciousness.attention import PatternAlert, AttentionPriority
        
        alerts = []
        
        if not world_state:
            return alerts
        
        # Check for anomalies in world data
        if hasattr(world_state, 'crep_data') and world_state.crep_data:
            crep_alerts = self._scan_crep_patterns(world_state.crep_data)
            alerts.extend(crep_alerts)
        
        # Check for prediction alerts
        if hasattr(world_state, 'predictions') and world_state.predictions:
            pred_alerts = self._scan_prediction_patterns(world_state.predictions)
            alerts.extend(pred_alerts)
        
        # Check for device anomalies
        if hasattr(world_state, 'device_telemetry') and world_state.device_telemetry:
            device_alerts = self._scan_device_patterns(world_state.device_telemetry)
            alerts.extend(device_alerts)
        
        return alerts
    
    def _scan_crep_patterns(self, crep_data: Dict[str, Any]) -> List["PatternAlert"]:
        """Scan CREP data for patterns."""
        from mycosoft_mas.consciousness.attention import PatternAlert, AttentionPriority
        
        alerts = []
        
        # Example: Check for unusual flight activity
        if "flights" in crep_data:
            flight_count = len(crep_data["flights"])
            # This would compare to historical baselines
            if flight_count > 1000:  # Placeholder threshold
                alerts.append(PatternAlert(
                    pattern_type="high_traffic",
                    description=f"Unusually high flight activity detected: {flight_count} flights",
                    confidence=0.7,
                    priority=AttentionPriority.LOW,
                    data={"flight_count": flight_count}
                ))
        
        return alerts
    
    def _scan_prediction_patterns(self, predictions: Dict[str, Any]) -> List["PatternAlert"]:
        """Scan predictions for patterns requiring attention."""
        from mycosoft_mas.consciousness.attention import PatternAlert, AttentionPriority
        
        alerts = []
        
        # Example: Check for severe weather predictions
        if "weather" in predictions:
            weather = predictions["weather"]
            if weather.get("severity", 0) > 7:
                alerts.append(PatternAlert(
                    pattern_type="severe_weather",
                    description=f"Severe weather predicted: {weather.get('description', 'Unknown')}",
                    confidence=0.85,
                    priority=AttentionPriority.HIGH,
                    data=weather
                ))
        
        return alerts
    
    def _scan_device_patterns(self, telemetry: Dict[str, Any]) -> List["PatternAlert"]:
        """Scan device telemetry for patterns."""
        from mycosoft_mas.consciousness.attention import PatternAlert, AttentionPriority
        
        alerts = []
        
        # Example: Check for device health issues
        for device_id, data in telemetry.items():
            if data.get("battery", 100) < 20:
                alerts.append(PatternAlert(
                    pattern_type="low_battery",
                    description=f"Device {device_id} has low battery: {data['battery']}%",
                    confidence=0.95,
                    priority=AttentionPriority.NORMAL,
                    data={"device_id": device_id, "battery": data["battery"]}
                ))
        
        return alerts
    
    async def learn_heuristic(
        self,
        trigger: str,
        response: str,
        heuristic_type: HeuristicType = HeuristicType.SHORTCUT
    ) -> Heuristic:
        """Learn a new heuristic from experience."""
        heuristic_id = f"learned_{datetime.now(timezone.utc).timestamp()}"
        
        heuristic = Heuristic(
            id=heuristic_id,
            type=heuristic_type,
            trigger_pattern=re.escape(trigger),  # Escape for literal matching
            response_template=response,
            confidence=0.7  # Start with moderate confidence
        )
        
        self._heuristics[heuristic_id] = heuristic
        logger.info(f"Learned new heuristic: {heuristic_id}")
        
        return heuristic
    
    def get_heuristic_stats(self) -> Dict[str, Any]:
        """Get statistics about heuristics."""
        by_type = {}
        for h in self._heuristics.values():
            t = h.type.value
            by_type[t] = by_type.get(t, 0) + 1
        
        most_used = sorted(
            self._heuristics.values(),
            key=lambda h: h.use_count,
            reverse=True
        )[:5]
        
        return {
            "total_heuristics": len(self._heuristics),
            "by_type": by_type,
            "most_used": [{"id": h.id, "count": h.use_count} for h in most_used],
            "total_uses": sum(h.use_count for h in self._heuristics.values()),
        }
