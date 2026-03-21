"""
MYCA CDP Browser Control — Goal-driven browser automation.

Replaces fixed Playwright actions with a goal-driven loop:
MYCA sees the screen, decides what to click/type, acts, observes result, repeats.

Uses Playwright with CDP for Chrome control. On VM 191, launches on :0 display.

Date: 2026-03-05
"""

import base64
import json
import logging
import os

logger = logging.getLogger("myca.os.browser_cdp")

MAX_BROWSER_STEPS = 15
DEFAULT_DISPLAY = os.getenv("DISPLAY", ":0")


class BrowserCDP:
    """Goal-driven CDP browser control for MYCA."""

    def __init__(self, os_ref):
        self._os = os_ref
        self._browser = None
        self._context = None
        self._page = None
        self._playwright = None

    async def initialize(self):
        """Lazy init — no browser launched until first use."""

    async def cleanup(self):
        """Close browser and Playwright."""
        try:
            if self._page:
                await self._page.close()
            if self._context:
                await self._context.close()
            if self._browser:
                await self._browser.close()
            if self._playwright:
                await self._playwright.stop()
        except Exception as e:
            logger.warning("Browser cleanup error: %s", e)
        finally:
            self._page = None
            self._context = None
            self._browser = None
            self._playwright = None

    async def launch_browser(self, url: str = "about:blank", visible: bool = True) -> dict:
        """Start Chrome on :0 display. Returns status."""
        try:
            from playwright.async_api import async_playwright
        except ImportError as e:
            return {"status": "failed", "error": f"Playwright not installed: {e}"}

        await self.cleanup()

        try:
            self._playwright = await async_playwright().start()
            env = os.environ.copy()
            if visible:
                env["DISPLAY"] = DEFAULT_DISPLAY
            self._browser = await self._playwright.chromium.launch(
                headless=not visible,
                args=["--no-sandbox", "--disable-dev-shm-usage"],
                env=env,
            )
            self._context = await self._browser.new_context(
                viewport={"width": 1280, "height": 800},
                ignore_https_errors=True,
            )
            self._page = await self._context.new_page()
            await self._page.goto(
                url or "about:blank", wait_until="domcontentloaded", timeout=15000
            )
            return {"status": "ok", "url": url or "about:blank"}
        except Exception as e:
            logger.error("Browser launch failed: %s", e)
            await self.cleanup()
            return {"status": "failed", "error": str(e)}

    async def get_page_state(self) -> dict:
        """Get screenshot (base64) + accessibility tree for LLM planning."""
        if not self._page:
            return {"error": "Browser not launched", "screenshot_b64": None, "a11y_tree": None}

        try:
            screenshot_bytes = await self._page.screenshot(type="png", full_page=False)
            screenshot_b64 = base64.standard_b64encode(screenshot_bytes).decode("ascii")
            a11y = await self._page.accessibility.snapshot()
            return {
                "screenshot_b64": screenshot_b64,
                "a11y_tree": json.dumps(a11y, indent=2) if a11y else "{}",
                "url": self._page.url,
            }
        except Exception as e:
            logger.warning("get_page_state failed: %s", e)
            return {"error": str(e), "screenshot_b64": None, "a11y_tree": None}

    async def execute_action(self, action: dict) -> dict:
        """Execute a single browser action (click, type, navigate, scroll, done)."""
        if not self._page:
            return {"status": "failed", "error": "Browser not launched"}

        kind = (action.get("action") or action.get("type") or "").lower()
        try:
            if kind == "done" or kind == "complete":
                return {"status": "done", "message": action.get("message", "Goal completed")}

            if kind == "navigate" or kind == "goto":
                url = action.get("url", "")
                await self._page.goto(url, wait_until="domcontentloaded", timeout=15000)
                return {"status": "ok", "action": "navigate", "url": url}

            if kind == "click":
                selector = action.get("selector") or action.get("element")
                if selector:
                    await self._page.click(selector, timeout=5000)
                else:
                    x = action.get("x")
                    y = action.get("y")
                    if x is not None and y is not None:
                        await self._page.mouse.click(x, y)
                    else:
                        return {"status": "failed", "error": "click requires selector or x,y"}
                return {"status": "ok", "action": "click"}

            if kind == "type" or kind == "fill":
                selector = action.get("selector") or action.get("element") or "input,textarea"
                text = action.get("text", "")
                await self._page.fill(selector, text, timeout=5000)
                return {"status": "ok", "action": "type"}

            if kind == "scroll":
                direction = (action.get("direction") or "down").lower()
                delta = action.get("delta", 300)
                if direction in ("up", "upward"):
                    delta = -abs(delta)
                await self._page.mouse.wheel(0, delta)
                return {"status": "ok", "action": "scroll"}

            return {"status": "failed", "error": f"Unknown action: {kind}"}
        except Exception as e:
            return {"status": "failed", "error": str(e)}

    async def run_browser_task(self, task: dict) -> dict:
        """
        Goal-driven browser loop: screenshot -> LLM decides action -> execute -> repeat.

        task: { "goal": str, "url": str (optional start URL), "visible": bool }
        """
        goal = task.get("goal", task.get("description", ""))
        start_url = task.get("url", "about:blank")
        visible = task.get("visible", True)

        launch_result = await self.launch_browser(url=start_url, visible=visible)
        if launch_result.get("status") != "ok":
            return {
                "status": "failed",
                "error": launch_result.get("error", "Browser launch failed"),
                "summary": f"Browser task: {goal[:80]}",
            }

        llm = getattr(getattr(self._os, "executive", None), "llm_brain", None)
        if not llm or not hasattr(llm, "plan_browser_action"):
            # Fallback: run a single read and return
            state = await self.get_page_state()
            return {
                "status": "completed",
                "summary": f"Browser opened; goal-driven loop unavailable (no plan_browser_action). Goal: {goal[:80]}",
                "url": state.get("url"),
            }

        history = []
        for step in range(MAX_BROWSER_STEPS):
            state = await self.get_page_state()
            if state.get("error") and not state.get("screenshot_b64"):
                return {"status": "failed", "error": state["error"], "step": step}

            next_action = await llm.plan_browser_action(
                screenshot_b64=state.get("screenshot_b64"),
                goal=goal,
                history=history,
                a11y_tree=state.get("a11y_tree"),
                url=state.get("url"),
            )

            if not next_action:
                break

            action_type = (next_action.get("action") or next_action.get("type") or "").lower()
            history.append({"step": step, "action": next_action})

            if action_type in ("done", "complete", "success"):
                await self.cleanup()
                return {
                    "status": "completed",
                    "summary": next_action.get("message", f"Goal completed: {goal[:80]}"),
                    "steps": len(history),
                }

            result = await self.execute_action(next_action)
            if result.get("status") == "failed":
                history[-1]["result"] = result
                # Continue one more step to let LLM try alternative
            if result.get("status") == "done":
                await self.cleanup()
                return {
                    "status": "completed",
                    "summary": result.get("message", goal[:80]),
                    "steps": len(history),
                }

        await self.cleanup()
        return {
            "status": "completed",
            "summary": f"Max steps ({MAX_BROWSER_STEPS}) reached. Goal: {goal[:80]}",
            "steps": len(history),
        }
