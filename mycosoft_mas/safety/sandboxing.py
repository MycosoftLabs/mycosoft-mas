"""Code Sandboxing. Created: February 3, 2026"""

import asyncio
import logging
from typing import Any, Dict, Optional

try:
    from RestrictedPython import compile_restricted, safe_globals
    from RestrictedPython.Guards import safer_getattr, guarded_unpack_sequence
    from RestrictedPython.Eval import default_guarded_getitem

    HAS_RESTRICTED_PYTHON = True
except ImportError:
    HAS_RESTRICTED_PYTHON = False

logger = logging.getLogger(__name__)

# Extended blocklist for defense-in-depth (supplements RestrictedPython)
FORBIDDEN_PATTERNS = [
    "os.",
    "subprocess",
    "eval",
    "exec",
    "__import__",
    "importlib",
    "getattr",
    "setattr",
    "delattr",
    "__builtins__",
    "__subclasses__",
    "__bases__",
    "__class__",
    "__globals__",
    "__code__",
    "open(",
    "file(",
    "compile(",
    "execfile",
    "shutil",
    "sys.",
    "signal",
    "ctypes",
    "pickle",
    "shelve",
    "marshal",
]


class CodeSandbox:
    """Sandboxed code execution environment."""

    def __init__(self, timeout_seconds: int = 30, memory_limit_mb: int = 512):
        self.timeout = timeout_seconds
        self.memory_limit = memory_limit_mb
        self.allowed_imports = ["math", "json", "re", "datetime", "uuid"]

    async def execute(
        self, code: str, globals_dict: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        # Defense-in-depth: string-based blocklist as first pass
        code_lower = code.lower()
        for forbidden in FORBIDDEN_PATTERNS:
            if forbidden.lower() in code_lower:
                return {"success": False, "error": f"Forbidden pattern detected: {forbidden}"}
        try:
            result = await asyncio.wait_for(
                self._run_sandboxed(code, globals_dict or {}), timeout=self.timeout
            )
            return {"success": True, "result": result}
        except asyncio.TimeoutError:
            return {"success": False, "error": "Execution timed out"}
        except SyntaxError as e:
            return {"success": False, "error": f"Syntax error in sandboxed code: {e}"}
        except Exception as e:
            logger.warning(f"Sandbox execution failed: {e}")
            return {"success": False, "error": str(e)}

    async def _run_sandboxed(self, code: str, globals_dict: Dict[str, Any]) -> Any:
        local_vars = {}

        if HAS_RESTRICTED_PYTHON:
            # Use RestrictedPython for proper sandboxing
            byte_code = compile_restricted(code, "<sandbox>", "exec")
            restricted_globals = safe_globals.copy()
            restricted_globals.update(
                {
                    "_getattr_": safer_getattr,
                    "_getitem_": default_guarded_getitem,
                    "_getiter_": iter,
                    "_iter_unpack_sequence_": guarded_unpack_sequence,
                    "_print_": lambda *args, **kwargs: None,
                }
            )
            # Inject only whitelisted modules
            for mod_name in self.allowed_imports:
                try:
                    restricted_globals[mod_name] = __import__(mod_name)
                except ImportError:
                    pass
            restricted_globals.update(globals_dict)
            exec(byte_code, restricted_globals, local_vars)
        else:
            # Fallback: restricted exec with no builtins (less secure)
            logger.warning(
                "RestrictedPython not installed - using limited sandbox. "
                "Install with: pip install RestrictedPython"
            )
            safe_builtins = {
                "True": True,
                "False": False,
                "None": None,
                "int": int,
                "float": float,
                "str": str,
                "bool": bool,
                "list": list,
                "dict": dict,
                "tuple": tuple,
                "set": set,
                "len": len,
                "range": range,
                "enumerate": enumerate,
                "zip": zip,
                "map": map,
                "filter": filter,
                "min": min,
                "max": max,
                "sum": sum,
                "abs": abs,
                "round": round,
                "sorted": sorted,
                "reversed": reversed,
                "isinstance": isinstance,
                "type": type,
                "ValueError": ValueError,
                "TypeError": TypeError,
                "KeyError": KeyError,
                "IndexError": IndexError,
            }
            exec(code, {"__builtins__": safe_builtins}, local_vars)

        return local_vars.get("result")
