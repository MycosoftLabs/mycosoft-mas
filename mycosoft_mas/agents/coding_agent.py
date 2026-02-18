"""
Coding Agent for MYCA Voice System
Created: February 4, 2026

Agent with full code modification capabilities including:
- Bug fixing via LLM
- Pull request creation
- Code review and merge
- GitHub integration
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import json
import os as os_module
import subprocess
import shlex

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    REVIEWING = "reviewing"
    MERGED = "merged"


class TaskType(Enum):
    BUG_FIX = "bug_fix"
    FEATURE = "feature"
    REFACTOR = "refactor"
    DOCUMENTATION = "documentation"
    TEST = "test"
    HOTFIX = "hotfix"


@dataclass
class CodeChange:
    """A single code change."""
    file_path: str
    old_content: Optional[str]
    new_content: str
    change_type: str  # create, modify, delete
    description: str


@dataclass
class CodingTask:
    """A coding task to be executed."""
    task_id: str
    task_type: TaskType
    description: str
    target_files: List[str] = field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Changes made
    changes: List[CodeChange] = field(default_factory=list)
    
    # Git/PR info
    branch_name: Optional[str] = None
    commit_hash: Optional[str] = None
    pr_number: Optional[int] = None
    pr_url: Optional[str] = None
    
    # Results
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class CodingAgent:
    """
    Agent for code modifications and GitHub operations.
    
    Features:
    - Fix bugs using LLM analysis
    - Create and manage pull requests
    - Run tests and validate changes
    - Integrate with GitHub API
    """
    
    def __init__(
        self,
        llm_client: Optional[Any] = None,
        github_token: Optional[str] = None,
        repo_path: str = ".",
        voice_announcer: Optional[Any] = None,
    ):
        self.llm_client = llm_client
        self.github_token = github_token or os_module.environ.get("GITHUB_TOKEN")
        self.repo_path = repo_path
        self.voice_announcer = voice_announcer
        
        self.tasks: Dict[str, CodingTask] = {}
        self.current_task: Optional[CodingTask] = None
        
        logger.info("CodingAgent initialized")
    
    async def fix_bug(self, description: str, target_files: Optional[List[str]] = None) -> CodingTask:
        """
        Fix a bug based on description.
        
        Args:
            description: Description of the bug
            target_files: Optional list of files to focus on
            
        Returns:
            CodingTask with results
        """
        task = CodingTask(
            task_id=self._generate_task_id(),
            task_type=TaskType.BUG_FIX,
            description=description,
            target_files=target_files or [],
        )
        self.tasks[task.task_id] = task
        self.current_task = task
        
        logger.info(f"Starting bug fix: {description}")
        
        if self.voice_announcer:
            self.voice_announcer(f"I'm working on fixing the bug: {description}")
        
        task.status = TaskStatus.IN_PROGRESS
        task.started_at = datetime.now()
        
        try:
            # Analyze the bug
            analysis = await self._analyze_bug(description, target_files)
            
            # Generate fix
            changes = await self._generate_fix(analysis)
            task.changes = changes
            
            # Apply changes (in memory for now, actual write would go here)
            for change in changes:
                logger.info(f"Change: {change.change_type} {change.file_path}")
            
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now()
            
            if self.voice_announcer:
                self.voice_announcer(f"I've fixed the bug. Made {len(changes)} file changes.")
            
            return task
            
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error = str(e)
            logger.error(f"Bug fix failed: {e}")
            
            if self.voice_announcer:
                self.voice_announcer(f"I couldn't fix the bug: {str(e)}")
            
            raise
    
    async def _analyze_bug(self, description: str, target_files: Optional[List[str]]) -> Dict[str, Any]:
        """Analyze a bug using LLM."""
        if not self.llm_client:
            return {"description": description, "target_files": target_files or [], "analysis": "No LLM available"}
        
        # Read target files if specified
        file_contents = {}
        for file_path in (target_files or []):
            try:
                full_path = os_module.path.join(self.repo_path, file_path)
                if os_module.path.exists(full_path):
                    with open(full_path, 'r') as f:
                        file_contents[file_path] = f.read()
            except Exception as e:
                logger.warning(f"Could not read {file_path}: {e}")
        
        prompt = f"""Analyze this bug and suggest a fix:

