"""Code Sandboxing. Created: February 3, 2026"""
import asyncio
from typing import Any, Dict

class CodeSandbox:
    """Sandboxed code execution environment."""
    
    def __init__(self, timeout_seconds: int = 30, memory_limit_mb: int = 512):
        self.timeout = timeout_seconds
        self.memory_limit = memory_limit_mb
        self.allowed_imports = ["math", "json", "re", "datetime", "uuid"]
    
    async def execute(self, code: str, globals_dict: Dict[str, Any] = None) -> Dict[str, Any]:
        for forbidden in ["os.", "subprocess", "eval", "exec", "__import__"]:
            if forbidden in code:
                return {"success": False, "error": f"Forbidden: {forbidden}"}
        try:
            result = await asyncio.wait_for(self._run_sandboxed(code, globals_dict or {}), timeout=self.timeout)
            return {"success": True, "result": result}
        except asyncio.TimeoutError:
            return {"success": False, "error": "Execution timed out"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _run_sandboxed(self, code: str, globals_dict: Dict[str, Any]) -> Any:
        local_vars = {}
        exec(code, {"__builtins__": {}}, local_vars)
        return local_vars.get("result")
