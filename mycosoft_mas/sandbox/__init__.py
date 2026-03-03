"""
Sandbox subsystem for ephemeral Docker container management.

Provides isolated execution environments for MYCA tool calls
(code execution, browser automation, file operations).
"""

from mycosoft_mas.sandbox.container_manager import SandboxManager, SandboxInfo

__all__ = ["SandboxManager", "SandboxInfo"]