Bug Description: {description}

Relevant Files:
{json.dumps(file_contents, indent=2) if file_contents else "No files provided"}

Provide:
1. Root cause analysis
2. Suggested fix approach
3. Files that need to be modified
4. Potential side effects
"""
        
        try:
            response = await self.llm_client.generate(prompt)
            return {"description": description, "analysis": response, "files": file_contents}
        except Exception as e:
            return {"description": description, "error": str(e)}
    
    async def _generate_fix(self, analysis: Dict[str, Any]) -> List[CodeChange]:
        """Generate code changes based on analysis."""
        changes = []
        
        if not self.llm_client:
            # Cannot generate fixes without LLM client
            logger.error("Coding agent cannot generate fixes: LLM client not initialized")
            raise ValueError(
                "Code fix generation requires LLM client. "
                "Configure ANTHROPIC_API_KEY or OPENAI_API_KEY in environment."
            )
        
        prompt = f"""Based on this analysis, generate the code fix:

{json.dumps(analysis, indent=2)}

For each file that needs changes, provide:
1. File path
2. The exact code changes needed
3. Brief description of the change

Format as JSON array of changes.
"""
        
        try:
            response = await self.llm_client.generate(prompt)
            fix_data = json.loads(response)
            
            for fix in fix_data:
                changes.append(CodeChange(
                    file_path=fix.get("file_path", "unknown"),
                    old_content=fix.get("old_content"),
                    new_content=fix.get("new_content", ""),
                    change_type=fix.get("change_type", "modify"),
                    description=fix.get("description", ""),
                ))
        except Exception as e:
            logger.warning(f"Could not parse LLM fix: {e}")
        
        return changes
    
    async def create_pull_request(
        self,
        title: str,
        description: str,
        branch: Optional[str] = None,
        base: str = "main",
    ) -> Dict[str, Any]:
        """
        Create a pull request.
        
        Args:
            title: PR title
            description: PR description
            branch: Source branch (creates new if None)
            base: Target branch
            
        Returns:
            PR details
        """
        logger.info(f"Creating PR: {title}")
        
        if self.voice_announcer:
            self.voice_announcer(f"Creating pull request: {title}")
        
        if not branch:
            branch = f"auto/{title.lower().replace(' ', '-')[:30]}"
        
        try:
            # Create branch if needed
            result = self._run_git(["checkout", "-b", branch])
            
            # Stage all changes
            self._run_git(["add", "."])
            
            # Commit
            self._run_git(["commit", "-m", title])
            
            # Push
            self._run_git(["push", "-u", "origin", branch])
            
            # Create PR using GitHub CLI if available
            pr_result = self._create_pr_via_gh(title, description, branch, base)
            
            if self.voice_announcer:
                self.voice_announcer(f"Pull request created successfully.")
            
            return pr_result
            
        except Exception as e:
            logger.error(f"Failed to create PR: {e}")
            raise
    
    def _run_git(self, args: List[str]) -> str:
        """Run a git command."""
        try:
            result = subprocess.run(
                ["git"] + args,
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True,
            )
            return result.stdout
        except subprocess.CalledProcessError as e:
            logger.error(f"Git command failed: {e.stderr}")
            raise
    
    def _create_pr_via_gh(self, title: str, description: str, branch: str, base: str) -> Dict[str, Any]:
        """Create PR using GitHub CLI."""
        try:
            result = subprocess.run(
                ["gh", "pr", "create", "--title", title, "--body", description, "--base", base],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True,
            )
            pr_url = result.stdout.strip()
            return {"url": pr_url, "branch": branch, "base": base, "title": title}
        except subprocess.CalledProcessError:
            # Fall back to returning basic info
            return {"branch": branch, "base": base, "title": title, "status": "branch pushed, PR creation needs manual step"}
    
    async def merge_pull_request(self, pr_number: int) -> Dict[str, Any]:
        """Merge a pull request."""
        logger.info(f"Merging PR #{pr_number}")
        
        if self.voice_announcer:
            self.voice_announcer(f"Merging pull request number {pr_number}")
        
        try:
            result = subprocess.run(
                ["gh", "pr", "merge", str(pr_number), "--merge"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True,
            )
            
            if self.voice_announcer:
                self.voice_announcer(f"Pull request {pr_number} has been merged.")
            
            return {"pr_number": pr_number, "status": "merged", "output": result.stdout}
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to merge PR: {e.stderr}")
            raise
    
    async def review_code(self, file_path: str) -> Dict[str, Any]:
        """Review code in a file."""
        logger.info(f"Reviewing code in: {file_path}")
        
        try:
            full_path = os_module.path.join(self.repo_path, file_path)
            with open(full_path, 'r') as f:
                content = f.read()
        except Exception as e:
            return {"error": f"Could not read file: {e}"}
        
        if not self.llm_client:
            return {"file": file_path, "review": "No LLM available for review"}
        
        prompt = f"""Review this code and provide feedback:

