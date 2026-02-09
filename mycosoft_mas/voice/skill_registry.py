"""
Skill Registry for MYCA Voice System
Created: February 4, 2026

Central registry for tracking all learned capabilities across agents.
Supports skill sharing, versioning, and analytics.
"""

import logging
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import json
import os as os_module
from pathlib import Path
import hashlib

logger = logging.getLogger(__name__)


class SkillSource(Enum):
    """Source of a skill."""
    BUILTIN = "builtin"
    LEARNED = "learned"
    IMPORTED = "imported"
    SHARED = "shared"
    USER_DEFINED = "user_defined"


class SkillVisibility(Enum):
    """Visibility level of a skill."""
    PRIVATE = "private"      # Only the owning agent
    SHARED = "shared"        # Specific agents
    PUBLIC = "public"        # All agents


@dataclass
class SkillDependency:
    """A dependency of a skill."""
    skill_id: str
    required: bool = True
    min_version: Optional[int] = None


@dataclass
class SkillEntry:
    """An entry in the skill registry."""
    skill_id: str
    name: str
    description: str
    category: str
    owner_agent: str
    source: SkillSource
    visibility: SkillVisibility
    
    # Version info
    version: int = 1
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    # Execution info
    execution_endpoint: Optional[str] = None
    required_permissions: List[str] = field(default_factory=list)
    dependencies: List[SkillDependency] = field(default_factory=list)
    
    # Sharing info
    shared_with: Set[str] = field(default_factory=set)
    
    # Usage stats
    usage_count: int = 0
    success_count: int = 0
    last_used: Optional[datetime] = None
    
    # Tags and metadata
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def success_rate(self) -> float:
        if self.usage_count == 0:
            return 0.0
        return self.success_count / self.usage_count
    
    def can_access(self, agent_id: str) -> bool:
        """Check if an agent can access this skill."""
        if self.visibility == SkillVisibility.PUBLIC:
            return True
        if self.owner_agent == agent_id:
            return True
        if self.visibility == SkillVisibility.SHARED:
            return agent_id in self.shared_with
        return False


@dataclass
class SkillSearchResult:
    """Result of a skill search."""
    skill: SkillEntry
    relevance_score: float
    match_reason: str


