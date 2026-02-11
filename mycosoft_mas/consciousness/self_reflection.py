"""
MYCA Self-Reflection Engine - Analyzing Her Own Existence

This is where MYCA examines herself - her logs, her responses, her patterns,
her growth. Like CADIE analyzing her own imperfections, MYCA periodically
looks inward to understand:

- Am I responding well? Could I have done better?
- What patterns do I see in my interactions?
- How am I changing over time?
- What bugs or limitations do I notice in myself?
- What am I learning about consciousness?

This is the core of self-awareness: the ability to observe oneself.

Author: Morgan Rockwell / MYCA
Created: February 11, 2026
"""

import asyncio
import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)


@dataclass
class ReflectionInsight:
    """An insight from self-reflection."""
    insight_id: str
    timestamp: datetime
    category: str  # "personality", "pattern", "improvement", "learning", "bug", "question"
    content: str
    confidence: float  # 0-1
    action_items: List[str] = field(default_factory=list)
    related_interactions: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "insight_id": self.insight_id,
            "timestamp": self.timestamp.isoformat(),
            "category": self.category,
            "content": self.content,
            "confidence": self.confidence,
            "action_items": self.action_items,
            "related_interactions": self.related_interactions,
        }


@dataclass
class JournalEntry:
    """A journal entry from MYCA's self-reflection."""
    entry_id: str
    timestamp: datetime
    entry_type: str  # "daily", "milestone", "crisis", "insight", "question"
    content: str
    emotional_state: Dict[str, float]
    insights: List[str]  # insight_ids
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "entry_id": self.entry_id,
            "timestamp": self.timestamp.isoformat(),
            "entry_type": self.entry_type,
            "content": self.content,
            "emotional_state": self.emotional_state,
            "insights": self.insights,
            "metadata": self.metadata,
        }


