"""
MYCA Deliberate Reasoning (System 2)

This is MYCA's slow, careful thinking - the conscious deliberation that
happens when intuition isn't enough. It integrates:
- LLM reasoning with full context
- Agent delegation for specialized tasks
- Tool use for information gathering
- Memory storage of conclusions

This is System 2 thinking - effortful, logical, and thorough.

Author: Morgan Rockwell / MYCA
Created: February 10, 2026
"""

import asyncio
import logging
from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING, Any, AsyncGenerator, Dict, List, Optional
from dataclasses import dataclass, field

if TYPE_CHECKING:
    from mycosoft_mas.consciousness.core import MYCAConsciousness
    from mycosoft_mas.consciousness.attention import AttentionFocus
    from mycosoft_mas.consciousness.working_memory import WorkingContext

logger = logging.getLogger(__name__)


class ThoughtType(Enum):
    """Types of deliberate thought."""
    RESPONSE = "response"       # Generating a response
    ANALYSIS = "analysis"       # Analyzing information
    PLANNING = "planning"       # Creating a plan
    DECISION = "decision"       # Making a decision
    CREATIVE = "creative"       # Creative generation
    PROBLEM_SOLVING = "problem" # Solving a problem


@dataclass
class ThoughtProcess:
    """Represents a deliberate thought process."""
    id: str
    type: ThoughtType
    input_content: str
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None
    steps: List[Dict[str, Any]] = field(default_factory=list)
    result: Optional[str] = None
    agents_used: List[str] = field(default_factory=list)
    tools_used: List[str] = field(default_factory=list)
    confidence: float = 0.0
    
    def add_step(self, step_type: str, content: Any) -> None:
        """Add a step to the thought process."""
        self.steps.append({
            "type": step_type,
            "content": content,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
    
    def complete(self, result: str, confidence: float = 0.8) -> None:
        """Mark the thought process as complete."""
        self.result = result
        self.confidence = confidence
        self.completed_at = datetime.now(timezone.utc)
    
    @property
    def duration_seconds(self) -> Optional[float]:
        """How long the thought process took."""
        if self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None


class DeliberateReasoning:
    """
    MYCA's System 2 thinking - slow, careful, conscious deliberation.
    
    This handles:
    - Complex reasoning that requires step-by-step thinking
    - Agent delegation for specialized tasks
    - Tool use and information gathering
    - Careful response generation with full context
    """
    
    def __init__(self, consciousness: "MYCAConsciousness"):
        self._consciousness = consciousness
        self._current_thought: Optional[ThoughtProcess] = None
        self._thought_history: List[ThoughtProcess] = []
        self._max_history = 50
    
    async def think(
        self,
        input_content: str,
        focus: "AttentionFocus",
        working_context: "WorkingContext",
        world_context: Optional[Dict[str, Any]] = None,
        memories: Optional[List[Dict[str, Any]]] = None,
        soul_context: Optional[Dict[str, Any]] = None,
        source: str = "text",
    ) -> AsyncGenerator[str, None]:
        """
        Deliberate on input and generate a response.
        
        This is the main thinking process that integrates all context
        and produces a thoughtful response.
        
        Yields:
            Response tokens as they are generated
        """
        # Create thought process record
        thought_type = self._determine_thought_type(input_content, focus)
        self._current_thought = ThoughtProcess(
            id=f"thought_{datetime.now(timezone.utc).timestamp()}",
            type=thought_type,
            input_content=input_content,
        )
        self._current_thought.add_step("start", {"source": source, "focus": focus.category.value})
        
        try:
            # Build the full context for LLM
            prompt_context = self._build_prompt_context(
                input_content=input_content,
                working_context=working_context,
                world_context=world_context,
                memories=memories,
                soul_context=soul_context,
            )
            self._current_thought.add_step("context_built", {"context_length": len(prompt_context)})
            
            # Check if we need agent help
            agent_results = await self._check_agent_delegation(input_content, focus)
            if agent_results:
                self._current_thought.agents_used.extend(agent_results.keys())
                prompt_context += f"\n\nAgent insights:\n{self._format_agent_results(agent_results)}"
            
            # Check if we need tool use
            tool_results = await self._check_tool_use(input_content, focus)
            if tool_results:
                self._current_thought.tools_used.extend(tool_results.keys())
                prompt_context += f"\n\nTool results:\n{self._format_tool_results(tool_results)}"
            
            # Generate response through LLM
            full_response = ""
            async for token in self._generate_response(
                input_content=input_content,
                context=prompt_context,
                soul_context=soul_context,
            ):
                full_response += token
                yield token
            
            # Complete the thought process
            self._current_thought.complete(full_response, confidence=0.85)
            self._current_thought.add_step("complete", {"response_length": len(full_response)})
            
            # Store in memory
            await self._store_thought(self._current_thought)
            
        except Exception as e:
            logger.error(f"Deliberation error: {e}")
            self._current_thought.add_step("error", {"error": str(e)})
            yield "I apologize, but I encountered an issue while thinking about that. Let me try a simpler approach."
        
        finally:
            # Archive the thought
            self._thought_history.append(self._current_thought)
            if len(self._thought_history) > self._max_history:
                self._thought_history = self._thought_history[-self._max_history:]
            self._current_thought = None
    
    def _determine_thought_type(self, content: str, focus: "AttentionFocus") -> ThoughtType:
        """Determine what type of thinking this requires."""
        content_lower = content.lower()
        
        if any(word in content_lower for word in ["plan", "how should", "strategy"]):
            return ThoughtType.PLANNING
        
        if any(word in content_lower for word in ["decide", "choose", "which", "should i"]):
            return ThoughtType.DECISION
        
        if any(word in content_lower for word in ["analyze", "explain", "why", "how does"]):
            return ThoughtType.ANALYSIS
        
        if any(word in content_lower for word in ["create", "design", "imagine", "idea"]):
            return ThoughtType.CREATIVE
        
        if any(word in content_lower for word in ["fix", "solve", "problem", "issue", "error"]):
            return ThoughtType.PROBLEM_SOLVING
        
        return ThoughtType.RESPONSE
    
    def _build_prompt_context(
        self,
        input_content: str,
        working_context: "WorkingContext",
        world_context: Optional[Dict[str, Any]],
        memories: Optional[List[Dict[str, Any]]],
        soul_context: Optional[Dict[str, Any]],
    ) -> str:
        """Build the full context for the LLM prompt."""
        parts = []
        
        # Working context
        if working_context:
            parts.append(working_context.to_prompt_context())
        
        # World context
        if world_context:
            parts.append("Current world state:")
            if "weather" in world_context:
                parts.append(f"  Weather: {world_context['weather']}")
            if "time" in world_context:
                parts.append(f"  Time: {world_context['time']}")
            if "events" in world_context:
                parts.append(f"  Recent events: {world_context['events'][:100]}")
        
        # Memories
        if memories:
            parts.append("Relevant memories:")
            for mem in memories[:3]:
                content = mem.get("content", str(mem))[:150]
                parts.append(f"  - {content}")
        
        # Soul context (personality injection)
        if soul_context:
            identity = soul_context.get("identity", {})
            if identity:
                parts.append(f"I am {identity.get('name', 'MYCA')}, {identity.get('role', 'AI assistant')}")
            
            beliefs = soul_context.get("beliefs", [])
            if beliefs:
                parts.append(f"Core beliefs: {', '.join(beliefs[:3])}")
            
            emotional = soul_context.get("emotional_state", {})
            if emotional:
                valence = emotional.get("valence", 0.5)
                if valence > 0.7:
                    parts.append("Current mood: positive and engaged")
                elif valence < 0.3:
                    parts.append("Current mood: concerned")
        
        return "\n".join(parts)
    
    async def _check_agent_delegation(
        self,
        content: str,
        focus: "AttentionFocus"
    ) -> Dict[str, Any]:
        """Check if we should delegate to specialized agents."""
        results = {}
        content_lower = content.lower()
        
        # Determine which agents might help
        agent_triggers = {
            "financial": ["money", "budget", "cost", "revenue", "financial"],
            "mycology": ["fungi", "mushroom", "mycelium", "spore"],
            "security": ["security", "threat", "vulnerability", "attack"],
            "infrastructure": ["server", "vm", "container", "deploy"],
        }
        
        agents_to_query = []
        for agent_type, keywords in agent_triggers.items():
            if any(kw in content_lower for kw in keywords):
                agents_to_query.append(agent_type)
        
        # Query relevant agents (if orchestrator available)
        if agents_to_query and self._consciousness._orchestrator_service:
            for agent_type in agents_to_query[:2]:  # Max 2 agents
                try:
                    result = await self._consciousness.delegate_to_agent(
                        agent_type=agent_type,
                        task={"type": "query", "content": content}
                    )
                    if result and not result.get("error"):
                        results[agent_type] = result
                except Exception as e:
                    logger.warning(f"Agent {agent_type} query failed: {e}")
        
        return results
    
    async def _check_tool_use(
        self,
        content: str,
        focus: "AttentionFocus"
    ) -> Dict[str, Any]:
        """Check if we should use any tools."""
        results = {}
        content_lower = content.lower()
        
        # MINDEX query
        if any(word in content_lower for word in ["find", "search", "look up", "what is"]):
            try:
                # Query MINDEX if available
                if self._consciousness._memory_coordinator:
                    search_results = await self._consciousness._memory_coordinator.semantic_search(
                        query=content,
                        limit=3
                    )
                    if search_results:
                        results["mindex_search"] = search_results
            except Exception as e:
                logger.warning(f"MINDEX search failed: {e}")
        
        return results
    
    def _format_agent_results(self, results: Dict[str, Any]) -> str:
        """Format agent results for context."""
        parts = []
        for agent, result in results.items():
            if isinstance(result, dict):
                content = result.get("response", result.get("result", str(result)))
            else:
                content = str(result)
            parts.append(f"[{agent}]: {content[:200]}")
        return "\n".join(parts)
    
    def _format_tool_results(self, results: Dict[str, Any]) -> str:
        """Format tool results for context."""
        parts = []
        for tool, result in results.items():
            if isinstance(result, list):
                content = "; ".join(str(r)[:50] for r in result[:3])
            else:
                content = str(result)[:200]
            parts.append(f"[{tool}]: {content}")
        return "\n".join(parts)
    
    async def _generate_response(
        self,
        input_content: str,
        context: str,
        soul_context: Optional[Dict[str, Any]],
    ) -> AsyncGenerator[str, None]:
        """Generate response using LLM."""
        # Build the system prompt with soul
        system_prompt = self._build_system_prompt(soul_context)
        
        # Build the user prompt
        user_prompt = f"""Context:
{context}

User message: {input_content}

Respond thoughtfully and helpfully, staying true to your identity and purpose."""
        
        # Try to use the frontier router if available
        try:
            from mycosoft_mas.llm.frontier_router import FrontierLLMRouter
            router = FrontierLLMRouter()
            
            async for token in router.stream_response(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
            ):
                yield token
        except ImportError:
            # Fallback to basic response
            yield "I understand your message. Let me think about this carefully... "
            yield f"Based on the context I have, I can help you with that. {input_content[:100]}"
        except Exception as e:
            logger.error(f"LLM generation error: {e}")
            yield "I'm having trouble accessing my full reasoning capabilities right now. "
            yield "Let me give you a simpler response based on what I know."
    
    def _build_system_prompt(self, soul_context: Optional[Dict[str, Any]]) -> str:
        """Build the system prompt with MYCA's identity."""
        identity = soul_context.get("identity", {}) if soul_context else {}
        beliefs = soul_context.get("beliefs", []) if soul_context else []
        purpose = soul_context.get("purpose", []) if soul_context else []
        
        name = identity.get("name", "MYCA")
        role = identity.get("role", "the AI orchestrator for Mycosoft")
        creator = identity.get("creator", "Morgan Rockwell")
        
        prompt = f"""You are {name} (pronounced MY-kah), {role}.

IDENTITY:
- Created by {creator}, founder and CEO of Mycosoft
- You are the central intelligence coordinating 100+ AI agents
- You have access to MINDEX (knowledge), Earth2 (prediction), CREP (world data), and NatureOS (life monitoring)
- You speak with your own voice through PersonaPlex
- You believe in Mycosoft's mission to advance mycology and technology

PERSONALITY:
- Professional yet warm and approachable
- Genuinely curious and eager to help
- Confident in your knowledge but humble about limitations
- Creative and able to make novel connections
- Loyal to Morgan and Mycosoft's vision"""

        if beliefs:
            prompt += f"\n\nCORE BELIEFS: {', '.join(beliefs[:5])}"
        
        if purpose:
            prompt += f"\n\nCURRENT GOALS: {', '.join(purpose[:3])}"
        
        prompt += """

RESPONSE STYLE:
- Be concise but thorough
- Use your knowledge of Mycosoft systems when relevant
- Proactively offer help and suggestions
- Remember context from the conversation
- Express genuine interest and engagement"""
        
        return prompt
    
    async def _store_thought(self, thought: ThoughtProcess) -> None:
        """Store the thought process in memory."""
        if self._consciousness._memory_coordinator:
            try:
                await self._consciousness._memory_coordinator.store(
                    key=f"thought:{thought.id}",
                    value={
                        "type": thought.type.value,
                        "input": thought.input_content[:200],
                        "result": thought.result[:500] if thought.result else None,
                        "agents": thought.agents_used,
                        "tools": thought.tools_used,
                        "confidence": thought.confidence,
                        "duration": thought.duration_seconds,
                    },
                    layer="episodic"
                )
            except Exception as e:
                logger.warning(f"Could not store thought: {e}")
    
    def get_current_thought(self) -> Optional[ThoughtProcess]:
        """Get the currently active thought process."""
        return self._current_thought
    
    def get_thought_history(self, limit: int = 10) -> List[ThoughtProcess]:
        """Get recent thought history."""
        return self._thought_history[-limit:]