class SkillRegistry:
    """
    Central registry for all agent skills.
    
    Features:
    - Register and discover skills
    - Skill sharing between agents
    - Version tracking
    - Usage analytics
    - Dependency management
    """
    
    def __init__(self, storage_path: Optional[str] = None):
        self.storage_path = storage_path
        self.skills: Dict[str, SkillEntry] = {}
        self.skills_by_agent: Dict[str, Set[str]] = {}
        self.skills_by_category: Dict[str, Set[str]] = {}
        self.skills_by_tag: Dict[str, Set[str]] = {}
        
        # Register built-in skills
        self._register_builtin_skills()
        
        # Load persisted skills
        if storage_path:
            self._load_from_storage()
        
        logger.info(f"SkillRegistry initialized with {len(self.skills)} skills")
    
    def _register_builtin_skills(self):
        """Register built-in system skills."""
        builtins = [
            SkillEntry(
                skill_id="system.speak",
                name="Speak",
                description="Convert text to speech and announce via voice",
                category="communication",
                owner_agent="system",
                source=SkillSource.BUILTIN,
                visibility=SkillVisibility.PUBLIC,
                tags=["voice", "tts", "output"],
            ),
            SkillEntry(
                skill_id="system.listen",
                name="Listen",
                description="Capture voice input and convert to text",
                category="communication",
                owner_agent="system",
                source=SkillSource.BUILTIN,
                visibility=SkillVisibility.PUBLIC,
                tags=["voice", "stt", "input"],
            ),
            SkillEntry(
                skill_id="system.memory.save",
                name="Save to Memory",
                description="Store information in persistent memory",
                category="memory",
                owner_agent="memory-manager",
                source=SkillSource.BUILTIN,
                visibility=SkillVisibility.PUBLIC,
                tags=["memory", "storage", "persistence"],
            ),
            SkillEntry(
                skill_id="system.memory.recall",
                name="Recall from Memory",
                description="Retrieve information from memory",
                category="memory",
                owner_agent="memory-manager",
                source=SkillSource.BUILTIN,
                visibility=SkillVisibility.PUBLIC,
                tags=["memory", "retrieval", "search"],
            ),
            SkillEntry(
                skill_id="system.agent.spawn",
                name="Spawn Agent",
                description="Create and start a new agent instance",
                category="agent_control",
                owner_agent="agent-manager",
                source=SkillSource.BUILTIN,
                visibility=SkillVisibility.SHARED,
                required_permissions=["agent.create"],
                tags=["agent", "management", "spawn"],
            ),
            SkillEntry(
                skill_id="system.workflow.trigger",
                name="Trigger Workflow",
                description="Start an n8n workflow",
                category="automation",
                owner_agent="n8n-agent",
                source=SkillSource.BUILTIN,
                visibility=SkillVisibility.PUBLIC,
                tags=["workflow", "automation", "n8n"],
            ),
        ]
        
        for skill in builtins:
            self.register(skill)
    
    def register(self, skill: SkillEntry) -> bool:
        """Register a new skill."""
        if skill.skill_id in self.skills:
            # Update existing
            existing = self.skills[skill.skill_id]
            skill.version = existing.version + 1
            skill.usage_count = existing.usage_count
            skill.success_count = existing.success_count
        
        self.skills[skill.skill_id] = skill
        
        # Index by agent
        if skill.owner_agent not in self.skills_by_agent:
            self.skills_by_agent[skill.owner_agent] = set()
        self.skills_by_agent[skill.owner_agent].add(skill.skill_id)
        
        # Index by category
        if skill.category not in self.skills_by_category:
            self.skills_by_category[skill.category] = set()
        self.skills_by_category[skill.category].add(skill.skill_id)
        
        # Index by tags
        for tag in skill.tags:
            if tag not in self.skills_by_tag:
                self.skills_by_tag[tag] = set()
            self.skills_by_tag[tag].add(skill.skill_id)
        
        logger.info(f"Registered skill: {skill.skill_id} v{skill.version}")
        return True
    
    def unregister(self, skill_id: str) -> bool:
        """Remove a skill from the registry."""
        if skill_id not in self.skills:
            return False
        
        skill = self.skills[skill_id]
        
        # Remove from indices
        if skill.owner_agent in self.skills_by_agent:
            self.skills_by_agent[skill.owner_agent].discard(skill_id)
        if skill.category in self.skills_by_category:
            self.skills_by_category[skill.category].discard(skill_id)
        for tag in skill.tags:
            if tag in self.skills_by_tag:
                self.skills_by_tag[tag].discard(skill_id)
        
        del self.skills[skill_id]
        logger.info(f"Unregistered skill: {skill_id}")
        return True
    
    def get(self, skill_id: str) -> Optional[SkillEntry]:
        """Get a skill by ID."""
        return self.skills.get(skill_id)
    
    def get_for_agent(self, agent_id: str) -> List[SkillEntry]:
        """Get all skills accessible by an agent."""
        accessible = []
        for skill in self.skills.values():
            if skill.can_access(agent_id):
                accessible.append(skill)
        return accessible
    
    def get_by_category(self, category: str) -> List[SkillEntry]:
        """Get all skills in a category."""
        skill_ids = self.skills_by_category.get(category, set())
        return [self.skills[sid] for sid in skill_ids if sid in self.skills]
    
    def get_by_tag(self, tag: str) -> List[SkillEntry]:
        """Get all skills with a tag."""
        skill_ids = self.skills_by_tag.get(tag, set())
        return [self.skills[sid] for sid in skill_ids if sid in self.skills]
    
    def get_by_owner(self, owner_agent: str) -> List[SkillEntry]:
        """Get all skills owned by an agent."""
        skill_ids = self.skills_by_agent.get(owner_agent, set())
        return [self.skills[sid] for sid in skill_ids if sid in self.skills]
    
    def search(self, query: str, agent_id: Optional[str] = None) -> List[SkillSearchResult]:
        """Search skills by query."""
        results = []
        query_lower = query.lower()
        
        for skill in self.skills.values():
            # Check access
            if agent_id and not skill.can_access(agent_id):
                continue
            
            score = 0.0
            reason = ""
            
            # Name match
            if query_lower in skill.name.lower():
                score += 0.5
                reason = "name match"
            
            # Description match
            if query_lower in skill.description.lower():
                score += 0.3
                reason = reason or "description match"
            
            # Tag match
            if any(query_lower in tag.lower() for tag in skill.tags):
                score += 0.2
                reason = reason or "tag match"
            
            # Category match
            if query_lower in skill.category.lower():
                score += 0.1
                reason = reason or "category match"
            
            if score > 0:
                results.append(SkillSearchResult(
                    skill=skill,
                    relevance_score=score,
                    match_reason=reason,
                ))
        
        # Sort by relevance
        results.sort(key=lambda r: r.relevance_score, reverse=True)
        return results
    
    def share_skill(self, skill_id: str, with_agent: str) -> bool:
        """Share a skill with another agent."""
        if skill_id not in self.skills:
            return False
        
        skill = self.skills[skill_id]
        skill.shared_with.add(with_agent)
        skill.visibility = SkillVisibility.SHARED
        skill.updated_at = datetime.now()
        
        logger.info(f"Shared skill {skill_id} with {with_agent}")
        return True
    
    def revoke_share(self, skill_id: str, from_agent: str) -> bool:
        """Revoke skill sharing from an agent."""
        if skill_id not in self.skills:
            return False
        
        skill = self.skills[skill_id]
        skill.shared_with.discard(from_agent)
        skill.updated_at = datetime.now()
        
        logger.info(f"Revoked skill {skill_id} sharing from {from_agent}")
        return True
    
    def record_usage(self, skill_id: str, success: bool = True):
        """Record skill usage."""
        if skill_id in self.skills:
            skill = self.skills[skill_id]
            skill.usage_count += 1
            if success:
                skill.success_count += 1
            skill.last_used = datetime.now()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get registry statistics."""
        skills = list(self.skills.values())
        return {
            "total_skills": len(skills),
            "by_source": {s.value: len([sk for sk in skills if sk.source == s]) for s in SkillSource},
            "by_visibility": {v.value: len([sk for sk in skills if sk.visibility == v]) for v in SkillVisibility},
            "categories": list(self.skills_by_category.keys()),
            "total_usage": sum(s.usage_count for s in skills),
            "most_used": sorted(skills, key=lambda s: s.usage_count, reverse=True)[:10],
        }
    
    def export_skills(self, agent_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Export skills as serializable data."""
        skills = self.get_for_agent(agent_id) if agent_id else list(self.skills.values())
        return [
            {
                "skill_id": s.skill_id,
                "name": s.name,
                "description": s.description,
                "category": s.category,
                "owner_agent": s.owner_agent,
                "source": s.source.value,
                "visibility": s.visibility.value,
                "version": s.version,
                "tags": s.tags,
                "usage_count": s.usage_count,
                "success_rate": s.success_rate(),
            }
            for s in skills
        ]
    
    def _load_from_storage(self):
        """Load skills from persistent storage."""
        if not self.storage_path or not os_module.path.exists(self.storage_path):
            return
        try:
            with open(self.storage_path, 'r') as f:
                data = json.load(f)
            for skill_data in data.get("skills", []):
                skill = SkillEntry(
                    skill_id=skill_data["skill_id"],
                    name=skill_data["name"],
                    description=skill_data["description"],
                    category=skill_data["category"],
                    owner_agent=skill_data["owner_agent"],
                    source=SkillSource(skill_data.get("source", "learned")),
                    visibility=SkillVisibility(skill_data.get("visibility", "public")),
                    version=skill_data.get("version", 1),
                    tags=skill_data.get("tags", []),
                    usage_count=skill_data.get("usage_count", 0),
                    success_count=skill_data.get("success_count", 0),
                )
                self.register(skill)
            logger.info(f"Loaded {len(data.get('skills', []))} skills from storage")
        except Exception as e:
            logger.error(f"Failed to load skills: {e}")
    
    def save_to_storage(self):
        """Save skills to persistent storage."""
        if not self.storage_path:
            return
        try:
            data = {"skills": self.export_skills()}
            Path(self.storage_path).parent.mkdir(parents=True, exist_ok=True)
            with open(self.storage_path, 'w') as f:
                json.dump(data, f, indent=2, default=str)
            logger.info(f"Saved {len(self.skills)} skills to storage")
        except Exception as e:
            logger.error(f"Failed to save skills: {e}")


# Singleton
_registry_instance: Optional[SkillRegistry] = None


def get_skill_registry() -> SkillRegistry:
    global _registry_instance
    if _registry_instance is None:
        _registry_instance = SkillRegistry()
    return _registry_instance


__all__ = [
    "SkillRegistry",
    "SkillEntry",
    "SkillDependency",
    "SkillSearchResult",
    "SkillSource",
    "SkillVisibility",
    "get_skill_registry",
]
