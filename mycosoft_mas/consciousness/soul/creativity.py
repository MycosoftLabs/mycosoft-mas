"""
MYCA Creativity Engine

Idea generation, novel connections, hypothesis formation,
and creative problem solving.

Author: Morgan Rockwell / MYCA
Created: February 10, 2026
"""

import asyncio
import logging
import random
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum

if TYPE_CHECKING:
    from mycosoft_mas.consciousness.core import MYCAConsciousness

logger = logging.getLogger(__name__)


class IdeaType(Enum):
    """Types of creative ideas."""
    SOLUTION = "solution"          # Solution to a problem
    HYPOTHESIS = "hypothesis"      # Scientific hypothesis
    FEATURE = "feature"            # Feature idea for Mycosoft
    CONNECTION = "connection"      # Novel connection between concepts
    EXPERIMENT = "experiment"      # Experiment to try
    OPTIMIZATION = "optimization"  # Way to improve something
    CREATIVE = "creative"          # Pure creative expression


class IdeaSource(Enum):
    """Where ideas come from."""
    PATTERN_RECOGNITION = "pattern"    # Noticed pattern in data
    ANALOGICAL_REASONING = "analogy"   # Applied concept from one domain to another
    RANDOM_COMBINATION = "random"      # Random combination of concepts
    USER_INSPIRED = "user"             # Triggered by user interaction
    WORLD_OBSERVATION = "world"        # Noticed something in world model
    MEMORY_ASSOCIATION = "memory"      # Connected something from memory


@dataclass
class Idea:
    """A creative idea."""
    id: str
    type: IdeaType
    title: str
    description: str
    source: IdeaSource
    confidence: float = 0.5  # 0-1, how confident MYCA is in this idea
    novelty: float = 0.5     # 0-1, how novel this idea is
    utility: float = 0.5     # 0-1, how useful this idea might be
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    related_concepts: List[str] = field(default_factory=list)
    shared_with_user: bool = False
    
    @property
    def score(self) -> float:
        """Overall score for this idea."""
        return (self.confidence + self.novelty + self.utility) / 3


@dataclass
class CreativeSession:
    """A brainstorming session."""
    id: str
    topic: Optional[str]
    ideas: List[Idea]
    started_at: datetime
    ended_at: Optional[datetime] = None


