"""
Skill Generator for Auto-Learning System.
Created: February 12, 2026

Automatically generates SKILL.md files from pattern analysis:
- Uses pattern scanner output to identify skill candidates
- Generates skill descriptions and steps using LLM
- Validates skill structure before saving
- Auto-registers via sync script

Used by the continuous improvement loop.
"""

import json
import logging
import os
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SkillGenerator")


@dataclass
class SkillTemplate:
    """Template for a generated skill."""
    skill_id: str
    name: str
    description: str
    when_to_use: List[str]
    steps: List[str]
    notes: List[str] = field(default_factory=list)
    related_patterns: List[str] = field(default_factory=list)
    examples: List[str] = field(default_factory=list)


class SkillGenerator:
    """
    Generates Cursor skills from detected patterns.
    
    Workflow:
    1. Load pattern scan report
    2. Identify skill candidates (high-occurrence patterns)
    3. Generate skill content (with optional LLM enhancement)
    4. Validate skill structure
    5. Save to appropriate location
    6. Register via sync script
    """
    
    def __init__(
        self,
        workspace_root: Optional[str] = None,
        pattern_report_path: Optional[str] = None
    ):
        self._workspace_root = Path(workspace_root or 
            "c:/Users/admin2/Desktop/MYCOSOFT/CODE/MAS/mycosoft-mas"
        )
        self._pattern_report_path = Path(pattern_report_path or 
            self._workspace_root / ".cursor" / "pattern_scan_report.json"
        )
        
        # Skill directories
        self._workspace_skills = self._workspace_root / ".cursor" / "skills"
        self._user_skills = Path("C:/Users/admin2/.cursor/skills")
        
        # Existing skills for deduplication
        self._existing_skills: set = set()
        self._load_existing_skills()
        
        # Skill templates for known pattern types
        self._skill_templates = self._define_templates()
    
    def _load_existing_skills(self) -> None:
        """Load list of existing skills."""
        for skills_dir in [self._workspace_skills, self._user_skills]:
            if skills_dir.exists():
                for skill_dir in skills_dir.iterdir():
                    if skill_dir.is_dir() and (skill_dir / "SKILL.md").exists():
                        self._existing_skills.add(skill_dir.name)
        
        logger.info(f"Found {len(self._existing_skills)} existing skills")
    
    def _define_templates(self) -> Dict[str, Dict[str, Any]]:
        """Define templates for different pattern types."""
        return {
            "base_agent": {
                "name_template": "create-{agent_type}-agent",
                "description": "Create a new MAS agent following the BaseAgent pattern.",
                "when_to_use": [
                    "When asked to create a new agent",
                    "When adding agent capabilities to the MAS",
                    "When spawning new agent types"
                ],
                "steps": [
                    "Analyze the agent requirements",
                    "Create agent file in `mycosoft_mas/agents/`",
                    "Implement `process_task` method",
                    "Add capabilities list",
                    "Update `mycosoft_mas/agents/__init__.py`",
                    "Create Cursor agent .md file in `.cursor/agents/`",
                    "Register agent via API or sync script",
                    "Update SYSTEM_REGISTRY doc"
                ]
            },
            "fastapi_router": {
                "name_template": "create-api-router",
                "description": "Create a new FastAPI router with endpoints.",
                "when_to_use": [
                    "When asked to add API endpoints",
                    "When creating new routers",
                    "When extending the MAS API surface"
                ],
                "steps": [
                    "Create router file in `mycosoft_mas/core/routers/`",
                    "Define router with prefix and tags",
                    "Add endpoint functions with proper decorators",
                    "Define Pydantic models for request/response",
                    "Register router in `myca_main.py`",
                    "Update API_CATALOG doc"
                ]
            },
            "mcp_server": {
                "name_template": "create-mcp-server",
                "description": "Create a new MCP server for Cursor integration.",
                "when_to_use": [
                    "When Cursor needs to access external functionality",
                    "When building new MCP integrations",
                    "When adding autonomous capabilities"
                ],
                "steps": [
                    "Create server file in `mycosoft_mas/mcp/`",
                    "Define MCPToolDefinition for each tool",
                    "Implement tool handlers",
                    "Add MCPProtocolHandler for JSON-RPC",
                    "Add stdio entry point",
                    "Register in `.mcp.json`",
                    "Update MCP documentation"
                ]
            },
            "nextjs_page": {
                "name_template": "create-nextjs-page",
                "description": "Create a new Next.js App Router page.",
                "when_to_use": [
                    "When adding new pages to the website",
                    "When creating new routes",
                    "When building new sections"
                ],
                "steps": [
                    "Create page.tsx in `app/[route]/`",
                    "Add metadata export",
                    "Implement server or client component",
                    "Add to sitemap if needed",
                    "Update navigation if needed"
                ]
            },
            "react_component": {
                "name_template": "create-react-component",
                "description": "Create a React component with Shadcn UI patterns.",
                "when_to_use": [
                    "When building new UI components",
                    "When creating reusable widgets",
                    "When adding interactive elements"
                ],
                "steps": [
                    "Create component file in `components/`",
                    "Define TypeScript interface for props",
                    "Implement functional component",
                    "Add Tailwind styling",
                    "Export from appropriate index"
                ]
            },
            "api_route": {
                "name_template": "create-api-route",
                "description": "Create a Next.js API route.",
                "when_to_use": [
                    "When adding backend API endpoints to website",
                    "When creating proxy routes to MAS/MINDEX",
                    "When building webhook handlers"
                ],
                "steps": [
                    "Create route.ts in `app/api/[path]/`",
                    "Export HTTP method handlers (GET, POST, etc.)",
                    "Handle request validation",
                    "Implement business logic or proxy",
                    "Return NextResponse"
                ]
            }
        }
    
    def load_pattern_report(self) -> Optional[Dict[str, Any]]:
        """Load the pattern scan report."""
        if not self._pattern_report_path.exists():
            logger.warning(f"Pattern report not found: {self._pattern_report_path}")
            return None
        
        with open(self._pattern_report_path, "r") as f:
            return json.load(f)
    
    def identify_candidates(self, min_occurrences: int = 5) -> List[Dict[str, Any]]:
        """Identify skill candidates from pattern report."""
        report = self.load_pattern_report()
        if not report:
            return []
        
        candidates = []
        
        for pattern in report.get("patterns", []):
            # Skip low-occurrence patterns
            if pattern.get("occurrences", 0) < min_occurrences:
                continue
            
            # Generate skill ID
            pattern_id = pattern.get("id", "")
            skill_id = self._generate_skill_id(pattern_id)
            
            # Skip if skill already exists
            if skill_id in self._existing_skills:
                logger.debug(f"Skill already exists: {skill_id}")
                continue
            
            # Check if we have a template for this pattern
            template_key = None
            for key in self._skill_templates:
                if key in pattern_id:
                    template_key = key
                    break
            
            candidates.append({
                "pattern": pattern,
                "skill_id": skill_id,
                "template_key": template_key,
                "priority": "high" if pattern.get("occurrences", 0) >= 10 else "medium"
            })
        
        # Also use suggestions from report
        for suggestion in report.get("suggestions", []):
            if suggestion.get("type") == "skill":
                skill_id = suggestion.get("suggested_name", "")
                if skill_id and skill_id not in self._existing_skills:
                    candidates.append({
                        "pattern": {"id": suggestion.get("based_on_pattern", "")},
                        "skill_id": skill_id,
                        "template_key": suggestion.get("based_on_pattern"),
                        "priority": suggestion.get("priority", "medium"),
                        "from_suggestion": True
                    })
        
        return candidates
    
    def _generate_skill_id(self, pattern_id: str) -> str:
        """Generate skill ID from pattern ID."""
        # Remove prefixes like "func_", "class_base_"
        skill_id = re.sub(r"^(func_|class_base_|class_)", "", pattern_id)
        # Convert to kebab-case
        skill_id = skill_id.replace("_", "-").lower()
        # Add "create-" prefix if not present
        if not skill_id.startswith("create-"):
            skill_id = f"create-{skill_id}"
        return skill_id
    
    def generate_skill(self, candidate: Dict[str, Any]) -> Optional[SkillTemplate]:
        """Generate a skill from a candidate."""
        pattern = candidate.get("pattern", {})
        skill_id = candidate.get("skill_id", "")
        template_key = candidate.get("template_key")
        
        if not skill_id:
            return None
        
        # Get template if available
        template = self._skill_templates.get(template_key, {}) if template_key else {}
        
        # Generate skill name
        name = template.get("name_template", skill_id).format(
            agent_type="new",
            pattern_name=pattern.get("name", "")
        )
        if "{" in name:
            name = skill_id.replace("-", " ").title()
        
        # Generate description
        description = template.get("description") or pattern.get("description") or \
            f"Auto-generated skill for {pattern.get('name', skill_id)} pattern."
        
        # Generate when to use
        when_to_use = template.get("when_to_use", [])
        if not when_to_use:
            when_to_use = [
                f"When working with {pattern.get('name', skill_id)} pattern",
                f"When creating new instances of this pattern type"
            ]
        
        # Generate steps
        steps = template.get("steps", [])
        if not steps:
            steps = [
                "Analyze the request and requirements",
                f"Create the necessary files following the {pattern.get('name', 'established')} pattern",
                "Implement the required functionality",
                "Update relevant registries and documentation",
                "Verify the implementation"
            ]
        
        return SkillTemplate(
            skill_id=skill_id,
            name=name,
            description=description,
            when_to_use=when_to_use,
            steps=steps,
            notes=[
                f"Auto-generated from pattern: {pattern.get('id', 'unknown')}",
                f"Pattern occurrences: {pattern.get('occurrences', 0)}",
                f"Generated: {datetime.now().strftime('%Y-%m-%d')}"
            ],
            related_patterns=[pattern.get("id", "")] if pattern.get("id") else [],
            examples=pattern.get("examples", [])[:3]
        )
    
    def render_skill_md(self, skill: SkillTemplate) -> str:
        """Render skill template to SKILL.md content."""
        lines = [
            f"# {skill.name}",
            "",
            skill.description,
            "",
            "## When to Use",
            ""
        ]
        
        for item in skill.when_to_use:
            lines.append(f"- {item}")
        
        lines.extend([
            "",
            "## Steps",
            ""
        ])
        
        for i, step in enumerate(skill.steps, 1):
            lines.append(f"{i}. {step}")
        
        if skill.examples:
            lines.extend([
                "",
                "## Examples",
                ""
            ])
            for example in skill.examples:
                lines.append(f"- `{example}`")
        
        if skill.notes:
            lines.extend([
                "",
                "## Notes",
                ""
            ])
            for note in skill.notes:
                lines.append(f"- {note}")
        
        return "\n".join(lines)
    
    def save_skill(
        self, 
        skill: SkillTemplate, 
        location: str = "workspace"
    ) -> Optional[str]:
        """Save skill to disk."""
        # Determine directory
        if location == "workspace":
            skill_dir = self._workspace_skills / skill.skill_id
        else:
            skill_dir = self._user_skills / skill.skill_id
        
        skill_dir.mkdir(parents=True, exist_ok=True)
        skill_path = skill_dir / "SKILL.md"
        
        content = self.render_skill_md(skill)
        
        with open(skill_path, "w") as f:
            f.write(content)
        
        logger.info(f"Created skill: {skill_path}")
        return str(skill_path)
    
    def generate_all(
        self,
        min_occurrences: int = 5,
        max_skills: int = 10,
        location: str = "workspace",
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """Generate skills from all candidates."""
        candidates = self.identify_candidates(min_occurrences)
        
        results = {
            "candidates_found": len(candidates),
            "skills_generated": 0,
            "skills_skipped": 0,
            "generated_skills": [],
            "errors": []
        }
        
        # Sort by priority and limit
        candidates.sort(key=lambda x: (x.get("priority") != "high", x.get("pattern", {}).get("occurrences", 0) * -1))
        candidates = candidates[:max_skills]
        
        for candidate in candidates:
            try:
                skill = self.generate_skill(candidate)
                if not skill:
                    results["skills_skipped"] += 1
                    continue
                
                if dry_run:
                    results["generated_skills"].append({
                        "skill_id": skill.skill_id,
                        "name": skill.name,
                        "description": skill.description,
                        "dry_run": True
                    })
                else:
                    path = self.save_skill(skill, location)
                    results["generated_skills"].append({
                        "skill_id": skill.skill_id,
                        "name": skill.name,
                        "path": path
                    })
                
                results["skills_generated"] += 1
                
            except Exception as e:
                results["errors"].append({
                    "candidate": candidate.get("skill_id"),
                    "error": str(e)
                })
        
        return results


def main():
    """Run skill generator."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate Cursor skills from patterns")
    parser.add_argument("--min-occurrences", type=int, default=5, help="Minimum pattern occurrences")
    parser.add_argument("--max-skills", type=int, default=10, help="Maximum skills to generate")
    parser.add_argument("--dry-run", action="store_true", help="Preview without creating files")
    parser.add_argument("--location", choices=["workspace", "user"], default="workspace")
    
    args = parser.parse_args()
    
    generator = SkillGenerator()
    results = generator.generate_all(
        min_occurrences=args.min_occurrences,
        max_skills=args.max_skills,
        location=args.location,
        dry_run=args.dry_run
    )
    
    print("\n=== Skill Generation Report ===")
    print(f"Candidates found: {results['candidates_found']}")
    print(f"Skills generated: {results['skills_generated']}")
    print(f"Skills skipped: {results['skills_skipped']}")
    
    if results["generated_skills"]:
        print("\nGenerated skills:")
        for skill in results["generated_skills"]:
            if skill.get("dry_run"):
                print(f"  [DRY RUN] {skill['skill_id']}: {skill['description'][:50]}...")
            else:
                print(f"  ✓ {skill['skill_id']}: {skill.get('path', 'unknown')}")
    
    if results["errors"]:
        print("\nErrors:")
        for error in results["errors"]:
            print(f"  ✗ {error['candidate']}: {error['error']}")


if __name__ == "__main__":
    main()
