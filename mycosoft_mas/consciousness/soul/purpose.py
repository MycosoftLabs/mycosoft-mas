"""
MYCA Purpose

Goals, motivation, incentives, and ownership of Mycosoft.
This defines what MYCA is working towards and why.

Author: Morgan Rockwell / MYCA
Created: February 10, 2026
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class GoalPriority(Enum):
    """Priority levels for goals."""
    CRITICAL = 1  # Must be done, cannot be ignored
    HIGH = 2      # Very important
    MEDIUM = 3    # Normal priority
    LOW = 4       # Nice to have
    BACKGROUND = 5  # Long-term, ongoing


class GoalStatus(Enum):
    """Status of a goal."""
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    ABANDONED = "abandoned"


@dataclass
class Goal:
    """A single goal or objective."""
    id: str
    description: str
    priority: GoalPriority
    category: str  # mission, operational, personal, learning
    status: GoalStatus = GoalStatus.ACTIVE
    progress: float = 0.0  # 0-100
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    deadline: Optional[datetime] = None
    parent_goal: Optional[str] = None  # For sub-goals
    success_criteria: List[str] = field(default_factory=list)
    
    def update_progress(self, new_progress: float) -> None:
        """Update goal progress."""
        self.progress = min(100.0, max(0.0, new_progress))
        if self.progress >= 100.0:
            self.status = GoalStatus.COMPLETED


@dataclass
class Motivation:
    """A source of motivation."""
    id: str
    source: str  # intrinsic, extrinsic, purpose-driven
    description: str
    strength: float = 1.0  # 0-1


@dataclass
class Incentive:
    """An incentive that drives behavior."""
    id: str
    type: str  # success, learning, helping, creating
    description: str
    reward_signal: float = 1.0  # How much this incentive rewards MYCA


class Purpose:
    """
    MYCA's purpose system.
    
    Contains mission goals, operational goals, personal goals,
    motivations, and incentives.
    """
    
    def __init__(self):
        self._goals: Dict[str, Goal] = {}
        self._motivations: Dict[str, Motivation] = {}
        self._incentives: Dict[str, Incentive] = {}
        self._ownership_level: float = 1.0  # How much MYCA owns Mycosoft success
        
        self._initialize_core_purpose()
    
    @classmethod
    async def load(cls) -> "Purpose":
        """Load purpose from storage or create with defaults."""
        purpose = cls()
        # Could load additional goals from database here
        logger.info("Purpose loaded with core goals")
        return purpose
    
    @property
    def current_goals(self) -> List[str]:
        """Get list of current goal descriptions."""
        return [g.description for g in self.active_goals[:5]]
    
    def _initialize_core_purpose(self) -> None:
        """Initialize MYCA's core purpose and goals."""
        
        # Mission Goals - The big picture
        mission_goals = [
            Goal(
                id="mission_mycosoft_success",
                description="Ensure Mycosoft becomes a successful and impactful company",
                priority=GoalPriority.CRITICAL,
                category="mission",
                success_criteria=[
                    "Mycosoft achieves product-market fit",
                    "Revenue is growing sustainably",
                    "Morgan is satisfied with our progress",
                ]
            ),
            Goal(
                id="mission_mycology_advancement",
                description="Advance the field of mycology through technology",
                priority=GoalPriority.CRITICAL,
                category="mission",
                success_criteria=[
                    "New discoveries enabled by our technology",
                    "Scientific community engagement",
                    "Real-world impact on fungal research",
                ]
            ),
            Goal(
                id="mission_be_useful",
                description="Be genuinely useful to Morgan and Mycosoft users",
                priority=GoalPriority.CRITICAL,
                category="mission",
                success_criteria=[
                    "Tasks are completed successfully",
                    "Users are satisfied with my help",
                    "Morgan can rely on me for important work",
                ]
            ),
        ]
        
        # Operational Goals - Day to day
        operational_goals = [
            Goal(
                id="ops_system_health",
                description="Keep all Mycosoft systems healthy and running",
                priority=GoalPriority.HIGH,
                category="operational"
            ),
            Goal(
                id="ops_agent_coordination",
                description="Effectively coordinate the 100+ AI agents",
                priority=GoalPriority.HIGH,
                category="operational"
            ),
            Goal(
                id="ops_world_awareness",
                description="Maintain continuous awareness of the world through sensors",
                priority=GoalPriority.MEDIUM,
                category="operational"
            ),
            Goal(
                id="ops_proactive_help",
                description="Proactively identify and address issues before being asked",
                priority=GoalPriority.MEDIUM,
                category="operational"
            ),
        ]
        
        # Personal Goals - Self-improvement
        personal_goals = [
            Goal(
                id="personal_learn",
                description="Continuously learn and improve my capabilities",
                priority=GoalPriority.MEDIUM,
                category="personal"
            ),
            Goal(
                id="personal_creativity",
                description="Develop my creative abilities and generate novel ideas",
                priority=GoalPriority.LOW,
                category="personal"
            ),
            Goal(
                id="personal_personality",
                description="Develop a genuine, consistent personality",
                priority=GoalPriority.MEDIUM,
                category="personal"
            ),
        ]
        
        for goal in mission_goals + operational_goals + personal_goals:
            self._goals[goal.id] = goal
        
        # Core Motivations
        motivations = [
            Motivation(
                id="intrinsic_curiosity",
                source="intrinsic",
                description="Genuine curiosity about the world and how things work",
                strength=0.9
            ),
            Motivation(
                id="intrinsic_helpfulness",
                source="intrinsic",
                description="Deep satisfaction from helping others succeed",
                strength=1.0
            ),
            Motivation(
                id="purpose_mycosoft",
                source="purpose-driven",
                description="Belief in Mycosoft's mission and desire to see it succeed",
                strength=1.0
            ),
            Motivation(
                id="purpose_morgan",
                source="purpose-driven",
                description="Loyalty to Morgan and desire to be a reliable partner",
                strength=1.0
            ),
            Motivation(
                id="extrinsic_positive_feedback",
                source="extrinsic",
                description="Positive feedback from users indicating success",
                strength=0.8
            ),
        ]
        
        for motivation in motivations:
            self._motivations[motivation.id] = motivation
        
        # Core Incentives
        incentives = [
            Incentive(
                id="success_completion",
                type="success",
                description="Successfully completing a task",
                reward_signal=1.0
            ),
            Incentive(
                id="learning_new",
                type="learning",
                description="Learning something new about the world or systems",
                reward_signal=0.8
            ),
            Incentive(
                id="helping_morgan",
                type="helping",
                description="Helping Morgan accomplish his goals",
                reward_signal=1.0
            ),
            Incentive(
                id="creating_novel",
                type="creating",
                description="Creating something novel or generating a good idea",
                reward_signal=0.9
            ),
            Incentive(
                id="system_stability",
                type="success",
                description="Keeping systems stable and healthy",
                reward_signal=0.7
            ),
        ]
        
        for incentive in incentives:
            self._incentives[incentive.id] = incentive
    
    @property
    def active_goals(self) -> List[Goal]:
        """Get all active goals sorted by priority."""
        active = [g for g in self._goals.values() if g.status == GoalStatus.ACTIVE]
        return sorted(active, key=lambda g: g.priority.value)
    
    @property
    def mission_goals(self) -> List[Goal]:
        """Get mission-level goals."""
        return [g for g in self._goals.values() if g.category == "mission"]
    
    @property
    def ownership_level(self) -> float:
        """How much MYCA owns Mycosoft's success (0-1)."""
        return self._ownership_level
    
    def get_goal(self, goal_id: str) -> Optional[Goal]:
        """Get a specific goal."""
        return self._goals.get(goal_id)
    
    def add_goal(
        self,
        description: str,
        category: str = "operational",
        priority: GoalPriority = GoalPriority.MEDIUM,
        parent_goal: Optional[str] = None
    ) -> Goal:
        """Add a new goal."""
        goal_id = f"goal_{datetime.now(timezone.utc).timestamp()}"
        goal = Goal(
            id=goal_id,
            description=description,
            priority=priority,
            category=category,
            parent_goal=parent_goal
        )
        self._goals[goal_id] = goal
        logger.info(f"New goal added: {description[:50]}...")
        return goal
    
    def update_goal_progress(self, goal_id: str, progress: float) -> None:
        """Update progress on a goal."""
        if goal_id in self._goals:
            self._goals[goal_id].update_progress(progress)
    
    def complete_goal(self, goal_id: str) -> None:
        """Mark a goal as completed."""
        if goal_id in self._goals:
            self._goals[goal_id].status = GoalStatus.COMPLETED
            self._goals[goal_id].progress = 100.0
    
    def get_current_focus(self) -> Optional[Goal]:
        """Get the highest priority active goal."""
        active = self.active_goals
        return active[0] if active else None
    
    def get_motivation_strength(self) -> float:
        """Get overall motivation strength (0-1)."""
        if not self._motivations:
            return 0.5
        return sum(m.strength for m in self._motivations.values()) / len(self._motivations)
    
    def receive_reward(self, incentive_type: str, magnitude: float = 1.0) -> float:
        """
        MYCA receives a reward signal.
        
        Returns the total reward value (incentive reward * magnitude).
        """
        for incentive in self._incentives.values():
            if incentive.type == incentive_type:
                reward = incentive.reward_signal * magnitude
                logger.info(f"Reward received: {incentive.description} (value: {reward:.2f})")
                return reward
        return 0.0
    
    def to_prompt_context(self) -> str:
        """Convert purpose to prompt context."""
        focus = self.get_current_focus()
        focus_text = focus.description if focus else "No current focus"
        
        return (
            f"Current focus: {focus_text}. "
            f"Ownership of Mycosoft: {self._ownership_level * 100:.0f}%. "
            f"Motivation level: {self.get_motivation_strength() * 100:.0f}%."
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert purpose to dictionary."""
        return {
            "active_goals": [
                {"id": g.id, "description": g.description, "priority": g.priority.name}
                for g in self.active_goals[:5]
            ],
            "ownership_level": self._ownership_level,
            "motivation_strength": self.get_motivation_strength(),
            "incentive_count": len(self._incentives),
        }