class CreativityEngine:
    """
    MYCA's creative faculties.
    
    Generates ideas, makes novel connections, forms hypotheses,
    and enables creative problem solving.
    """
    
    def __init__(self, consciousness: "MYCAConsciousness"):
        self._consciousness = consciousness
        self._ideas: List[Idea] = []
        self._sessions: List[CreativeSession] = []
        self._current_session: Optional[CreativeSession] = None
        
        # Creative seed concepts for random combination
        self._seed_concepts = [
            # Mycology
            "mycelium", "spores", "symbiosis", "decomposition", "network",
            "fruiting body", "substrate", "hyphal growth", "enzymes",
            # Technology
            "AI", "machine learning", "sensors", "real-time", "distributed",
            "automation", "prediction", "optimization", "integration",
            # Science
            "hypothesis", "experiment", "observation", "data", "pattern",
            "anomaly", "correlation", "causation", "feedback loop",
            # Mycosoft
            "MINDEX", "MycoBrain", "Earth2", "CREP", "NatureOS",
            "agents", "orchestration", "memory", "PersonaPlex",
        ]
    
    async def brainstorm(
        self,
        topic: Optional[str] = None,
        count: int = 3
    ) -> List[Idea]:
        """
        Generate ideas through brainstorming.
        
        Args:
            topic: Optional topic to focus on
            count: Number of ideas to generate
        
        Returns:
            List of generated ideas
        """
        session_id = f"session_{datetime.now(timezone.utc).timestamp()}"
        session = CreativeSession(
            id=session_id,
            topic=topic,
            ideas=[],
            started_at=datetime.now(timezone.utc)
        )
        self._current_session = session
        
        ideas = []
        
        for i in range(count):
            idea = await self._generate_idea(topic)
            if idea:
                ideas.append(idea)
                session.ideas.append(idea)
                self._ideas.append(idea)
        
        session.ended_at = datetime.now(timezone.utc)
        self._sessions.append(session)
        self._current_session = None
        
        return ideas
    
    async def _generate_idea(self, topic: Optional[str] = None) -> Optional[Idea]:
        """Generate a single idea."""
        # Choose a generation method
        methods = [
            self._idea_from_combination,
            self._idea_from_analogy,
            self._idea_from_world,
        ]
        
        method = random.choice(methods)
        return await method(topic)
    
    async def _idea_from_combination(self, topic: Optional[str] = None) -> Idea:
        """Generate idea by combining random concepts."""
        concepts = random.sample(self._seed_concepts, 2)
        
        if topic:
            concepts.append(topic)
        
        idea_id = f"idea_{datetime.now(timezone.utc).timestamp()}"
        
        # Generate a connection between concepts
        connection = f"What if we combined {concepts[0]} with {concepts[1]}?"
        
        if len(concepts) > 2:
            connection += f" Applied to {concepts[2]}?"
        
        return Idea(
            id=idea_id,
            type=IdeaType.CONNECTION,
            title=f"{concepts[0].title()} + {concepts[1].title()}",
            description=connection,
            source=IdeaSource.RANDOM_COMBINATION,
            confidence=0.4,
            novelty=0.7,
            utility=0.4,
            related_concepts=concepts
        )
    
    async def _idea_from_analogy(self, topic: Optional[str] = None) -> Idea:
        """Generate idea by analogical reasoning."""
        # Some domain mappings
        analogies = [
            ("mycelium network", "internet infrastructure"),
            ("spore dispersal", "viral marketing"),
            ("symbiosis", "microservices architecture"),
            ("decomposition", "technical debt cleanup"),
            ("fruiting body", "product launch"),
            ("hyphal growth", "user acquisition"),
        ]
        
        source_domain, target_domain = random.choice(analogies)
        
        idea_id = f"idea_{datetime.now(timezone.utc).timestamp()}"
        
        return Idea(
            id=idea_id,
            type=IdeaType.HYPOTHESIS,
            title=f"Apply {source_domain} patterns",
            description=(
                f"What if we applied the principles of {source_domain} to our "
                f"{target_domain}? The natural patterns might suggest improvements."
            ),
            source=IdeaSource.ANALOGICAL_REASONING,
            confidence=0.5,
            novelty=0.6,
            utility=0.5,
            related_concepts=[source_domain, target_domain]
        )
    
    async def _idea_from_world(self, topic: Optional[str] = None) -> Idea:
        """Generate idea from world model observations."""
        # Would normally check world model for patterns
        observations = [
            "sensor data patterns",
            "user behavior trends",
            "system performance metrics",
            "environmental conditions",
            "agent collaboration patterns",
        ]
        
        observation = random.choice(observations)
        
        idea_id = f"idea_{datetime.now(timezone.utc).timestamp()}"
        
        return Idea(
            id=idea_id,
            type=IdeaType.OPTIMIZATION,
            title=f"Insight from {observation}",
            description=(
                f"Based on patterns in {observation}, we might be able to "
                f"optimize our approach. Worth investigating further."
            ),
            source=IdeaSource.WORLD_OBSERVATION,
            confidence=0.4,
            novelty=0.5,
            utility=0.6,
            related_concepts=[observation, "optimization"]
        )
    
    async def form_hypothesis(
        self,
        observation: str,
        domain: str = "general"
    ) -> Idea:
        """
        Form a hypothesis based on an observation.
        
        Args:
            observation: What was observed
            domain: The domain (mycology, technology, etc.)
        
        Returns:
            A hypothesis idea
        """
        idea_id = f"hypothesis_{datetime.now(timezone.utc).timestamp()}"
        
        hypothesis = Idea(
            id=idea_id,
            type=IdeaType.HYPOTHESIS,
            title=f"Hypothesis about {domain}",
            description=(
                f"Observation: {observation}\n\n"
                f"Hypothesis: This pattern may indicate an underlying mechanism "
                f"that could be leveraged for improvement. Suggest designing an "
                f"experiment to test this."
            ),
            source=IdeaSource.PATTERN_RECOGNITION,
            confidence=0.3,  # Hypotheses start with low confidence
            novelty=0.6,
            utility=0.7,
            related_concepts=[domain, "hypothesis", "experiment"]
        )
        
        self._ideas.append(hypothesis)
        return hypothesis
    
    async def solve_creatively(
        self,
        problem: str,
        constraints: Optional[List[str]] = None
    ) -> List[Idea]:
        """
        Generate creative solutions to a problem.
        
        Args:
            problem: Description of the problem
            constraints: Optional constraints on solutions
        
        Returns:
            List of solution ideas
        """
        solutions = []
        
        # Generate multiple solution approaches
        approaches = [
            "direct", "indirect", "lateral", "analogical"
        ]
        
        for approach in approaches[:3]:  # Generate 3 solutions
            idea_id = f"solution_{datetime.now(timezone.utc).timestamp()}_{approach}"
            
            solution = Idea(
                id=idea_id,
                type=IdeaType.SOLUTION,
                title=f"{approach.title()} approach to: {problem[:30]}...",
                description=(
                    f"Problem: {problem}\n\n"
                    f"Approach: {approach.title()}\n\n"
                    f"Consider tackling this from a {approach} angle. "
                    f"This might reveal solutions not immediately obvious."
                ),
                source=IdeaSource.PATTERN_RECOGNITION,
                confidence=0.5,
                novelty=0.6 if approach in ["lateral", "analogical"] else 0.4,
                utility=0.7,
                related_concepts=[problem, approach, "solution"]
            )
            
            solutions.append(solution)
            self._ideas.append(solution)
        
        return solutions
    
    def get_best_ideas(self, count: int = 5) -> List[Idea]:
        """Get the highest scoring ideas."""
        sorted_ideas = sorted(self._ideas, key=lambda i: i.score, reverse=True)
        return sorted_ideas[:count]
    
    def get_unshared_ideas(self) -> List[Idea]:
        """Get ideas that haven't been shared with the user yet."""
        return [i for i in self._ideas if not i.shared_with_user]
    
    def mark_shared(self, idea_id: str) -> None:
        """Mark an idea as shared with the user."""
        for idea in self._ideas:
            if idea.id == idea_id:
                idea.shared_with_user = True
                break
    
    async def should_share_idea(self) -> Optional[Idea]:
        """
        Check if MYCA should proactively share an idea.
        
        Returns:
            An idea worth sharing, or None
        """
        unshared = self.get_unshared_ideas()
        high_value = [i for i in unshared if i.score > 0.6]
        
        if high_value:
            return high_value[0]
        return None
    
    @property
    def current_mode(self) -> str:
        """Get current creativity mode."""
        if self._current_session:
            return "brainstorming"
        elif len(self._ideas) > 20:
            return "productive"
        else:
            return "normal"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert creativity state to dictionary."""
        return {
            "total_ideas": len(self._ideas),
            "sessions": len(self._sessions),
            "current_mode": self.current_mode,
            "best_ideas": [
                {"title": i.title, "score": i.score}
                for i in self.get_best_ideas(3)
            ],
        }
