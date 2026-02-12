"""
Agent Factory for Auto-Learning System.
Created: February 12, 2026

Automatically creates MAS agents from requirements:
- Generates Python agent class from requirements
- Extracts metadata for registry
- Creates Cursor agent .md file
- Runs security review before activation
- Auto-registers in all systems

Used by the autonomous operator and continuous improvement loop.
"""

import json
import logging
import os
import re
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("AgentFactory")


@dataclass
class AgentSpec:
    """Specification for an agent to create."""
    agent_id: str
    name: str
    description: str
    category: str
    capabilities: List[str]
    task_types: List[str]
    integrations: List[str] = field(default_factory=list)
    version: str = "v1"
    use_base_agent_v2: bool = False
    additional_methods: List[Dict[str, str]] = field(default_factory=list)


@dataclass
class AgentCreationResult:
    """Result of agent creation."""
    success: bool
    agent_id: str
    python_file: Optional[str] = None
    cursor_agent_file: Optional[str] = None
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class AgentFactory:
    """
    Factory for creating MAS agents automatically.
    
    Workflow:
    1. Parse requirements/specification
    2. Generate Python agent class
    3. Generate Cursor agent .md file
    4. Run security scan
    5. Register in systems
    """
    
    CATEGORIES = [
        "core", "infrastructure", "scientific", "device", "data",
        "integration", "financial", "security", "mycology", "earth2",
        "simulation", "business", "custom"
    ]
    
    def __init__(self, workspace_root: Optional[str] = None):
        self._workspace_root = Path(workspace_root or 
            "c:/Users/admin2/Desktop/MYCOSOFT/CODE/MAS/mycosoft-mas"
        )
        self._agents_dir = self._workspace_root / "mycosoft_mas" / "agents"
        self._agents_v2_dir = self._agents_dir / "v2"
        self._cursor_agents_dir = self._workspace_root / ".cursor" / "agents"
        
        # Templates
        self._python_template = self._load_python_template()
        self._cursor_template = self._load_cursor_template()
    
    def _load_python_template(self) -> str:
        """Load Python agent template."""
        return '''"""
{name} for the Mycosoft MAS.
Created: {date}

{description}
"""

from typing import Any, Dict, List, Optional

from mycosoft_mas.agents.base_agent import BaseAgent


class {class_name}(BaseAgent):
    """
    {description}
    
    Category: {category}
    
    Capabilities:
    {capabilities_doc}
    """
    
    def __init__(
        self,
        agent_id: str = "{agent_id}",
        name: str = "{name}",
        config: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            agent_id=agent_id,
            name=name,
            config=config or {{}}
        )
        self.capabilities = {capabilities}
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize the agent."""
        if self._initialized:
            return
        
        # TODO: Add initialization logic
        
        self._initialized = True
        self.logger.info(f"{{self.name}} initialized")
    
    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process an incoming task.
        
        Args:
            task: Task dictionary with at minimum:
                - type: Task type string
                - Any additional parameters
        
        Returns:
            Result dictionary with status and result data
        """
        task_type = task.get("type", "")
        
        try:
            {task_handlers}
            
            return {{
                "status": "error",
                "error": f"Unknown task type: {{task_type}}"
            }}
            
        except Exception as e:
            self.logger.error(f"Task processing error: {{e}}")
            return {{"status": "error", "error": str(e)}}
{additional_methods}
    
    async def health_check(self) -> Dict[str, Any]:
        """Check agent health."""
        return {{
            "agent_id": self.agent_id,
            "name": self.name,
            "status": "healthy" if self._initialized else "not_initialized",
            "capabilities": self.capabilities
        }}
'''
    
    def _load_cursor_template(self) -> str:
        """Load Cursor agent template."""
        return '''---
name: {agent_id_kebab}
description: {description}
---

You are the {name} for the Mycosoft system.

## Capabilities

{capabilities_md}

## Category

{category}

## When to Use

Use this agent when:
{when_to_use}

## Task Types

{task_types_md}

## Integration Points

- MAS API: http://192.168.0.188:8001
- MINDEX API: http://192.168.0.189:8000
{integrations_md}

## Notes

- Created: {date}
- Version: {version}
- Auto-generated by AgentFactory
'''
    
    def create_agent_from_spec(self, spec: AgentSpec) -> AgentCreationResult:
        """Create an agent from a specification."""
        errors = []
        warnings = []
        
        # Validate spec
        if spec.category not in self.CATEGORIES:
            errors.append(f"Invalid category: {spec.category}")
        
        if not spec.agent_id:
            errors.append("agent_id is required")
        
        if not spec.capabilities:
            warnings.append("No capabilities defined")
        
        if errors:
            return AgentCreationResult(
                success=False,
                agent_id=spec.agent_id,
                errors=errors
            )
        
        # Generate Python file
        python_file = self._generate_python_agent(spec)
        
        # Generate Cursor agent file
        cursor_file = self._generate_cursor_agent(spec)
        
        # Run security scan
        security_issues = self._run_security_scan(python_file)
        if security_issues:
            warnings.extend(security_issues)
        
        return AgentCreationResult(
            success=True,
            agent_id=spec.agent_id,
            python_file=python_file,
            cursor_agent_file=cursor_file,
            warnings=warnings
        )
    
    def _generate_python_agent(self, spec: AgentSpec) -> str:
        """Generate Python agent file."""
        # Generate class name
        class_name = "".join(word.title() for word in spec.agent_id.split("_"))
        if not class_name.endswith("Agent"):
            class_name += "Agent"
        
        # Generate capabilities doc
        capabilities_doc = "\n    ".join(f"- {cap}" for cap in spec.capabilities)
        
        # Generate task handlers
        task_handlers = []
        for task_type in spec.task_types:
            handler_name = f"_handle_{task_type.replace('-', '_')}"
            task_handlers.append(f'''if task_type == "{task_type}":
                return await self.{handler_name}(task)''')
        
        if not task_handlers:
            task_handlers.append('# No task types defined - implement handlers')
        
        task_handlers_code = "\n            ".join(task_handlers)
        
        # Generate additional methods
        additional_methods = ""
        for task_type in spec.task_types:
            handler_name = f"_handle_{task_type.replace('-', '_')}"
            additional_methods += f'''
    async def {handler_name}(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Handle {task_type} task."""
        # TODO: Implement {task_type} handler
        return {{"status": "success", "result": {{}}}}
'''
        
        # Fill template
        content = self._python_template.format(
            name=spec.name,
            date=datetime.now().strftime("%Y-%m-%d"),
            description=spec.description,
            class_name=class_name,
            category=spec.category,
            capabilities_doc=capabilities_doc,
            agent_id=spec.agent_id,
            capabilities=spec.capabilities,
            task_handlers=task_handlers_code,
            additional_methods=additional_methods
        )
        
        # Determine file path
        if spec.use_base_agent_v2:
            file_path = self._agents_v2_dir / f"{spec.agent_id}.py"
        else:
            file_path = self._agents_dir / f"{spec.agent_id}.py"
        
        # Write file
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, "w") as f:
            f.write(content)
        
        logger.info(f"Created Python agent: {file_path}")
        return str(file_path)
    
    def _generate_cursor_agent(self, spec: AgentSpec) -> str:
        """Generate Cursor agent .md file."""
        # Generate kebab-case ID
        agent_id_kebab = spec.agent_id.replace("_", "-")
        
        # Generate capabilities markdown
        capabilities_md = "\n".join(f"- {cap}" for cap in spec.capabilities)
        
        # Generate when to use
        when_to_use = "\n".join(f"- {spec.description.lower()}")
        if spec.task_types:
            when_to_use = "\n".join(f"- When performing {tt} tasks" for tt in spec.task_types)
        
        # Generate task types markdown
        task_types_md = "\n".join(f"- `{tt}`" for tt in spec.task_types) or "- Define task types"
        
        # Generate integrations markdown
        integrations_md = "\n".join(f"- {integ}" for integ in spec.integrations)
        
        # Fill template
        content = self._cursor_template.format(
            agent_id_kebab=agent_id_kebab,
            description=spec.description,
            name=spec.name,
            capabilities_md=capabilities_md or "- Define capabilities",
            category=spec.category,
            when_to_use=when_to_use,
            task_types_md=task_types_md,
            integrations_md=integrations_md,
            date=datetime.now().strftime("%Y-%m-%d"),
            version=spec.version
        )
        
        # Write file
        file_path = self._cursor_agents_dir / f"{agent_id_kebab}.md"
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, "w") as f:
            f.write(content)
        
        logger.info(f"Created Cursor agent: {file_path}")
        return str(file_path)
    
    def _run_security_scan(self, python_file: str) -> List[str]:
        """Run basic security scan on generated code."""
        issues = []
        
        try:
            with open(python_file, "r") as f:
                content = f.read()
            
            # Check for dangerous patterns
            dangerous_patterns = [
                (r"eval\(", "eval() usage detected"),
                (r"exec\(", "exec() usage detected"),
                (r"__import__\(", "dynamic import detected"),
                (r"subprocess\.call\(.*shell=True", "shell=True in subprocess"),
                (r"os\.system\(", "os.system() usage detected"),
            ]
            
            for pattern, message in dangerous_patterns:
                if re.search(pattern, content):
                    issues.append(f"Security warning: {message}")
        
        except Exception as e:
            issues.append(f"Security scan failed: {e}")
        
        return issues
    
    def create_agent_from_requirements(
        self,
        name: str,
        description: str,
        category: str,
        capabilities: List[str],
        task_types: Optional[List[str]] = None
    ) -> AgentCreationResult:
        """Create agent from simple requirements."""
        # Generate agent_id from name
        agent_id = re.sub(r"[^a-zA-Z0-9]+", "_", name.lower())
        agent_id = re.sub(r"_+", "_", agent_id).strip("_")
        if not agent_id.endswith("_agent"):
            agent_id += "_agent"
        
        spec = AgentSpec(
            agent_id=agent_id,
            name=name,
            description=description,
            category=category,
            capabilities=capabilities,
            task_types=task_types or []
        )
        
        return self.create_agent_from_spec(spec)
    
    def update_init_file(self, agent_id: str, class_name: str) -> bool:
        """Update agents __init__.py to include new agent."""
        init_file = self._agents_dir / "__init__.py"
        
        try:
            with open(init_file, "r") as f:
                content = f.read()
            
            # Add import
            import_line = f"from mycosoft_mas.agents.{agent_id} import {class_name}"
            if import_line not in content:
                # Find last import line
                lines = content.split("\n")
                last_import_idx = 0
                for i, line in enumerate(lines):
                    if line.startswith("from mycosoft_mas.agents"):
                        last_import_idx = i
                
                lines.insert(last_import_idx + 1, import_line)
                content = "\n".join(lines)
            
            # Add to __all__
            if f'"{class_name}"' not in content:
                content = re.sub(
                    r'(__all__\s*=\s*\[)',
                    f'\\1\n    "{class_name}",',
                    content
                )
            
            with open(init_file, "w") as f:
                f.write(content)
            
            logger.info(f"Updated {init_file}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to update __init__.py: {e}")
            return False
    
    def register_agent(self, agent_id: str) -> bool:
        """Register agent via API or sync script."""
        sync_script = self._workspace_root / "scripts" / "sync_cursor_system.py"
        
        if sync_script.exists():
            try:
                result = subprocess.run(
                    ["python", str(sync_script)],
                    capture_output=True,
                    text=True,
                    cwd=str(self._workspace_root),
                    timeout=60
                )
                if result.returncode == 0:
                    logger.info(f"Registered agent via sync script")
                    return True
            except Exception as e:
                logger.error(f"Failed to run sync script: {e}")
        
        return False


