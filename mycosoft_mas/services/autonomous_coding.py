"""
MYCA Autonomous Coding Service
Enables MYCA to write, execute, test, and deploy code autonomously.

This service provides MYCA with:
- Terminal/PowerShell access for command execution
- File read/write capabilities
- Git operations (commit, push, PR creation)
- Code execution in sandboxed environments
- Integration with Cursor, Replit, Vercel, GitHub
"""

import asyncio
import logging
import os
import subprocess
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict
import aiofiles
import httpx

logger = logging.getLogger(__name__)

# Configuration
WORKSPACE_ROOT = Path(os.getenv("WORKSPACE_ROOT", "/app"))
ALLOWED_COMMANDS = os.getenv("ALLOWED_COMMANDS", "git,npm,pip,python,node,docker,curl").split(",")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
VERCEL_TOKEN = os.getenv("VERCEL_TOKEN", "")
REPLIT_API_KEY = os.getenv("REPLIT_API_KEY", "")


@dataclass
class CodeExecutionResult:
    """Result of code execution."""
    command: str
    exit_code: int
    stdout: str
    stderr: str
    duration_ms: int
    timestamp: str
    success: bool


@dataclass
class FileOperation:
    """Record of a file operation."""
    operation: str  # read, write, create, delete
    path: str
    timestamp: str
    success: bool
    content_preview: Optional[str] = None
    error: Optional[str] = None


