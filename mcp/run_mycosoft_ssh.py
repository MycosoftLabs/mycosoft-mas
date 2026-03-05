#!/usr/bin/env python3
"""
Launcher for mycosoft-ssh MCP server. Sets cwd and PYTHONPATH so it works
when invoked from any directory (Claude Code, Cursor, etc).
MAR03 2026
"""
import os
import sys
from pathlib import Path

MAS_ROOT = Path(__file__).resolve().parents[1]
MCP_DIR = Path(__file__).resolve().parent
os.chdir(MAS_ROOT)
if str(MAS_ROOT) not in sys.path:
    sys.path.insert(0, str(MAS_ROOT))
if str(MCP_DIR) not in sys.path:
    sys.path.insert(0, str(MCP_DIR))

from mycosoft_ssh.server import mcp

if __name__ == "__main__":
    mcp.run()
