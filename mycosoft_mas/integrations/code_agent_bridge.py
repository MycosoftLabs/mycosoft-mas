"""
Cowork/Cursor Headless Integration -- Code Agent Bridge

Bridges MYCA to Claude Code CLI and Cursor Server for automated
code generation, testing, linting, and PR creation.
"""

import asyncio
import json
import logging
import os
import subprocess
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class CodeResult:
    files_changed: List[str]
    tests_passed: bool
    commit_sha: Optional[str] = None
    pr_url: Optional[str] = None
    output: str = ""
    error: Optional[str] = None


class CodeAgentBridge:
    """Bridge to Claude Code CLI and Cursor for automated code tasks."""

    def __init__(
        self,
        claude_code_path: str = "claude",
        anthropic_api_key: Optional[str] = None,
    ):
        self._claude_code = claude_code_path
        self._api_key = anthropic_api_key or os.getenv("ANTHROPIC_API_KEY", "")

    async def execute_code_task(
        self,
        task_description: str,
        repo_path: str,
        branch: Optional[str] = None,
        timeout: int = 300,
    ) -> CodeResult:
        """Run Claude Code CLI with a task description against a repo."""
        env = {**os.environ}
        if self._api_key:
            env["ANTHROPIC_API_KEY"] = self._api_key

        cmd = [self._claude_code, "--print", "--dangerously-skip-permissions"]
        if branch:
            cmd.extend(["--branch", branch])

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=repo_path,
                env=env,
            )
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(input=task_description.encode()),
                timeout=timeout,
            )
            output = stdout.decode(errors="replace")
            err = stderr.decode(errors="replace")

            files_changed = await self._get_changed_files(repo_path)
            return CodeResult(
                files_changed=files_changed,
                tests_passed=proc.returncode == 0,
                output=output,
                error=err if proc.returncode != 0 else None,
            )
        except asyncio.TimeoutError:
            return CodeResult(
                files_changed=[], tests_passed=False,
                error=f"Task timed out after {timeout}s",
            )
        except FileNotFoundError:
            return CodeResult(
                files_changed=[], tests_passed=False,
                error=f"Claude Code CLI not found at '{self._claude_code}'",
            )
        except Exception as exc:
            return CodeResult(
                files_changed=[], tests_passed=False, error=str(exc),
            )

    async def run_tests(
        self, repo_path: str, test_command: str = "pytest",
    ) -> CodeResult:
        """Run tests in a repository."""
        try:
            proc = await asyncio.create_subprocess_shell(
                test_command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=repo_path,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)
            return CodeResult(
                files_changed=[],
                tests_passed=proc.returncode == 0,
                output=stdout.decode(errors="replace"),
                error=stderr.decode(errors="replace") if proc.returncode != 0 else None,
            )
        except Exception as exc:
            return CodeResult(files_changed=[], tests_passed=False, error=str(exc))

    async def lint_code(self, repo_path: str) -> CodeResult:
        """Run linter on a repository."""
        try:
            proc = await asyncio.create_subprocess_shell(
                "python -m ruff check . 2>&1 || python -m flake8 . 2>&1",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=repo_path,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=60)
            return CodeResult(
                files_changed=[],
                tests_passed=proc.returncode == 0,
                output=stdout.decode(errors="replace"),
                error=stderr.decode(errors="replace") if proc.returncode != 0 else None,
            )
        except Exception as exc:
            return CodeResult(files_changed=[], tests_passed=False, error=str(exc))

    async def create_pr(
        self,
        repo_path: str,
        branch: str,
        title: str,
        body: str,
    ) -> CodeResult:
        """Create a pull request via GitHub CLI."""
        try:
            proc = await asyncio.create_subprocess_exec(
                "gh", "pr", "create",
                "--title", title,
                "--body", body,
                "--head", branch,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=repo_path,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)
            pr_url = stdout.decode().strip() if proc.returncode == 0 else None
            return CodeResult(
                files_changed=[],
                tests_passed=proc.returncode == 0,
                pr_url=pr_url,
                output=stdout.decode(errors="replace"),
                error=stderr.decode(errors="replace") if proc.returncode != 0 else None,
            )
        except Exception as exc:
            return CodeResult(files_changed=[], tests_passed=False, error=str(exc))

    async def _get_changed_files(self, repo_path: str) -> List[str]:
        try:
            proc = await asyncio.create_subprocess_exec(
                "git", "diff", "--name-only",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=repo_path,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=10)
            return [f for f in stdout.decode().strip().split("\n") if f]
        except Exception:
            return []