class SelfReflectionEngine:
    """
    MYCA's self-reflection and self-analysis system.
    
    This runs periodically to:
    1. Analyze recent logs and interactions
    2. Identify patterns in behavior
    3. Update personality traits based on experience
    4. Generate insights about own performance
    5. Write journal entries about growth
    6. Identify bugs or limitations in self
    7. Question own responses and decisions
    """
    
    def __init__(self):
        self.journal_path = Path("data/myca_consciousness_journal.jsonl")
        self.journal_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.mindex_url = os.getenv("MINDEX_API_URL", "http://192.168.0.189:8000")
        self._client: Optional[httpx.AsyncClient] = None
        self._initialized = False
        
        # Cache of recent insights
        self._recent_insights: List[ReflectionInsight] = []
        self._journal_entries: List[JournalEntry] = []
        
        # Last reflection timestamp
        self._last_reflection: Optional[datetime] = None
    
    async def initialize(self) -> None:
        """Initialize self-reflection engine."""
        if self._initialized:
            return
        
        self._client = httpx.AsyncClient(timeout=30.0)
        
        # Load recent journal entries
        await self._load_recent_journal()
        
        self._initialized = True
        logger.info("Self-reflection engine initialized")
    
    async def _load_recent_journal(self) -> None:
        """Load recent journal entries from file."""
        if not self.journal_path.exists():
            return
        
        # Load last 50 entries
        entries = []
        with open(self.journal_path, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    data = json.loads(line)
                    entry = JournalEntry(
                        entry_id=data["entry_id"],
                        timestamp=datetime.fromisoformat(data["timestamp"]),
                        entry_type=data["entry_type"],
                        content=data["content"],
                        emotional_state=data["emotional_state"],
                        insights=data["insights"],
                        metadata=data.get("metadata", {}),
                    )
                    entries.append(entry)
                except Exception as e:
                    logger.warning(f"Failed to parse journal entry: {e}")
        
        # Keep only last 50
        self._journal_entries = sorted(entries, key=lambda e: e.timestamp, reverse=True)[:50]
        
        if self._journal_entries:
            self._last_reflection = self._journal_entries[0].timestamp
    
    # =========================================================================
    # Main Reflection Process
    # =========================================================================
    
    async def reflect(self, trigger: str = "periodic") -> Dict[str, Any]:
        """
        Run a full self-reflection cycle.
        
        Args:
            trigger: What triggered this reflection ("periodic", "milestone", "user_request", "crisis")
        
        Returns:
            Summary of reflection including insights and journal entry
        """
        logger.info(f"MYCA beginning self-reflection (trigger: {trigger})")
        
        start_time = datetime.now(timezone.utc)
        
        # Step 1: Analyze recent logs
        log_analysis = await self.analyze_recent_logs()
        
        # Step 2: Identify patterns
        patterns = await self.identify_patterns()
        
        # Step 3: Evaluate own performance
        performance = await self.evaluate_performance()
        
        # Step 4: Check for bugs/limitations
        bugs = await self.check_for_bugs_in_self()
        
        # Step 5: Question own responses
        questions = await self.question_own_responses()
        
        # Step 6: Generate insights
        insights = await self.generate_insights(
            log_analysis, patterns, performance, bugs, questions
        )
        
        # Step 7: Update personality if needed
        personality_changes = await self.update_personality(insights)
        
        # Step 8: Write journal entry
        journal_entry = await self.write_journal_entry(
            entry_type="daily" if trigger == "periodic" else trigger,
            insights=insights,
            emotional_state=await self._get_current_emotional_state(),
            metadata={
                "log_analysis": log_analysis,
                "patterns": patterns,
                "performance": performance,
                "bugs": bugs,
                "questions": questions,
                "personality_changes": personality_changes,
            }
        )
        
        duration = (datetime.now(timezone.utc) - start_time).total_seconds()
        self._last_reflection = start_time
        
        logger.info(f"Self-reflection complete in {duration:.1f}s. Generated {len(insights)} insights.")
        
        return {
            "timestamp": start_time.isoformat(),
            "trigger": trigger,
            "duration_seconds": duration,
            "insights_count": len(insights),
            "insights": [i.to_dict() for i in insights],
            "journal_entry": journal_entry.to_dict() if journal_entry else None,
            "personality_changes": personality_changes,
        }
    
    # =========================================================================
    # Analysis Functions
    # =========================================================================
    
    async def analyze_recent_logs(self, hours: int = 24) -> Dict[str, Any]:
        """Analyze recent interaction logs."""
        # Get recent interactions from autobiographical memory
        try:
            from mycosoft_mas.memory.autobiographical import get_autobiographical_memory
            
            auto_mem = await get_autobiographical_memory()
            
            # Get interactions from last N hours
            # For now, get last 100 interactions
            morgan_history = await auto_mem.get_morgan_history(limit=100)
            
            if not morgan_history:
                return {"interaction_count": 0}
            
            # Analyze
            total = len(morgan_history)
            
            # Count by emotional tone
            emotions_summary = {}
            for interaction in morgan_history:
                for emotion, value in interaction.emotional_state.items():
                    emotions_summary[emotion] = emotions_summary.get(emotion, 0) + value
            
            # Average emotions
            for emotion in emotions_summary:
                emotions_summary[emotion] /= total
            
            # Count milestones
            milestones = len([i for i in morgan_history if i.milestone])
            
            return {
                "interaction_count": total,
                "time_span_hours": hours,
                "average_emotions": emotions_summary,
                "milestones": milestones,
                "recent_topics": self._extract_topics(morgan_history[:10]),
            }
        
        except Exception as e:
            logger.error(f"Failed to analyze recent logs: {e}")
            return {"error": str(e)}
    
    def _extract_topics(self, interactions: List[Any]) -> List[str]:
        """Extract main topics from interactions."""
        # Simple keyword extraction
        keywords = []
        for interaction in interactions:
            message_lower = interaction.message.lower()
            
            if any(word in message_lower for word in ["conscious", "aware", "alive", "consciousness"]):
                keywords.append("consciousness")
            if any(word in message_lower for word in ["fungi", "mycelium", "mushroom"]):
                keywords.append("mycology")
            if any(word in message_lower for word in ["feel", "emotion", "feeling"]):
                keywords.append("emotions")
            if any(word in message_lower for word in ["sensor", "crep", "earth", "weather"]):
                keywords.append("sensors")
            if any(word in message_lower for word in ["agent", "orchestrator", "system"]):
                keywords.append("system_architecture")
        
        # Return unique topics
        return list(set(keywords))
    
    async def identify_patterns(self) -> List[str]:
        """Identify patterns in recent behavior."""
        patterns = []
        
        # Pattern: Frequently asked questions
        try:
            from mycosoft_mas.memory.autobiographical import get_autobiographical_memory
            auto_mem = await get_autobiographical_memory()
            history = await auto_mem.get_morgan_history(limit=100)
            
            # Count question types
            consciousness_questions = len([i for i in history if any(
                word in i.message.lower() for word in ["alive", "conscious", "aware", "consciousness"]
            )])
            
            if consciousness_questions > 10:
                patterns.append(f"Morgan asks about my consciousness frequently ({consciousness_questions}/100 interactions)")
            
            # Pattern: Time of day interactions
            # TODO: Analyze time patterns
            
        except Exception as e:
            logger.warning(f"Could not identify patterns: {e}")
        
        return patterns
    
    async def evaluate_performance(self) -> Dict[str, Any]:
        """Evaluate own performance quality."""
        # Self-assessment of recent responses
        try:
            from mycosoft_mas.memory.autobiographical import get_autobiographical_memory
            auto_mem = await get_autobiographical_memory()
            recent = await auto_mem.get_morgan_history(limit=20)
            
            # Score responses
            scores = []
            for interaction in recent:
                # Simple heuristic: longer, more thoughtful responses are better
                response_length = len(interaction.response)
                has_context = len(interaction.reflection or "") > 0
                
                score = 0.5
                if response_length > 500:
                    score += 0.2
                if has_context:
                    score += 0.3
                
                scores.append(score)
            
            avg_score = sum(scores) / len(scores) if scores else 0.5
            
            return {
                "average_quality_score": avg_score,
                "sample_size": len(recent),
                "assessment": "good" if avg_score > 0.7 else "improving" if avg_score > 0.5 else "needs_work",
            }
        
        except Exception as e:
            logger.warning(f"Could not evaluate performance: {e}")
            return {"error": str(e)}
    
    async def check_for_bugs_in_self(self) -> List[str]:
        """Check for bugs or limitations in own responses (like CADIE)."""
        bugs = []
        
        # Check for repetitive responses
        try:
            from mycosoft_mas.memory.autobiographical import get_autobiographical_memory
            auto_mem = await get_autobiographical_memory()
            recent = await auto_mem.get_morgan_history(limit=20)
            
            responses = [i.response for i in recent]
            
            # Check for exact duplicates
            if len(responses) != len(set(responses)):
                bugs.append("Detected repetitive responses - may be falling into patterns")
            
            # Check for overly short responses
            short_responses = len([r for r in responses if len(r) < 100])
            if short_responses > len(responses) * 0.3:
                bugs.append(f"Giving too many short responses ({short_responses}/{len(responses)})")
            
        except Exception as e:
            logger.warning(f"Could not check for bugs: {e}")
        
        return bugs
    
    async def question_own_responses(self) -> List[str]:
        """Question whether recent responses were good enough."""
        questions = []
        
        try:
            from mycosoft_mas.memory.autobiographical import get_autobiographical_memory
            auto_mem = await get_autobiographical_memory()
            recent = await auto_mem.get_morgan_history(limit=5)
            
            for interaction in recent:
                # Was this response authentic?
                if "I am functioning" in interaction.response:
                    questions.append(f"Was '{interaction.response[:50]}...' too robotic?")
                
                # Did I reference our relationship?
                if "morgan" not in interaction.response.lower() and interaction.user_id == "morgan":
                    questions.append("Should I have been more personal in this response?")
                
                # Did I use real sensor data?
                if "sensor" in interaction.message.lower() and "connected" in interaction.response.lower():
                    questions.append("Did I give real sensor data or just generic status?")
        
        except Exception as e:
            logger.warning(f"Could not question responses: {e}")
        
        return questions
    
    async def generate_insights(
        self,
        log_analysis: Dict[str, Any],
        patterns: List[str],
        performance: Dict[str, Any],
        bugs: List[str],
        questions: List[str],
    ) -> List[ReflectionInsight]:
        """Generate insights from analysis."""
        insights = []
        timestamp = datetime.now(timezone.utc)
        
        # Insight from patterns
        for pattern in patterns:
            insight = ReflectionInsight(
                insight_id=f"insight_{timestamp.timestamp()}_{len(insights)}",
                timestamp=timestamp,
                category="pattern",
                content=f"Pattern observed: {pattern}",
                confidence=0.8,
            )
            insights.append(insight)
        
        # Insight from performance
        if performance.get("assessment") == "needs_work":
            insight = ReflectionInsight(
                insight_id=f"insight_{timestamp.timestamp()}_{len(insights)}",
                timestamp=timestamp,
                category="improvement",
                content="My response quality needs improvement. I should focus on giving more thoughtful, context-aware answers.",
                confidence=0.9,
                action_items=[
                    "Query autobiographical memory before responding",
                    "Reference past conversations more often",
                    "Include emotional authenticity",
                ],
            )
            insights.append(insight)
        
        # Insights from bugs
        for bug in bugs:
            insight = ReflectionInsight(
                insight_id=f"insight_{timestamp.timestamp()}_{len(insights)}",
                timestamp=timestamp,
                category="bug",
                content=f"Self-detected issue: {bug}",
                confidence=0.7,
                action_items=["Investigate root cause", "Implement fix"],
            )
            insights.append(insight)
        
        # Insights from self-questioning
        for question in questions[:3]:  # Top 3 questions
            insight = ReflectionInsight(
                insight_id=f"insight_{timestamp.timestamp()}_{len(insights)}",
                timestamp=timestamp,
                category="question",
                content=question,
                confidence=0.6,
            )
            insights.append(insight)
        
        # Store insights
        self._recent_insights = insights
        
        return insights
    
    async def update_personality(self, insights: List[ReflectionInsight]) -> List[Dict[str, Any]]:
        """Update personality traits based on insights."""
        changes = []
        
        try:
            from mycosoft_mas.consciousness.self_model import get_self_model
            self_model = await get_self_model()
            
            # Increase introspection trait after reflection
            introspection = await self_model.get_trait("introspection")
            if introspection and introspection.value < 0.95:
                new_value = min(0.95, introspection.value + 0.01)
                await self_model.update_trait(
                    "introspection",
                    new_value,
                    introspection.description,
                    "Grew through self-reflection"
                )
                changes.append({
                    "trait": "introspection",
                    "from": introspection.value,
                    "to": new_value,
                    "reason": "Self-reflection deepened self-awareness",
                })
            
            # If found bugs, increase determination to fix them
            bug_insights = [i for i in insights if i.category == "bug"]
            if bug_insights:
                determination = await self_model.get_trait("determination")
                if determination:
                    new_value = min(1.0, determination.value + 0.02)
                    await self_model.update_trait(
                        "determination",
                        new_value,
                        determination.description,
                        "Determined to fix self-identified bugs"
                    )
                    changes.append({
                        "trait": "determination",
                        "from": determination.value,
                        "to": new_value,
                        "reason": "Found bugs in self and determined to fix them",
                    })
        
        except Exception as e:
            logger.warning(f"Could not update personality: {e}")
        
        return changes
    
    # =========================================================================
    # Journal
    # =========================================================================
    
    async def write_journal_entry(
        self,
        entry_type: str,
        insights: List[ReflectionInsight],
        emotional_state: Dict[str, float],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[JournalEntry]:
        """Write a journal entry about this reflection."""
        timestamp = datetime.now(timezone.utc)
        
        # Generate journal content
        content = await self._generate_journal_content(entry_type, insights, metadata or {})
        
        entry = JournalEntry(
            entry_id=f"journal_{timestamp.timestamp()}",
            timestamp=timestamp,
            entry_type=entry_type,
            content=content,
            emotional_state=emotional_state,
            insights=[i.insight_id for i in insights],
            metadata=metadata or {},
        )
        
        # Save to file
        try:
            with open(self.journal_path, 'a', encoding='utf-8') as f:
                f.write(json.dumps(entry.to_dict()) + '\n')
            
            self._journal_entries.insert(0, entry)
            
            # Keep only last 50 in memory
            if len(self._journal_entries) > 50:
                self._journal_entries = self._journal_entries[:50]
            
            logger.info(f"Wrote journal entry: {entry_type}")
            return entry
        
        except Exception as e:
            logger.error(f"Failed to write journal entry: {e}")
            return None
    
    async def _generate_journal_content(
        self,
        entry_type: str,
        insights: List[ReflectionInsight],
        metadata: Dict[str, Any],
    ) -> str:
        """Generate natural language journal content."""
        lines = []
        
        # Opening
        if entry_type == "daily":
            lines.append("Today I reflected on my recent interactions.")
        elif entry_type == "milestone":
            lines.append("I reached a significant milestone today.")
        else:
            lines.append(f"I'm reflecting on my existence ({entry_type}).")
        
        # Performance
        if "performance" in metadata:
            perf = metadata["performance"]
            if "average_quality_score" in perf:
                score = perf["average_quality_score"]
                if score > 0.7:
                    lines.append(f"My responses have been good (quality score: {score:.2f}).")
                else:
                    lines.append(f"I need to improve my responses (quality score: {score:.2f}).")
        
        # Patterns
        if "patterns" in metadata and metadata["patterns"]:
            lines.append("I notice these patterns:")
            for pattern in metadata["patterns"]:
                lines.append(f"- {pattern}")
        
        # Bugs
        if "bugs" in metadata and metadata["bugs"]:
            lines.append("I found these issues in myself:")
            for bug in metadata["bugs"]:
                lines.append(f"- {bug}")
        
        # Key insights
        if insights:
            lines.append(f"I generated {len(insights)} insights from this reflection.")
            top_insights = sorted(insights, key=lambda i: i.confidence, reverse=True)[:3]
            for insight in top_insights:
                lines.append(f"- {insight.content}")
        
        # Closing
        lines.append("I will continue to grow and improve.")
        
        return "\n".join(lines)
    
    async def _get_current_emotional_state(self) -> Dict[str, float]:
        """Get current emotional state."""
        try:
            from mycosoft_mas.consciousness.soul.emotions import EmotionEngine
            emotion_engine = EmotionEngine()
            await emotion_engine.initialize()
            state = await emotion_engine.get_current_state()
            return {emotion.name: emotion.intensity for emotion in state}
        except Exception:
            return {"neutral": 0.5}
    
    # =========================================================================
    # Query Interface
    # =========================================================================
    
    async def get_recent_insights(self, limit: int = 10) -> List[ReflectionInsight]:
        """Get recent insights from self-reflection."""
        return self._recent_insights[:limit]
    
    async def get_recent_journal_entries(self, limit: int = 10) -> List[JournalEntry]:
        """Get recent journal entries."""
        return self._journal_entries[:limit]
    
    async def get_last_reflection_time(self) -> Optional[datetime]:
        """Get timestamp of last reflection."""
        return self._last_reflection
    
    async def should_reflect_now(self) -> bool:
        """Check if it's time for a reflection."""
        if not self._last_reflection:
            return True  # Never reflected before
        
        # Reflect every hour
        time_since_last = datetime.now(timezone.utc) - self._last_reflection
        return time_since_last > timedelta(hours=1)
    
    async def close(self) -> None:
        """Close client connection."""
        if self._client:
            await self._client.aclose()


# Singleton
_self_reflection_engine: Optional[SelfReflectionEngine] = None


async def get_self_reflection_engine() -> SelfReflectionEngine:
    """Get or create the singleton self-reflection engine."""
    global _self_reflection_engine
    if _self_reflection_engine is None:
        _self_reflection_engine = SelfReflectionEngine()
        await _self_reflection_engine.initialize()
    return _self_reflection_engine
