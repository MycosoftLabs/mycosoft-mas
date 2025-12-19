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
