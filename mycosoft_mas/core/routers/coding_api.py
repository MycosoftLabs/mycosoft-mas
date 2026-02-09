"""
MYCA Autonomous Coding API
Endpoints for MYCA to execute code, manage files, and deploy projects.
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any, Optional, List
from pydantic import BaseModel
from mycosoft_mas.services.autonomous_coding import get_autonomous_coding_service

router = APIRouter(prefix="/coding", tags=["coding"])


class ExecuteCommandRequest(BaseModel):
    """Request to execute a command."""
    command: str
    working_dir: Optional[str] = None
    timeout: int = 300


class RunCodeRequest(BaseModel):
    """Request to run code."""
    code: str
    language: str = "python"  # python, node
    timeout: int = 60


class FileWriteRequest(BaseModel):
    """Request to write a file."""
    path: str
    content: str


class GitCommitRequest(BaseModel):
    """Request to create a git commit."""
    message: str
    working_dir: Optional[str] = None


class GitPushRequest(BaseModel):
    """Request to push to remote."""
    branch: str = "main"
    working_dir: Optional[str] = None


class CreatePRRequest(BaseModel):
    """Request to create a GitHub PR."""
    title: str
    body: str
    head: str
    base: str = "main"
    repo: str = "mycosoft/mycosoft-mas"


@router.post("/execute")
async def execute_command(request: ExecuteCommandRequest) -> Dict[str, Any]:
    """Execute a terminal command."""
    service = get_autonomous_coding_service()
    result = await service.execute_command(
        command=request.command,
        working_dir=request.working_dir,
        timeout=request.timeout,
    )
    return {
        "success": result.success,
        "exit_code": result.exit_code,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "duration_ms": result.duration_ms,
    }


@router.post("/run")
async def run_code(request: RunCodeRequest) -> Dict[str, Any]:
    """Execute code in specified language."""
    service = get_autonomous_coding_service()
    
    if request.language == "python":
        result = await service.run_python(request.code, request.timeout)
    elif request.language == "node":
        result = await service.run_node(request.code, request.timeout)
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported language: {request.language}")
    
    return {
        "success": result.success,
        "exit_code": result.exit_code,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "duration_ms": result.duration_ms,
    }


@router.get("/file/read")
async def read_file(path: str) -> Dict[str, Any]:
    """Read a file."""
    service = get_autonomous_coding_service()
    success, content = await service.read_file(path)
    
    if not success:
        raise HTTPException(status_code=404, detail=content)
    
    return {
        "success": True,
        "path": path,
        "content": content,
        "length": len(content),
    }


@router.post("/file/write")
async def write_file(request: FileWriteRequest) -> Dict[str, Any]:
    """Write to a file."""
    service = get_autonomous_coding_service()
    success, message = await service.write_file(request.path, request.content)
    
    if not success:
        raise HTTPException(status_code=500, detail=message)
    
    return {
        "success": True,
        "path": request.path,
        "message": message,
    }


@router.get("/directory/list")
async def list_directory(path: str = ".") -> Dict[str, Any]:
    """List directory contents."""
    service = get_autonomous_coding_service()
    success, entries = await service.list_directory(path)
    
    return {
        "success": success,
        "path": path,
        "entries": entries,
    }


@router.get("/git/status")
async def git_status(working_dir: Optional[str] = None) -> Dict[str, Any]:
    """Get git status."""
    service = get_autonomous_coding_service()
    return await service.git_status(working_dir)


@router.post("/git/commit")
async def git_commit(request: GitCommitRequest) -> Dict[str, Any]:
    """Create a git commit."""
    service = get_autonomous_coding_service()
    return await service.git_commit(request.message, request.working_dir)


@router.post("/git/push")
async def git_push(request: GitPushRequest) -> Dict[str, Any]:
    """Push to remote."""
    service = get_autonomous_coding_service()
    return await service.git_push(request.branch, request.working_dir)


@router.post("/github/pr")
async def create_pr(request: CreatePRRequest) -> Dict[str, Any]:
    """Create a GitHub Pull Request."""
    service = get_autonomous_coding_service()
    return await service.create_github_pr(
        title=request.title,
        body=request.body,
        head=request.head,
        base=request.base,
        repo=request.repo,
    )


@router.post("/deploy/vercel")
async def deploy_vercel(project_dir: str) -> Dict[str, Any]:
    """Deploy to Vercel."""
    service = get_autonomous_coding_service()
    return await service.deploy_vercel(project_dir)


@router.post("/test")
async def run_tests(working_dir: Optional[str] = None) -> Dict[str, Any]:
    """Run project tests."""
    service = get_autonomous_coding_service()
    return await service.run_tests(working_dir)


@router.get("/history/executions")
async def get_execution_history(limit: int = 50) -> Dict[str, Any]:
    """Get command execution history."""
    service = get_autonomous_coding_service()
    history = await service.get_execution_history(limit)
    return {
        "total": len(history),
        "executions": history,
    }


@router.get("/history/operations")
async def get_operation_history(limit: int = 50) -> Dict[str, Any]:
    """Get file operation history."""
    service = get_autonomous_coding_service()
    history = await service.get_operation_history(limit)
    return {
        "total": len(history),
        "operations": history,
    }


# ============================================================
# Claude Code Integration Endpoints (MYCA Autonomous Coding)
# Added: February 9, 2026
# ============================================================


class ClaudeCodeTaskRequest(BaseModel):
    """Request to execute a coding task via Claude Code."""
    task_type: str  # create_agent, fix_bug, create_endpoint, deploy, general_coding
    description: str
    target_repo: str = "mas"
    target_files: Optional[List[str]] = None
    max_turns: int = 20
    max_budget_usd: float = 5.0
    auto_deploy: bool = False
    require_tests: bool = True


class CreateAgentRequest(BaseModel):
    """Request to create a new MAS agent via Claude Code."""
    description: str
    agent_name: Optional[str] = None
    category: str = "general"


class FixBugRequest(BaseModel):
    """Request to fix a bug via Claude Code."""
    error_description: str
    target_files: Optional[List[str]] = None
    stack_trace: Optional[str] = None


class CreateEndpointRequest(BaseModel):
    """Request to create a new API endpoint via Claude Code."""
    description: str
    prefix: Optional[str] = None
    methods: List[str] = ["GET"]


class DeployRequest(BaseModel):
    """Request to deploy code changes."""
    target_vm: str = "mas"  # mas, website, mindex


@router.post("/claude/task")
async def claude_code_task(request: ClaudeCodeTaskRequest) -> Dict[str, Any]:
    """Submit a general coding task to Claude Code on the Sandbox VM."""
    from mycosoft_mas.agents.coding_agent import get_coding_agent
    agent = get_coding_agent()
    result = await agent.invoke_claude_code(
        task_description=request.description,
        target_repo=request.target_repo,
        max_turns=request.max_turns,
        max_budget=request.max_budget_usd,
    )
    return {
        "task_type": request.task_type,
        "result": result,
        "auto_deploy": request.auto_deploy,
    }


@router.post("/claude/create-agent")
async def claude_create_agent(request: CreateAgentRequest) -> Dict[str, Any]:
    """Create a new MAS agent using Claude Code."""
    from mycosoft_mas.agents.coding_agent import get_coding_agent
    agent = get_coding_agent()
    result = await agent.create_agent_via_claude(request.description)
    return {"task_type": "create_agent", "result": result}


@router.post("/claude/fix-bug")
async def claude_fix_bug(request: FixBugRequest) -> Dict[str, Any]:
    """Fix a bug using Claude Code."""
    from mycosoft_mas.agents.coding_agent import get_coding_agent
    agent = get_coding_agent()
    description = request.error_description
    if request.stack_trace:
        description += f"\n\nStack trace:\n{request.stack_trace}"
    result = await agent.fix_bug_via_claude(description, request.target_files)
    return {"task_type": "fix_bug", "result": result}


@router.post("/claude/create-endpoint")
async def claude_create_endpoint(request: CreateEndpointRequest) -> Dict[str, Any]:
    """Create a new API endpoint using Claude Code."""
    from mycosoft_mas.agents.coding_agent import get_coding_agent
    agent = get_coding_agent()
    result = await agent.create_endpoint_via_claude(request.description)
    return {"task_type": "create_endpoint", "result": result}


@router.post("/claude/deploy")
async def claude_deploy(request: DeployRequest) -> Dict[str, Any]:
    """Deploy code changes to a VM using Claude Code."""
    from mycosoft_mas.agents.coding_agent import get_coding_agent
    agent = get_coding_agent()
    result = await agent.deploy_via_claude(request.target_vm)
    return {"task_type": "deploy", "target_vm": request.target_vm, "result": result}


@router.get("/claude/health")
async def claude_code_health() -> Dict[str, Any]:
    """Check if Claude Code is available on the Sandbox VM."""
    import asyncio
    import os
    try:
        key_path = os.environ.get("MAS_SSH_KEY_PATH")
        if key_path and os.path.exists(key_path):
            ssh_cmd = f'ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 -o IdentitiesOnly=yes -i {key_path} mycosoft@192.168.0.187 "claude --version"'
        else:
            ssh_cmd = 'ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 mycosoft@192.168.0.187 "claude --version"'
        proc = await asyncio.create_subprocess_shell(
            ssh_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=10)
        version = stdout.decode().strip()
        if proc.returncode == 0:
            return {"status": "available", "version": version, "vm": "192.168.0.187"}
        return {"status": "unavailable", "error": stderr.decode().strip()}
    except Exception as e:
        return {"status": "unavailable", "error": str(e)}
