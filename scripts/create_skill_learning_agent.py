"""Helper script to create skill_learning_agent.py"""
import os

content = '''"""
Skill Learning Agent for MYCA Voice System
Created: February 4, 2026

Agent that learns new skills through LLM interactions, stores them,
and announces completion. Supports dynamic capability expansion.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import json
import hashlib

logger = logging.getLogger(__name__)


class SkillStatus(Enum):
    LEARNING = "learning"
    LEARNED = "learned"
    FAILED = "failed"
    DEPRECATED = "deprecated"


class SkillCategory(Enum):
    CODING = "coding"
    INFRASTRUCTURE = "infrastructure"
    BUSINESS = "business"
    SCIENTIFIC = "scientific"
    COMMUNICATION = "communication"
    AUTOMATION = "automation"
    ANALYSIS = "analysis"
    GENERAL = "general"


@dataclass
class LearnedSkill:
    """A skill that has been learned by the agent."""
    skill_id: str
    name: str
    description: str
    category: SkillCategory
    status: SkillStatus
    learned_at: datetime
    source: str  # How it was learned (llm, demonstration, documentation)
    
    # Execution info
    execution_steps: List[str] = field(default_factory=list)
    required_tools: List[str] = field(default_factory=list)
    required_agents: List[str] = field(default_factory=list)
    
    # Performance metrics
    usage_count: int = 0
    success_count: int = 0
    last_used: Optional[datetime] = None
    average_execution_time: float = 0.0
    
    # LLM-generated content
    prompt_template: Optional[str] = None
    example_inputs: List[str] = field(default_factory=list)
    example_outputs: List[str] = field(default_factory=list)
    
    # Metadata
    version: int = 1
    parent_skill_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def success_rate(self) -> float:
        if self.usage_count == 0:
            return 0.0
        return self.success_count / self.usage_count


@dataclass
class LearningTask:
    """A task to learn a new skill."""
    task_id: str
    skill_description: str
    requested_by: str
    requested_at: datetime
    status: str = "pending"
    result: Optional[LearnedSkill] = None
    error: Optional[str] = None


class SkillLearningAgent:
    """
    Agent that learns new skills dynamically through LLM.
    
    Features:
    - Learn skills from natural language descriptions
    - Store and retrieve learned skills
    - Execute skills with learned procedures
    - Announce completion via voice
    - Share skills with other agents
    """
    
    def __init__(
        self,
        llm_client: Optional[Any] = None,
        voice_announcer: Optional[Callable[[str], None]] = None,
        skill_storage_path: Optional[str] = None,
    ):
        self.llm_client = llm_client
        self.voice_announcer = voice_announcer
        self.skill_storage_path = skill_storage_path
        
        self.skills: Dict[str, LearnedSkill] = {}
        self.learning_tasks: Dict[str, LearningTask] = {}
        
        # Load existing skills
        if skill_storage_path:
            self._load_skills()
        
        logger.info(f"SkillLearningAgent initialized with {len(self.skills)} skills")
    
    async def learn(self, skill_description: str, user_id: str = "system") -> LearnedSkill:
        """
        Learn a new skill from a natural language description.
        
        Args:
            skill_description: What skill to learn
            user_id: Who requested learning this skill
            
        Returns:
            The learned skill
        """
        task_id = hashlib.md5(f"{skill_description}{datetime.now().isoformat()}".encode()).hexdigest()[:16]
        
        task = LearningTask(
            task_id=task_id,
            skill_description=skill_description,
            requested_by=user_id,
            requested_at=datetime.now(),
            status="learning",
        )
        self.learning_tasks[task_id] = task
        
        logger.info(f"Starting to learn: {skill_description}")
        
        if self.voice_announcer:
            self.voice_announcer(f"I'm learning how to {skill_description}. This may take a moment.")
        
        try:
            # Generate skill using LLM
            skill = await self._generate_skill_from_llm(skill_description)
            
            # Store the skill
            self.skills[skill.skill_id] = skill
            
            # Update task
            task.status = "completed"
            task.result = skill
            
            # Save skills
            if self.skill_storage_path:
                self._save_skills()
            
            # Announce completion
            announcement = self._generate_completion_announcement(skill)
            if self.voice_announcer:
                self.voice_announcer(announcement)
            
            logger.info(f"Successfully learned skill: {skill.name} ({skill.skill_id})")
            return skill
            
        except Exception as e:
            task.status = "failed"
            task.error = str(e)
            logger.error(f"Failed to learn skill: {e}")
            
            if self.voice_announcer:
                self.voice_announcer(f"I wasn't able to learn that skill. {str(e)}")
            
            raise
    
    async def _generate_skill_from_llm(self, description: str) -> LearnedSkill:
        """Generate a skill definition using LLM."""
        
        # If no LLM client, create a basic skill structure
        if not self.llm_client:
            return self._create_basic_skill(description)
        
        prompt = f"""You are a skill learning system. Generate a detailed skill definition for the following:

Skill to learn: {description}

Provide the response as JSON with the following structure:
{{
    "name": "short skill name",
    "description": "detailed description",
    "category": "one of: coding, infrastructure, business, scientific, communication, automation, analysis, general",
    "execution_steps": ["step 1", "step 2", ...],
    "required_tools": ["tool1", "tool2", ...],
    "required_agents": ["agent1", "agent2", ...],
    "prompt_template": "template for executing this skill with {{input}} placeholder",
    "example_inputs": ["example input 1", "example input 2"],
    "example_outputs": ["expected output 1", "expected output 2"]
}}
"""
        
        try:
            response = await self.llm_client.generate(prompt)
            skill_data = json.loads(response)
            
            skill_id = hashlib.md5(skill_data["name"].encode()).hexdigest()[:12]
            
            return LearnedSkill(
                skill_id=skill_id,
                name=skill_data["name"],
                description=skill_data["description"],
                category=SkillCategory(skill_data.get("category", "general")),
                status=SkillStatus.LEARNED,
                learned_at=datetime.now(),
                source="llm",
                execution_steps=skill_data.get("execution_steps", []),
                required_tools=skill_data.get("required_tools", []),
                required_agents=skill_data.get("required_agents", []),
                prompt_template=skill_data.get("prompt_template"),
                example_inputs=skill_data.get("example_inputs", []),
                example_outputs=skill_data.get("example_outputs", []),
            )
        except Exception as e:
            logger.warning(f"LLM skill generation failed, using basic: {e}")
            return self._create_basic_skill(description)
    
    def _create_basic_skill(self, description: str) -> LearnedSkill:
        """Create a basic skill without LLM."""
        skill_id = hashlib.md5(description.encode()).hexdigest()[:12]
        
        # Infer category from description
        category = SkillCategory.GENERAL
        desc_lower = description.lower()
        if any(w in desc_lower for w in ["code", "program", "deploy", "git"]):
            category = SkillCategory.CODING
        elif any(w in desc_lower for w in ["server", "container", "docker", "network"]):
            category = SkillCategory.INFRASTRUCTURE
        elif any(w in desc_lower for w in ["report", "financial", "invoice", "budget"]):
            category = SkillCategory.BUSINESS
        elif any(w in desc_lower for w in ["analyze", "data", "research", "experiment"]):
            category = SkillCategory.SCIENTIFIC
        
        return LearnedSkill(
            skill_id=skill_id,
            name=description[:50],
            description=description,
            category=category,
            status=SkillStatus.LEARNED,
            learned_at=datetime.now(),
            source="basic",
            execution_steps=[f"Execute: {description}"],
        )
    
    def _generate_completion_announcement(self, skill: LearnedSkill) -> str:
        """Generate a voice announcement for skill completion."""
        announcements = [
            f"I've learned how to {skill.description}. I can now help you with this.",
            f"Got it! I now know how to {skill.name}. Just ask when you need this.",
            f"Skill learned: {skill.name}. I'm ready to use this capability.",
            f"I've figured out {skill.description}. This is now part of my skill set.",
        ]
        import random
        return random.choice(announcements)
    
    async def execute_skill(self, skill_id: str, input_data: Any) -> Any:
        """Execute a learned skill."""
        if skill_id not in self.skills:
            raise ValueError(f"Skill not found: {skill_id}")
        
        skill = self.skills[skill_id]
        skill.usage_count += 1
        skill.last_used = datetime.now()
        
        start_time = datetime.now()
        
        try:
            # If we have an LLM client and prompt template, use it
            if self.llm_client and skill.prompt_template:
                prompt = skill.prompt_template.replace("{input}", str(input_data))
                result = await self.llm_client.generate(prompt)
            else:
                # Basic execution - just return the steps
                result = {"steps": skill.execution_steps, "input": input_data}
            
            skill.success_count += 1
            
            # Update average execution time
            execution_time = (datetime.now() - start_time).total_seconds()
            if skill.average_execution_time == 0:
                skill.average_execution_time = execution_time
            else:
                skill.average_execution_time = (skill.average_execution_time + execution_time) / 2
            
            return result
            
        except Exception as e:
            logger.error(f"Skill execution failed: {e}")
            raise
    
    def get_skill(self, skill_id: str) -> Optional[LearnedSkill]:
        """Get a skill by ID."""
        return self.skills.get(skill_id)
    
    def search_skills(self, query: str) -> List[LearnedSkill]:
        """Search skills by name or description."""
        query_lower = query.lower()
        return [
            skill for skill in self.skills.values()
            if query_lower in skill.name.lower() or query_lower in skill.description.lower()
        ]
    
    def get_skills_by_category(self, category: SkillCategory) -> List[LearnedSkill]:
        """Get all skills in a category."""
        return [s for s in self.skills.values() if s.category == category]
    
    def get_all_skills(self) -> List[LearnedSkill]:
        """Get all learned skills."""
        return list(self.skills.values())
    
    def forget_skill(self, skill_id: str) -> bool:
        """Remove a skill."""
        if skill_id in self.skills:
            self.skills[skill_id].status = SkillStatus.DEPRECATED
            del self.skills[skill_id]
            if self.skill_storage_path:
                self._save_skills()
            return True
        return False
    
    def get_skill_stats(self) -> Dict[str, Any]:
        """Get statistics about learned skills."""
        skills = list(self.skills.values())
        return {
            "total_skills": len(skills),
            "by_category": {cat.value: len([s for s in skills if s.category == cat]) for cat in SkillCategory},
            "by_status": {st.value: len([s for s in skills if s.status == st]) for st in SkillStatus},
            "total_usage": sum(s.usage_count for s in skills),
            "average_success_rate": sum(s.success_rate() for s in skills) / len(skills) if skills else 0,
            "most_used": sorted(skills, key=lambda s: s.usage_count, reverse=True)[:5],
        }
    
    def _load_skills(self):
        """Load skills from storage."""
        if not self.skill_storage_path:
            return
        try:
            import os
            if os.path.exists(self.skill_storage_path):
                with open(self.skill_storage_path, 'r') as f:
                    data = json.load(f)
                for skill_data in data.get("skills", []):
                    skill = LearnedSkill(
                        skill_id=skill_data["skill_id"],
                        name=skill_data["name"],
                        description=skill_data["description"],
                        category=SkillCategory(skill_data.get("category", "general")),
                        status=SkillStatus(skill_data.get("status", "learned")),
                        learned_at=datetime.fromisoformat(skill_data["learned_at"]),
                        source=skill_data.get("source", "unknown"),
                        execution_steps=skill_data.get("execution_steps", []),
                        required_tools=skill_data.get("required_tools", []),
                        required_agents=skill_data.get("required_agents", []),
                        prompt_template=skill_data.get("prompt_template"),
                        usage_count=skill_data.get("usage_count", 0),
                        success_count=skill_data.get("success_count", 0),
                    )
                    self.skills[skill.skill_id] = skill
                logger.info(f"Loaded {len(self.skills)} skills from storage")
        except Exception as e:
            logger.error(f"Failed to load skills: {e}")
    
    def _save_skills(self):
        """Save skills to storage."""
        if not self.skill_storage_path:
            return
        try:
            data = {
                "skills": [
                    {
                        "skill_id": s.skill_id,
                        "name": s.name,
                        "description": s.description,
                        "category": s.category.value,
                        "status": s.status.value,
                        "learned_at": s.learned_at.isoformat(),
                        "source": s.source,
                        "execution_steps": s.execution_steps,
                        "required_tools": s.required_tools,
                        "required_agents": s.required_agents,
                        "prompt_template": s.prompt_template,
                        "usage_count": s.usage_count,
                        "success_count": s.success_count,
                    }
                    for s in self.skills.values()
                ]
            }
            import os
            os.makedirs(os.path.dirname(self.skill_storage_path), exist_ok=True)
            with open(self.skill_storage_path, 'w') as f:
                json.dump(data, f, indent=2)
            logger.info(f"Saved {len(self.skills)} skills to storage")
        except Exception as e:
            logger.error(f"Failed to save skills: {e}")


# Singleton instance
_agent_instance: Optional[SkillLearningAgent] = None


def get_skill_learning_agent() -> SkillLearningAgent:
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = SkillLearningAgent()
    return _agent_instance


__all__ = [
    "SkillLearningAgent",
    "LearnedSkill",
    "LearningTask",
    "SkillStatus",
    "SkillCategory",
    "get_skill_learning_agent",
]
'''

os.makedirs('mycosoft_mas/agents', exist_ok=True)
with open('mycosoft_mas/agents/skill_learning_agent.py', 'w', encoding='utf-8') as f:
    f.write(content)
print('Created skill_learning_agent.py')