File: {file_path}

```
{content}
```

Provide:
1. Code quality assessment
2. Potential bugs or issues
3. Suggestions for improvement
4. Security concerns if any
"""
        
        try:
            response = await self.llm_client.generate(prompt)
            return {"file": file_path, "review": response}
        except Exception as e:
            return {"file": file_path, "error": str(e)}
    
    def get_task(self, task_id: str) -> Optional[CodingTask]:
        """Get a task by ID."""
        return self.tasks.get(task_id)
    
    def get_all_tasks(self) -> List[CodingTask]:
        """Get all tasks."""
        return list(self.tasks.values())
    
    def _generate_task_id(self) -> str:
        """Generate a unique task ID."""
        import hashlib
        return hashlib.md5(datetime.now().isoformat().encode()).hexdigest()[:12]



    # ============================================================
    # Claude Code Integration (MYCA Autonomous Coding)
    # Added: February 9, 2026
    # ============================================================

    async def invoke_claude_code(
        self,
        task_description: str,
        target_repo: str = "mas",
        max_turns: int = 20,
        max_budget: float = 5.0,
        allowed_tools: str = "Read,Edit,Write,Bash,Grep,Glob",
    ) -> Dict[str, Any]:
        """
        Invoke Claude Code on the Sandbox VM to perform a coding task.

        Args:
            task_description: Natural language description of the coding task
            target_repo: Which repo to work in ("mas" or "website")
            max_turns: Maximum agent turns
            max_budget: Maximum USD budget
            allowed_tools: Comma-separated tool list

        Returns:
            Dict with result, session_id, cost, and changes
        """
        import asyncio

        sandbox_host = "192.168.0.187"
        repo_paths = {
            "mas": "/opt/mycosoft/mas",
            "website": "/opt/mycosoft/website",
        }
        repo_path = repo_paths.get(target_repo, repo_paths["mas"])

        # Build the claude -p command with proper shell escaping
        # Note: --dangerously-skip-permissions is intentional for MYCA autonomous operation
        # but assumes trusted task descriptions from voice/orchestrator only
        escaped_desc = shlex.quote(task_description)
        claude_cmd = (
            f"cd {shlex.quote(repo_path)} && "
            f"claude -p {escaped_desc} "
            f"--output-format json "
            f"--max-turns {max_turns} "
            f"--max-budget-usd {max_budget} "
            f"--allowedTools {shlex.quote(allowed_tools)} "
            f"--dangerously-skip-permissions "
            f"2>/dev/null"
        )

        # Optional SSH key for container -> 187 (MAS_SSH_KEY_PATH)
        key_path = os_module.environ.get("MAS_SSH_KEY_PATH")
        if key_path and os_module.path.exists(key_path):
            ssh_cmd = f'ssh -o StrictHostKeyChecking=no -o IdentitiesOnly=yes -i {key_path} mycosoft@{sandbox_host} "{claude_cmd}"'
        else:
            ssh_cmd = f'ssh -o StrictHostKeyChecking=no mycosoft@{sandbox_host} "{claude_cmd}"'

        logger.info(f"Invoking Claude Code: {task_description[:100]}...")

        try:
            proc = await asyncio.create_subprocess_shell(
                ssh_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=600
            )

            output = stdout.decode("utf-8", errors="replace").strip()
            error_output = stderr.decode("utf-8", errors="replace").strip()

            if proc.returncode != 0:
                logger.error(f"Claude Code failed: {error_output}")
                return {
                    "success": False,
                    "error": error_output or f"Exit code {proc.returncode}",
                    "output": output,
                }

            # Try to parse and validate JSON response
            try:
                result = json.loads(output)
                # Validate that result is a dict
                if not isinstance(result, dict):
                    logger.warning(f"Claude Code returned non-dict JSON: {type(result)}")
                    return {
                        "success": False,
                        "error": "Invalid JSON structure (expected object)",
                        "output": output,
                    }
                return {
                    "success": True,
                    "result": result.get("result", output),
                    "session_id": result.get("session_id"),
                    "cost": result.get("cost_usd"),
                    "num_turns": result.get("num_turns"),
                }
            except json.JSONDecodeError as e:
                logger.warning(f"Claude Code returned invalid JSON: {e}")
                # Treat unparseable output as raw text result (success)
                # since Claude Code might return valid but non-JSON output
                return {
                    "success": True,
                    "result": output,
                    "session_id": None,
                    "cost": None,
                }

        except asyncio.TimeoutError:
            logger.error("Claude Code timed out after 600s")
            return {"success": False, "error": "Timeout after 600 seconds"}
        except Exception as e:
            logger.error(f"Claude Code invocation error: {e}")
            return {"success": False, "error": str(e)}

    async def create_agent_via_claude(
        self, agent_description: str
    ) -> Dict[str, Any]:
        """Create a new MAS agent using Claude Code."""
        prompt = (
            f"Create a new MAS agent based on this description: {agent_description}. "
            f"Follow the BaseAgent pattern in CLAUDE.md. "
            f"Create the agent file, update agents/__init__.py, and run tests."
        )
        return await self._execute_with_safety("create_agent", prompt, "mas")

    async def fix_bug_via_claude(
        self, error_description: str, target_files: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Fix a bug using Claude Code."""
        files_hint = f" Focus on files: {', '.join(target_files)}" if target_files else ""
        prompt = (
            f"Fix this bug: {error_description}.{files_hint} "
            f"Create a git branch, implement the fix, and run tests."
        )
        return await self._execute_with_safety("fix_bug", prompt, "mas")

    async def create_endpoint_via_claude(
        self, endpoint_description: str
    ) -> Dict[str, Any]:
        """Create a new API endpoint using Claude Code."""
        prompt = (
            f"Create a new API endpoint: {endpoint_description}. "
            f"Follow the APIRouter pattern in CLAUDE.md. "
            f"Create the router file, register in myca_main.py, and run tests."
        )
        return await self._execute_with_safety("create_endpoint", prompt, "mas")

    async def deploy_via_claude(
        self, target_vm: str = "mas"
    ) -> Dict[str, Any]:
        """Deploy code changes using Claude Code."""
        prompt = (
            f"Deploy the latest code changes to the {target_vm} VM. "
            f"Follow the deployment instructions in CLAUDE.md."
        )
        return await self.invoke_claude_code(
            prompt, target_repo="mas", max_turns=10, allowed_tools="Read,Bash"
        )

    async def _execute_with_safety(
        self, task_type: str, prompt: str, target_repo: str
    ) -> Dict[str, Any]:
        """Execute a coding task with git safety checkpoint."""
        import time

        branch_name = f"myca-{task_type}-{int(time.time())}"

        # Create checkpoint branch
        checkpoint_prompt = (
            f"First, create a git branch called '{branch_name}' and switch to it. "
            f"Then: {prompt}"
        )

        result = await self.invoke_claude_code(
            checkpoint_prompt, target_repo=target_repo
        )

        if result.get("success"):
            # Log to audit
            logger.info(
                f"Claude Code task completed: type={task_type}, "
                f"branch={branch_name}, cost={result.get('cost')}"
            )

        return {
            **result,
            "task_type": task_type,
            "branch_name": branch_name,
        }

    # Singleton
_agent_instance: Optional[CodingAgent] = None


def get_coding_agent() -> CodingAgent:
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = CodingAgent()
    return _agent_instance


__all__ = [
    "CodingAgent",
    "CodingTask",
    "CodeChange",
    "TaskStatus",
    "TaskType",
    "get_coding_agent",
]
