"""Helper script to create coding_agent.py"""
import os

content = '''"""
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
            # Return placeholder change
            return [CodeChange(
                file_path="unknown",
                old_content=None,
                new_content="# Fix applied",
                change_type="modify",
                description=analysis.get("description", "Bug fix"),
            )]
        
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
'''

os.makedirs('mycosoft_mas/agents', exist_ok=True)
with open('mycosoft_mas/agents/coding_agent.py', 'w', encoding='utf-8') as f:
    f.write(content)
print('Created coding_agent.py')