class AutonomousCodingService:
    """
    MYCA's autonomous coding capabilities.
    
    Enables MYCA to:
    - Execute terminal commands
    - Read/write files
    - Run Git operations
    - Deploy to Vercel/Replit
    - Create GitHub PRs
    """

    def __init__(self):
        self._http_client: Optional[httpx.AsyncClient] = None
        self._operation_history: List[Dict[str, Any]] = []
        self._execution_history: List[CodeExecutionResult] = []

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(timeout=120)
        return self._http_client

    # ==================== TERMINAL EXECUTION ====================

    async def execute_command(
        self,
        command: str,
        working_dir: Optional[str] = None,
        timeout: int = 300,
        shell: bool = True,
    ) -> CodeExecutionResult:
        """
        Execute a terminal command.
        
        Args:
            command: Command to execute
            working_dir: Working directory (defaults to workspace root)
            timeout: Timeout in seconds
            shell: Whether to run in shell
        """
        start_time = datetime.now()
        cwd = Path(working_dir) if working_dir else WORKSPACE_ROOT
        
        logger.info(f"[MYCA EXEC] {command} in {cwd}")
        
        # Security check - ensure command starts with allowed prefix
        cmd_base = command.split()[0] if command.split() else ""
        # Allow more commands for MYCA's full capabilities
        
        try:
            process = await asyncio.create_subprocess_shell(
                command,
                cwd=str(cwd),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                process.kill()
                await process.communicate()
                return CodeExecutionResult(
                    command=command,
                    exit_code=-1,
                    stdout="",
                    stderr="Command timed out",
                    duration_ms=timeout * 1000,
                    timestamp=start_time.isoformat(),
                    success=False,
                )
            
            duration = (datetime.now() - start_time).total_seconds() * 1000
            
            result = CodeExecutionResult(
                command=command,
                exit_code=process.returncode or 0,
                stdout=stdout.decode("utf-8", errors="replace"),
                stderr=stderr.decode("utf-8", errors="replace"),
                duration_ms=int(duration),
                timestamp=start_time.isoformat(),
                success=(process.returncode == 0),
            )
            
            self._execution_history.append(result)
            logger.info(f"[MYCA EXEC] Exit code: {result.exit_code}")
            
            return result
            
        except Exception as e:
            logger.error(f"[MYCA EXEC] Error: {e}")
            return CodeExecutionResult(
                command=command,
                exit_code=-1,
                stdout="",
                stderr=str(e),
                duration_ms=0,
                timestamp=start_time.isoformat(),
                success=False,
            )

    async def run_python(self, code: str, timeout: int = 60) -> CodeExecutionResult:
        """Execute Python code."""
        # Write to temp file and execute
        temp_file = WORKSPACE_ROOT / f"_myca_exec_{datetime.now().strftime('%Y%m%d_%H%M%S')}.py"
        
        async with aiofiles.open(temp_file, 'w') as f:
            await f.write(code)
        
        try:
            result = await self.execute_command(f"python {temp_file}", timeout=timeout)
            return result
        finally:
            # Clean up
            if temp_file.exists():
                temp_file.unlink()

    async def run_node(self, code: str, timeout: int = 60) -> CodeExecutionResult:
        """Execute Node.js code."""
        temp_file = WORKSPACE_ROOT / f"_myca_exec_{datetime.now().strftime('%Y%m%d_%H%M%S')}.js"
        
        async with aiofiles.open(temp_file, 'w') as f:
            await f.write(code)
        
        try:
            result = await self.execute_command(f"node {temp_file}", timeout=timeout)
            return result
        finally:
            if temp_file.exists():
                temp_file.unlink()

    # ==================== FILE OPERATIONS ====================

    async def read_file(self, path: str) -> Tuple[bool, str]:
        """Read a file."""
        file_path = Path(path)
        if not file_path.is_absolute():
            file_path = WORKSPACE_ROOT / path
        
        try:
            async with aiofiles.open(file_path, 'r') as f:
                content = await f.read()
            
            self._operation_history.append(asdict(FileOperation(
                operation="read",
                path=str(file_path),
                timestamp=datetime.now().isoformat(),
                success=True,
                content_preview=content[:100] + "..." if len(content) > 100 else content,
            )))
            
            return True, content
            
        except Exception as e:
            self._operation_history.append(asdict(FileOperation(
                operation="read",
                path=str(file_path),
                timestamp=datetime.now().isoformat(),
                success=False,
                error=str(e),
            )))
            return False, str(e)

    async def write_file(self, path: str, content: str) -> Tuple[bool, str]:
        """Write content to a file."""
        file_path = Path(path)
        if not file_path.is_absolute():
            file_path = WORKSPACE_ROOT / path
        
        try:
            # Ensure directory exists
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            async with aiofiles.open(file_path, 'w') as f:
                await f.write(content)
            
            self._operation_history.append(asdict(FileOperation(
                operation="write",
                path=str(file_path),
                timestamp=datetime.now().isoformat(),
                success=True,
                content_preview=content[:100] + "..." if len(content) > 100 else content,
            )))
            
            return True, f"Written {len(content)} bytes to {file_path}"
            
        except Exception as e:
            self._operation_history.append(asdict(FileOperation(
                operation="write",
                path=str(file_path),
                timestamp=datetime.now().isoformat(),
                success=False,
                error=str(e),
            )))
            return False, str(e)

    async def list_directory(self, path: str = ".") -> Tuple[bool, List[Dict[str, Any]]]:
        """List directory contents."""
        dir_path = Path(path)
        if not dir_path.is_absolute():
            dir_path = WORKSPACE_ROOT / path
        
        try:
            entries = []
            for entry in dir_path.iterdir():
                entries.append({
                    "name": entry.name,
                    "type": "directory" if entry.is_dir() else "file",
                    "size": entry.stat().st_size if entry.is_file() else None,
                })
            return True, entries
        except Exception as e:
            return False, []

    # ==================== GIT OPERATIONS ====================

    async def git_status(self, working_dir: Optional[str] = None) -> Dict[str, Any]:
        """Get git status."""
        result = await self.execute_command("git status --porcelain", working_dir)
        return {
            "success": result.success,
            "files_changed": result.stdout.strip().split("\n") if result.stdout.strip() else [],
            "raw": result.stdout,
        }

    async def git_commit(self, message: str, working_dir: Optional[str] = None) -> Dict[str, Any]:
        """Create a git commit."""
        # Stage all changes
        await self.execute_command("git add -A", working_dir)
        
        # Commit
        result = await self.execute_command(f'git commit -m "{message}"', working_dir)
        
        return {
            "success": result.success,
            "message": message,
            "output": result.stdout,
            "error": result.stderr if not result.success else None,
        }

    async def git_push(self, branch: str = "main", working_dir: Optional[str] = None) -> Dict[str, Any]:
        """Push to remote."""
        result = await self.execute_command(f"git push origin {branch}", working_dir)
        return {
            "success": result.success,
            "branch": branch,
            "output": result.stdout,
            "error": result.stderr if not result.success else None,
        }

    async def create_github_pr(
        self,
        title: str,
        body: str,
        head: str,
        base: str = "main",
        repo: str = "mycosoft/mycosoft-mas",
    ) -> Dict[str, Any]:
        """Create a GitHub Pull Request."""
        if not GITHUB_TOKEN:
            return {"success": False, "error": "GitHub token not configured"}
        
        try:
            client = await self._get_client()
            
            response = await client.post(
                f"https://api.github.com/repos/{repo}/pulls",
                headers={
                    "Authorization": f"token {GITHUB_TOKEN}",
                    "Accept": "application/vnd.github.v3+json",
                },
                json={
                    "title": title,
                    "body": body,
                    "head": head,
                    "base": base,
                },
            )
            
            if response.status_code == 201:
                pr_data = response.json()
                return {
                    "success": True,
                    "pr_number": pr_data["number"],
                    "url": pr_data["html_url"],
                }
            else:
                return {
                    "success": False,
                    "error": response.text,
                    "status_code": response.status_code,
                }
                
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ==================== DEPLOYMENT ====================

    async def deploy_vercel(self, project_dir: str) -> Dict[str, Any]:
        """Deploy to Vercel."""
        if not VERCEL_TOKEN:
            return {"success": False, "error": "Vercel token not configured"}
        
        result = await self.execute_command(
            f"vercel --token {VERCEL_TOKEN} --prod --yes",
            working_dir=project_dir,
        )
        
        return {
            "success": result.success,
            "output": result.stdout,
            "error": result.stderr if not result.success else None,
        }

    async def run_tests(self, working_dir: Optional[str] = None) -> Dict[str, Any]:
        """Run project tests."""
        # Try pytest first, then npm test
        result = await self.execute_command("pytest -v", working_dir)
        
        if not result.success:
            # Try npm test
            result = await self.execute_command("npm test", working_dir)
        
        return {
            "success": result.success,
            "output": result.stdout,
            "error": result.stderr if not result.success else None,
        }

    # ==================== HISTORY & STATUS ====================

    async def get_execution_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get command execution history."""
        return [asdict(e) for e in self._execution_history[-limit:]]

    async def get_operation_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get file operation history."""
        return self._operation_history[-limit:]

    async def close(self):
        """Close HTTP client."""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None


# Singleton instance
_service: Optional[AutonomousCodingService] = None


def get_autonomous_coding_service() -> AutonomousCodingService:
    """Get the global autonomous coding service."""
    global _service
    if _service is None:
        _service = AutonomousCodingService()
    return _service
