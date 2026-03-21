"""
Browser Tool -- headless browser automation in sandbox containers.

Routes through GatewayControlPlane -> SandboxManager -> Node daemon
for safe, isolated browser automation via Playwright.
"""

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Dict, Optional

if TYPE_CHECKING:
    from mycosoft_mas.gateway.control_plane import GatewayControlPlane

logger = logging.getLogger(__name__)


@dataclass
class BrowserResult:
    title: str = ""
    url: str = ""
    content_preview: str = ""
    screenshot: Optional[bytes] = None
    error: Optional[str] = None


class BrowserTool:
    """Headless browser automation in sandbox containers."""

    def __init__(self, gateway: Optional["GatewayControlPlane"] = None):
        self._gateway = gateway

    async def _browser_call(
        self,
        action: str,
        payload: Dict[str, Any],
        session_id: Optional[str] = None,
    ) -> BrowserResult:
        if not self._gateway:
            return BrowserResult(error="Gateway not available")

        result = await self._gateway.intercept_tool_call(
            "browser",
            {"action": action, **payload},
            session_id=session_id,
        )
        out = result.output or {}
        if isinstance(out, dict):
            screenshot_b64 = out.get("screenshot")
            screenshot_bytes = None
            if screenshot_b64:
                import base64

                screenshot_bytes = base64.b64decode(screenshot_b64)
            return BrowserResult(
                title=out.get("title", ""),
                url=out.get("url", ""),
                content_preview=out.get("content", ""),
                screenshot=screenshot_bytes,
                error=out.get("error") or result.error,
            )
        return BrowserResult(error=result.error or str(out))

    async def navigate(self, url: str, session_id: Optional[str] = None) -> BrowserResult:
        return await self._browser_call("navigate", {"url": url}, session_id)

    async def click(self, selector: str, session_id: Optional[str] = None) -> BrowserResult:
        return await self._browser_call("click", {"selector": selector}, session_id)

    async def type(
        self, selector: str, text: str, session_id: Optional[str] = None
    ) -> BrowserResult:
        return await self._browser_call("type", {"selector": selector, "text": text}, session_id)

    async def screenshot(self, session_id: Optional[str] = None) -> bytes:
        result = await self._browser_call("screenshot", {}, session_id)
        return result.screenshot or b""

    async def get_content(
        self, selector: Optional[str] = None, session_id: Optional[str] = None
    ) -> str:
        result = await self._browser_call(
            "get_content",
            {"selector": selector} if selector else {},
            session_id,
        )
        return result.content_preview
