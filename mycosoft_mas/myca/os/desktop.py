"""
MYCA Desktop — Computer-use tools for VM 191.

Uses xdotool, scrot/gnome-screenshot, and DISPLAY=:0 for visible desktop control.
Enables MYCA to click, type, take screenshots, and launch apps on the XFCE desktop.

Date: 2026-03-05
"""

import asyncio
import logging
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger("myca.os.desktop")

DISPLAY = os.getenv("DISPLAY", ":0")
XDOTOOL = os.getenv("XDOTOOL_PATH", "xdotool")
SCROT = os.getenv("SCROT_PATH", "scrot")
SCREENSHOT_DIR = Path(os.getenv("MYCA_SCREENSHOT_DIR", "/tmp/myca_screenshots"))


def _env_with_display():
    env = os.environ.copy()
    env["DISPLAY"] = DISPLAY
    return env


async def system_run(command: str, timeout: float = 30) -> dict:
    """Run a shell command and return stdout/stderr."""
    try:
        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=_env_with_display(),
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        return {
            "returncode": proc.returncode,
            "stdout": stdout.decode("utf-8", errors="replace"),
            "stderr": stderr.decode("utf-8", errors="replace"),
        }
    except asyncio.TimeoutError:
        return {"returncode": -1, "stdout": "", "stderr": "Command timed out"}
    except Exception as e:
        return {"returncode": -1, "stdout": "", "stderr": str(e)}


async def desktop_screenshot(path: Optional[str] = None) -> dict:
    """Capture the current desktop screenshot. Returns path or error."""
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = path or str(SCREENSHOT_DIR / f"screenshot_{__import__('time').time():.0f}.png")

    # Try scrot first, then gnome-screenshot
    for cmd in [
        f"{SCROT} {out_path}",
        f"gnome-screenshot -f {out_path}",
    ]:
        r = await system_run(cmd, timeout=10)
        if r["returncode"] == 0 and Path(out_path).exists():
            return {"status": "ok", "path": out_path}
    return {
        "status": "failed",
        "error": "Screenshot capture failed (scrot/gnome-screenshot not available?)",
    }


async def desktop_click(x: int, y: int) -> dict:
    """Click at screen coordinates (x, y) using xdotool."""
    r = await system_run(f"{XDOTOOL} mousemove {x} {y} click 1", timeout=5)
    return {"status": "ok" if r["returncode"] == 0 else "failed", "stderr": r.get("stderr", "")}


async def desktop_type(text: str) -> dict:
    """Type text using xdotool (UTF-8 safe with type)."""
    # Escape for shell
    escaped = text.replace("'", "'\"'\"'")
    r = await system_run(f"{XDOTOOL} type '{escaped}'", timeout=10)
    return {"status": "ok" if r["returncode"] == 0 else "failed", "stderr": r.get("stderr", "")}


async def desktop_key(key_sequence: str) -> dict:
    """Send key sequence (e.g. 'Return', 'Tab', 'ctrl+c')."""
    escaped = key_sequence.replace("'", "'\"'\"'")
    r = await system_run(f"{XDOTOOL} key '{escaped}'", timeout=5)
    return {"status": "ok" if r["returncode"] == 0 else "failed", "stderr": r.get("stderr", "")}


async def app_launch(app_name: str) -> dict:
    """Launch a desktop application by name. Uses xdg-open or known app commands."""
    app_commands = {
        "chrome": "google-chrome",
        "chromium": "chromium-browser",
        "firefox": "firefox",
        "discord": "discord",
        "slack": "slack",
        "terminal": "xfce4-terminal",
        "cursor": "cursor",
        "code": "code",
        "vs code": "code",
        "asana": "xdg-open https://app.asana.com",
    }
    cmd = app_commands.get(app_name.lower(), app_name)
    r = await system_run(cmd, timeout=15)
    return {
        "status": "ok" if r["returncode"] == 0 else "failed",
        "stdout": r.get("stdout", ""),
        "stderr": r.get("stderr", ""),
    }


class DesktopTools:
    """Computer-use tools for MYCA. Integrate with ToolOrchestrator."""

    def __init__(self, os_ref=None):
        self._os = os_ref

    async def system_run(self, command: str, timeout: float = 30) -> dict:
        return await system_run(command, timeout)

    async def screenshot(self, path: Optional[str] = None) -> dict:
        return await desktop_screenshot(path)

    async def click(self, x: int, y: int) -> dict:
        return await desktop_click(x, y)

    async def type_text(self, text: str) -> dict:
        return await desktop_type(text)

    async def key(self, key_sequence: str) -> dict:
        return await desktop_key(key_sequence)

    async def launch_app(self, app_name: str) -> dict:
        return await app_launch(app_name)
