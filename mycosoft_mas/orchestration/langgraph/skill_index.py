"""
Skill Index - Progressive Disclosure via SKILL.md Files
Date: January 27, 2026
"""
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass


@dataclass
class Skill:
    name: str
    description: str
    version: str
    tags: List[str]
    path: str
    body: Optional[str] = None
    
    def to_metadata_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "tags": self.tags,
            "path": self.path,
        }
    
    def to_full_dict(self) -> Dict[str, Any]:
        return {**self.to_metadata_dict(), "body": self.body}


class SkillIndex:
    def __init__(self, skills_dir: str = ".deepagents/skills"):
        self.skills_dir = Path(skills_dir)
        self.skills: Dict[str, Skill] = {}
        self.skill_usage: Dict[str, int] = {}
    
    def load_index(self) -> int:
        self.skills.clear()
        if not self.skills_dir.exists():
            return 0
        
        for skill_dir in self.skills_dir.iterdir():
            if skill_dir.is_dir():
                skill_file = skill_dir / "SKILL.md"
                if skill_file.exists():
                    skill = self._parse_skill_file(skill_file)
                    if skill:
                        self.skills[skill.name] = skill
        return len(self.skills)
    
    def _parse_skill_file(self, path: Path) -> Optional[Skill]:
        try:
            content = path.read_text(encoding="utf-8")
            if content.startswith("---"):
                parts = content.split("---", 2)
                if len(parts) >= 3:
                    frontmatter = yaml.safe_load(parts[1])
                    body = parts[2].strip()
                    return Skill(
                        name=frontmatter.get("name", path.parent.name),
                        description=frontmatter.get("description", ""),
                        version=frontmatter.get("version", "1.0"),
                        tags=frontmatter.get("tags", []),
                        path=str(path),
                        body=body,
                    )
            return Skill(
                name=path.parent.name,
                description="",
                version="1.0",
                tags=[],
                path=str(path),
                body=content,
            )
        except Exception as e:
            print(f"Error parsing skill {path}: {e}")
            return None
    
    def list_skills(self) -> List[Dict[str, Any]]:
        return [skill.to_metadata_dict() for skill in self.skills.values()]
    
    def get_skill(self, name: str, include_body: bool = False) -> Optional[Dict[str, Any]]:
        skill = self.skills.get(name)
        if not skill:
            return None
        self.skill_usage[name] = self.skill_usage.get(name, 0) + 1
        return skill.to_full_dict() if include_body else skill.to_metadata_dict()