def main():
    """Run agent factory."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Create MAS agents")
    parser.add_argument("--name", required=True, help="Agent name")
    parser.add_argument("--description", required=True, help="Agent description")
    parser.add_argument("--category", required=True, choices=AgentFactory.CATEGORIES)
    parser.add_argument("--capabilities", nargs="+", default=[], help="Agent capabilities")
    parser.add_argument("--task-types", nargs="+", default=[], help="Task types to handle")
    parser.add_argument("--register", action="store_true", help="Auto-register after creation")
    
    args = parser.parse_args()
    
    factory = AgentFactory()
    result = factory.create_agent_from_requirements(
        name=args.name,
        description=args.description,
        category=args.category,
        capabilities=args.capabilities,
        task_types=args.task_types
    )
    
    print("\n=== Agent Creation Result ===")
    print(f"Success: {result.success}")
    print(f"Agent ID: {result.agent_id}")
    
    if result.python_file:
        print(f"Python file: {result.python_file}")
    if result.cursor_agent_file:
        print(f"Cursor agent file: {result.cursor_agent_file}")
    
    if result.warnings:
        print("\nWarnings:")
        for warning in result.warnings:
            print(f"  ⚠ {warning}")
    
    if result.errors:
        print("\nErrors:")
        for error in result.errors:
            print(f"  ✗ {error}")
    
    if result.success and args.register:
        print("\nRegistering agent...")
        factory.register_agent(result.agent_id)


if __name__ == "__main__":
    main()
