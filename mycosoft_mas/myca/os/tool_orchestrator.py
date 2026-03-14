"""
MYCA Tool Orchestrator — All tools MYCA can use autonomously.

MYCA has access to developer-grade tools on her VM 191:
- Claude Code CLI — autonomous coding, PR creation, code review
- Cursor — IDE operations (via CLI or MCP)
- browser-use / Playwright — web automation, research, form filling
- n8n — workflow triggers (MYCA's personal n8n on 191:5679)
- Git / GitHub CLI — repo operations, PRs, issues
- Docker — container management on VM 191
- SSH — cross-VM operations to MAS (188), MINDEX (189), Sandbox (187)

Date: 2026-03-04
"""

import os
import asyncio
import json
import logging
import re
import subprocess
from typing import Any, Dict, Optional, Tuple
from pathlib import Path

import aiohttp

logger = logging.getLogger("myca.os.tools")


class ToolOrchestrator:
    """Orchestrates all tools MYCA can use."""

    def __init__(self, os_ref):
        self._os = os_ref
        self._session: Optional[aiohttp.ClientSession] = None

        # Tool paths
        self._claude_code = os.getenv("CLAUDE_CODE_PATH", "claude")
        self._git = "git"
        self._gh = "gh"
        self._docker = "docker"

        # Service URLs
        self._n8n_url = os.getenv("MYCA_N8N_URL", "http://localhost:5679")
        self._n8n_api_key = os.getenv("MYCA_N8N_API_KEY", "")
        self._workspace_url = os.getenv("MYCA_WORKSPACE_URL", "http://localhost:8100")

        # Working directories
        self._repos_dir = Path(os.getenv("MYCA_REPOS_DIR", "/home/mycosoft/repos"))
        self._mas_repo = self._repos_dir / "mycosoft-mas"

    async def initialize(self):
        self._session = aiohttp.ClientSession()
        logger.info("ToolOrchestrator initialized")

        # Check which tools are available
        available = await self._check_tool_availability()
        logger.info(f"Available tools: {', '.join(available)}")

    async def cleanup(self):
        if self._session and not self._session.closed:
            await self._session.close()

    # ── Claude Code / OpenWork ───────────────────────────────────

    async def run_openwork_task(self, task: dict) -> dict:
        """Run coding task via OpenWork (OpenCode) if available, else Claude Code."""
        bridge = self._os.openwork_bridge
        health = await bridge.health_check()
        if health.get("healthy"):
            prompt = task.get("prompt", task.get("description", ""))
            return await bridge.run_task(prompt, title=task.get("title"))
        return await self.run_claude_code(task)

    async def run_claude_code(self, task: dict) -> dict:
        """Run a coding task using Claude Code CLI."""
        prompt = task.get("prompt", task.get("description", ""))
        repo = task.get("repo", str(self._mas_repo))
        allow_edit = task.get("allow_edit", True)

        cmd = [self._claude_code, "--print"]
        if allow_edit:
            cmd.append("--dangerously-skip-permissions")
        cmd.extend(["--message", prompt])

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=repo,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env={**os.environ, "CLAUDE_CODE_DISABLE_NONINTERACTIVE_HINT": "1"},
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=300)

            output = stdout.decode("utf-8", errors="replace")
            return {
                "status": "completed" if proc.returncode == 0 else "failed",
                "output": output[:5000],
                "returncode": proc.returncode,
                "summary": f"Claude Code task: {prompt[:100]}",
            }
        except asyncio.TimeoutError:
            return {"status": "timeout", "summary": "Claude Code task timed out (5min)"}
        except Exception as e:
            return {"status": "failed", "error": str(e)}

    # ── Browser Automation ───────────────────────────────────────

    async def run_browser_task(self, task: dict) -> dict:
        """Run goal-driven browser task using CDP control loop."""
        return await self._os.browser_cdp.run_browser_task(task)

    async def run_browser_research(self, task: dict) -> dict:
        """Run browser-based research using Playwright."""
        url = task.get("url", "")
        action = task.get("action", "read")  # read, search, fill_form, screenshot, login, click
        query = task.get("query", "")
        headless = task.get("headless", True)

        try:
            if action == "search":
                return await self._browser_search(query)
            elif action == "read":
                return await self._browser_read(url)
            elif action == "fill_form":
                fields = task.get("fields", {})
                submit_selector = task.get("submit_selector")
                return await self._browser_fill_form(url, fields, submit_selector, headless)
            elif action == "screenshot":
                path = task.get("path", "/tmp/myca_screenshot.png")
                return await self._browser_screenshot(url, path, headless)
            elif action == "login":
                site = task.get("site", "")
                return await self._browser_login(site, headless)
            elif action == "click":
                selector = task.get("selector", "")
                return await self._browser_click(url, selector, headless)
            else:
                return {"status": "completed", "summary": f"Browser {action}: {url}"}
        except Exception as e:
            return {"status": "failed", "error": str(e)}

    async def _browser_search(self, query: str) -> dict:
        """Search the web using browser automation."""
        # Use Playwright headless
        cmd = [
            "python3", "-c",
            f"""
import asyncio
from playwright.async_api import async_playwright

async def search():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(f'https://www.google.com/search?q={query}')
        results = await page.query_selector_all('.g')
        texts = []
        for r in results[:5]:
            text = await r.inner_text()
            texts.append(text[:200])
        await browser.close()
        return texts

results = asyncio.run(search())
for r in results:
    print(r)
    print('---')
"""
        ]
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=60)
        return {
            "status": "completed",
            "results": stdout.decode()[:3000],
            "summary": f"Searched: {query}",
        }

    async def _browser_read(self, url: str) -> dict:
        """Read a webpage using Playwright."""
        cmd = [
            "python3", "-c",
            f"""
import asyncio
from playwright.async_api import async_playwright

async def read():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto('{url}', wait_until='domcontentloaded')
        text = await page.inner_text('body')
        await browser.close()
        return text[:5000]

print(asyncio.run(read()))
"""
        ]
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=60)
        return {
            "status": "completed",
            "content": stdout.decode()[:5000],
            "summary": f"Read: {url}",
        }

    async def _browser_fill_form(
        self,
        url: str,
        fields: dict,
        submit_selector: Optional[str],
        headless: bool = True,
    ) -> dict:
        """Fill form fields and optionally submit."""
        import base64
        import json
        fields_b64 = base64.b64encode(json.dumps(fields).encode()).decode()
        submit_b64 = base64.b64encode((submit_selector or "").encode()).decode()
        headless_str = "True" if headless else "False"
        script = f'''
import asyncio
import base64
import json
from playwright.async_api import async_playwright

async def fill():
    fields = json.loads(base64.b64decode("{fields_b64}").decode())
    submit_sel = base64.b64decode("{submit_b64}").decode() if "{submit_b64}" else None
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless={headless_str})
        page = await browser.new_page()
        await page.goto("{url}", wait_until="domcontentloaded")
        for selector, value in fields.items():
            el = await page.query_selector(selector)
            if el:
                await el.fill(str(value))
        if submit_sel:
            btn = await page.query_selector(submit_sel)
            if btn:
                await btn.click()
                await page.wait_for_load_state("networkidle", timeout=10000)
        content = await page.inner_text("body")
        await browser.close()
        return content[:5000]

print(asyncio.run(fill()))
'''
        proc = await asyncio.create_subprocess_exec(
            "python3", "-c", script,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=90)
        err = stderr.decode() if stderr else ""
        if proc.returncode != 0:
            return {"status": "failed", "error": err[:500], "summary": f"Fill form: {url}"}
        return {
            "status": "completed",
            "content": stdout.decode()[:5000],
            "summary": f"Filled form: {url}",
        }

    async def _browser_screenshot(
        self,
        url: str,
        path: str,
        headless: bool = True,
    ) -> dict:
        """Take a screenshot of a webpage."""
        headless_str = "True" if headless else "False"
        script = f'''
import asyncio
from playwright.async_api import async_playwright

async def shot():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless={headless_str})
        page = await browser.new_page()
        await page.goto("{url}", wait_until="domcontentloaded")
        await page.screenshot(path="{path}")
        await browser.close()
    return "{path}"

print(asyncio.run(shot()))
'''
        proc = await asyncio.create_subprocess_exec(
            "python3", "-c", script,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=60)
        if proc.returncode != 0:
            return {"status": "failed", "error": stderr.decode()[:500], "summary": f"Screenshot: {url}"}
        return {
            "status": "completed",
            "path": path,
            "summary": f"Screenshot saved: {path}",
        }

    async def _browser_login(self, site: str, headless: bool = True) -> dict:
        """Log into Gmail or Asana using env credentials."""
        user_env = ""
        pass_env = ""
        url = ""
        user_sel = ""
        pass_sel = ""
        submit_sel = ""
        if site == "gmail":
            user_env = "SMTP_USER"
            pass_env = "SMTP_PASSWORD"
            url = "https://accounts.google.com/"
            user_sel = "input[type=email]"
            pass_sel = "input[type=password]"
            submit_sel = "button[type=submit], input[type=submit]"
        elif site == "asana":
            user_env = "ASANA_EMAIL"
            pass_env = "ASANA_PASSWORD"
            url = "https://app.asana.com/-/login"
            user_sel = "input[type=email], input[name=email]"
            pass_sel = "input[type=password], input[name=password]"
            submit_sel = "button[type=submit], input[type=submit]"
        else:
            return {"status": "failed", "error": f"Unknown site: {site}"}

        user = os.getenv(user_env, "")
        pwd = os.getenv(pass_env, "")
        if not user or not pwd:
            return {"status": "failed", "error": f"Missing {user_env} or {pass_env}"}

        headless_str = "True" if headless else "False"
        script = f'''
import asyncio
import os
from playwright.async_api import async_playwright

user = os.environ.get("_MYCA_LOGIN_USER", "")
pwd = os.environ.get("_MYCA_LOGIN_PWD", "")

async def login():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless={headless_str})
        page = await browser.new_page()
        await page.goto("{url}", wait_until="domcontentloaded")
        u = await page.query_selector("{user_sel}")
        if u:
            await u.fill(user)
            sub = await page.query_selector("{submit_sel}")
            if sub:
                await sub.click()
                await page.wait_for_timeout(2000)
        p_el = await page.query_selector("{pass_sel}")
        if p_el:
            await p_el.fill(pwd)
            sub2 = await page.query_selector("{submit_sel}")
            if sub2:
                await sub2.click()
                await page.wait_for_load_state("networkidle", timeout=15000)
        final_url = page.url
        await browser.close()
        return final_url

print(asyncio.run(login()))
'''
        proc_env = {**os.environ, "_MYCA_LOGIN_USER": user, "_MYCA_LOGIN_PWD": pwd}
        proc = await asyncio.create_subprocess_exec(
            "python3", "-c", script,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=proc_env,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=60)
        if proc.returncode != 0:
            return {"status": "failed", "error": stderr.decode()[:500], "summary": f"Login {site}"}
        return {
            "status": "completed",
            "final_url": stdout.decode().strip(),
            "summary": f"Logged into {site}",
        }

    async def _browser_click(
        self,
        url: str,
        selector: str,
        headless: bool = True,
    ) -> dict:
        """Navigate to URL and click an element."""
        import base64
        sel_b64 = base64.b64encode(selector.encode()).decode()
        headless_str = "True" if headless else "False"
        script = f'''
import asyncio
import base64
from playwright.async_api import async_playwright

sel = base64.b64decode("{sel_b64}").decode()

async def click():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless={headless_str})
        page = await browser.new_page()
        await page.goto("{url}", wait_until="domcontentloaded")
        el = await page.query_selector(sel)
        if el:
            await el.click()
            await page.wait_for_load_state("networkidle", timeout=10000)
        content = await page.inner_text("body")
        await browser.close()
        return content[:3000]

print(asyncio.run(click()))
'''
        proc = await asyncio.create_subprocess_exec(
            "python3", "-c", script,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=60)
        if proc.returncode != 0:
            return {"status": "failed", "error": stderr.decode()[:500], "summary": f"Click: {url}"}
        return {
            "status": "completed",
            "content": stdout.decode()[:3000],
            "summary": f"Clicked {selector} on {url}",
        }

    def launch_visible_browser(self) -> None:
        """Launch Chrome on XFCE DISPLAY for noVNC viewing (http://192.168.0.191:6080)."""
        env = {**os.environ, "DISPLAY": ":0"}
        subprocess.Popen(
            ["chromium-browser", "--no-sandbox", "--disable-dev-shm-usage"],
            env=env,
            start_new_session=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        logger.info("Launched visible Chrome on DISPLAY=:0 for noVNC")

    # ── n8n Workflows ────────────────────────────────────────────

    async def trigger_n8n_workflow(self, task: dict) -> dict:
        """Execute an n8n workflow via webhook trigger (or activate if no webhook).

        Delegates to n8n_bridge when available. Task params:
          - workflow: Workflow name
          - webhook_path: Optional. If set, used directly (skips lookup)
          - data: Payload to POST to webhook (default {})
        """
        workflow_name = task.get("workflow", "")
        webhook_path = task.get("webhook_path", "") or None
        data = task.get("data", {})

        if not workflow_name and not webhook_path:
            return {"status": "failed", "error": "Missing workflow name or webhook_path"}

        bridge = self._os.n8n_bridge
        return await bridge.trigger_workflow(
            workflow_name or "webhook",
            data=data if isinstance(data, dict) else {},
            webhook_path=webhook_path,
        )

    async def run_github_task(self, task: dict) -> dict:
        """Run a GitHub-native task via the REST client."""
        from mycosoft_mas.integrations.github_client import GitHubClient

        owner = task.get("owner") or os.getenv("GITHUB_OWNER", "")
        repo = task.get("repo_name") or task.get("repo") or ""
        operation = task.get("operation", "health")
        client = GitHubClient()

        try:
            if operation == "health":
                return {"status": "completed", "result": await client.health_check(), "summary": "GitHub health checked"}
            if operation == "list_issues" and owner and repo:
                issues = await client.list_issues(owner, repo, limit=20)
                return {"status": "completed", "issues": issues, "summary": f"Listed issues for {owner}/{repo}"}
            if operation == "list_pull_requests" and owner and repo:
                prs = await client.list_pull_requests(owner, repo, limit=20)
                return {"status": "completed", "pull_requests": prs, "summary": f"Listed pull requests for {owner}/{repo}"}
            if operation == "create_issue" and owner and repo:
                issue = await client.create_issue(owner, repo, task.get("title", "MYCA task"), task.get("body", task.get("description", "")))
                return {"status": "completed" if issue else "failed", "issue": issue, "summary": f"Created issue in {owner}/{repo}"}
            if operation == "comment_issue" and owner and repo and task.get("issue_number"):
                comment = await client.add_issue_comment(owner, repo, int(task["issue_number"]), task.get("body", task.get("description", "")))
                return {"status": "completed" if comment else "failed", "comment": comment, "summary": f"Commented on {owner}/{repo}#{task['issue_number']}"}
            return {"status": "failed", "error": "Unsupported GitHub task or missing owner/repo"}
        finally:
            await client.close()

    async def run_asana_task(self, task: dict) -> dict:
        """Run an Asana-native task via the REST client."""
        from mycosoft_mas.integrations.asana_client import AsanaClient

        client = AsanaClient({"api_key": os.getenv("ASANA_API_KEY", "") or os.getenv("ASANA_PAT", "")})
        operation = task.get("operation", "workspaces")

        try:
            if operation == "workspaces":
                workspaces = await client.get_workspaces()
                return {"status": "completed", "workspaces": workspaces, "summary": "Listed Asana workspaces"}
            if operation == "create_task":
                created = await client.create_task(
                    name=task.get("title", "MYCA task"),
                    workspace_gid=task.get("workspace_gid"),
                    project_gid=task.get("project_gid"),
                    notes=task.get("notes", task.get("description", "")),
                )
                return {"status": "completed" if created else "failed", "task": created, "summary": "Created Asana task"}
            if operation == "comment_task" and task.get("task_gid"):
                comment = await client.add_comment(task.get("task_gid", ""), task.get("body", task.get("description", "")))
                return {"status": "completed" if comment else "failed", "comment": comment, "summary": f"Commented on Asana task {task.get('task_gid')}"}
            if operation == "list_tasks":
                tasks = await client.list_tasks(project_gid=task.get("project_gid"), workspace_gid=task.get("workspace_gid"), limit=20)
                return {"status": "completed", "tasks": tasks, "summary": "Listed Asana tasks"}
            return {"status": "failed", "error": "Unsupported Asana task"}
        finally:
            await client.close()

    async def run_natureos_task(self, task: dict) -> dict:
        """Run a NatureOS-native task."""
        from mycosoft_mas.integrations.natureos_client import NATUREOSClient

        client = NATUREOSClient()
        operation = task.get("operation", "health")
        if operation == "health":
            return {"status": "completed", "result": await client.get_matlab_health(), "summary": "NatureOS health checked"}
        if operation == "anomaly_detection":
            result = await client.run_anomaly_detection(task.get("device_id", "mushroom1"))
            return {"status": "completed", "result": result, "summary": "NatureOS anomaly detection executed"}
        if operation == "forecast":
            result = await client.forecast_environmental(task.get("metric", "temperature"), int(task.get("hours", 24)))
            return {"status": "completed", "result": result, "summary": "NatureOS forecast executed"}
        if operation == "device_sync":
            result = await client.sync_digital_twin(task.get("device_id", "mushroom1"))
            return {"status": "completed", "result": result, "summary": "NatureOS digital twin sync executed"}
        return {"status": "failed", "error": "Unsupported NatureOS task"}

    async def run_search_task(self, task: dict) -> dict:
        """Run a unified search task against MINDEX-backed knowledge surfaces."""
        query = task.get("query") or task.get("description") or task.get("title") or ""
        if not query:
            return {"status": "failed", "error": "Search query required"}
        results = await self._os.mindex_bridge.search_knowledge(query, limit=int(task.get("limit", 10)))
        return {"status": "completed", "results": results, "summary": f"Unified search completed for: {query[:80]}"}

    # ── CREP Map Control ───────────────────────────────────────────

    def _infer_crep_tool_from_description(self, text: str) -> Optional[Tuple[str, Dict[str, Any], bool]]:
        """
        Infer CREP tool and args from natural language (title/description).
        Returns (tool, args, needs_confirmation) or None if unparseable.
        """
        if not text or not isinstance(text, str):
            return None
        t = text.strip().lower()

        # fly to / go to / zoom to / center on <place>
        m = re.search(
            r"(?:fly to|go to|zoom to|center on|navigate to)\s+(.+)",
            t,
            re.IGNORECASE,
        )
        if m:
            query = m.group(1).strip()
            if len(query) >= 2:
                return ("crep_geocode_and_fly_to", {"query": query, "zoom": 10}, False)

        # show <layer> / show <layer> layer
        m = re.search(
            r"show\s+(planes|vessels|satellites|fungal|weather|devices)(?:\s+layer)?",
            t,
        )
        if m:
            return ("crep_set_layer_visibility", {"layer": m.group(1), "visible": True}, False)

        # hide <layer>
        m = re.search(
            r"hide\s+(planes|vessels|satellites|fungal|weather|devices)(?:\s+layer)?",
            t,
        )
        if m:
            return ("crep_set_layer_visibility", {"layer": m.group(1), "visible": False}, False)

        # toggle <layer>
        m = re.search(
            r"toggle\s+(planes|vessels|satellites|fungal|weather|devices)(?:\s+layer)?",
            t,
        )
        if m:
            return ("crep_toggle_layer", {"layer": m.group(1)}, False)

        # clear filters
        if re.search(r"clear\s+(?:all\s+)?filters?", t):
            return ("crep_clear_filters", {}, True)

        # zoom in / zoom out
        if re.search(r"zoom\s+in", t):
            return ("crep_zoom_by", {"delta": 1}, False)
        if re.search(r"zoom\s+out", t):
            return ("crep_zoom_by", {"delta": -1}, False)

        # get view / view context / what do I see
        if re.search(r"(?:get\s+view|view\s+context|what\s+(?:do\s+i\s+)?see)", t):
            return ("crep_get_view_context", {}, False)

        # timeline search <query>
        m = re.search(r"timeline\s+search\s+(.+)", t, re.IGNORECASE)
        if m:
            return ("crep_timeline_search", {"query": m.group(1).strip()}, False)

        return None

    async def run_crep_map_task(self, task: dict) -> dict:
        """
        Execute a CREP map action via the CREP bridge.

        Task payload:
          - tool: CREP tool name (crep_fly_to, crep_set_layer_visibility, etc.)
          - args: dict of tool arguments
          - confirmed: bool (required for crep_clear_filters and similar)

        When tool/args are missing, infers from title/description via intent parsing.
        """
        crep = getattr(self._os, "crep_bridge", None)
        if not crep or not hasattr(crep, "execute_crep_action"):
            return {"status": "failed", "error": "CREP bridge not available"}

        tool = task.get("tool") or task.get("tool_name")
        args = task.get("args") or task.get("payload") or {}
        confirmed = task.get("confirmed", False)

        if not tool:
            desc = (task.get("description") or task.get("title") or "").strip()
            inferred = self._infer_crep_tool_from_description(desc)
            if inferred:
                tool, args, needs_confirm = inferred
                if needs_confirm and not confirmed:
                    return {
                        "status": "requires_confirmation",
                        "error": "Command requires user confirmation (e.g. clear filters)",
                        "summary": "CREP command needs confirmation",
                    }
            else:
                return {
                    "status": "failed",
                    "error": "CREP task requires 'tool' or a parseable description (e.g. 'fly to Paris', 'show planes layer')",
                }

        result = await crep.execute_crep_action(tool, args, confirmed=confirmed)

        if result.get("success"):
            return {
                "status": "completed",
                "frontend_command": result.get("frontend_command"),
                "speak": result.get("speak"),
                "summary": result.get("speak") or f"CREP {tool} executed",
            }
        if result.get("requires_confirmation"):
            return {
                "status": "requires_confirmation",
                "error": result.get("error", "Command requires user confirmation"),
                "summary": "CREP command needs confirmation (e.g. clear filters)",
            }
        return {
            "status": "failed",
            "error": result.get("error", "CREP command failed"),
        }

    # ── Finance / CFO Connector ────────────────────────────────────

    async def run_finance_task(self, task: dict) -> dict:
        """Run a finance task via the finance discovery/delegation layer.

        Routes through the canonical CFO-facing contract instead of generic fallback
        or direct Morgan escalation. Operations:
          - delegate: delegate to a finance agent (agent_id, task payload)
          - list_agents, list_services, list_workloads, list_tasks: discovery
          - status, alerts: aggregate status and alerts
          - submit_report: submit finance report to C-Suite
        """
        from mycosoft_mas.finance.discovery import (
            delegate_finance_task,
            list_finance_agents,
            list_finance_services,
            list_finance_workloads,
            list_finance_tasks,
            get_finance_status,
            get_finance_alerts,
            submit_finance_report,
        )

        operation = task.get("operation", "status")

        try:
            if operation == "delegate":
                agent_id = task.get("agent_id") or task.get("agent")
                if not agent_id:
                    return {"status": "failed", "error": "agent_id required for delegate"}
                payload = {k: v for k, v in task.items() if k not in ("operation", "agent_id", "agent", "type")}
                result = await delegate_finance_task(agent_id, payload)
                if result.get("status") == "ok":
                    return {
                        "status": "completed",
                        "result": result.get("result"),
                        "agent_id": agent_id,
                        "summary": f"Delegated to {agent_id}",
                    }
                return {
                    "status": "failed",
                    "error": result.get("error", "delegation failed"),
                    "agent_id": agent_id,
                }
            elif operation == "list_agents":
                agents = list_finance_agents()
                return {"status": "completed", "agents": agents, "summary": f"Listed {len(agents)} finance agents"}
            elif operation == "list_services":
                services = list_finance_services()
                return {"status": "completed", "services": services, "summary": f"Listed {len(services)} finance services"}
            elif operation == "list_workloads":
                workloads = await list_finance_workloads()
                return {"status": "completed", "workloads": workloads, "summary": f"Listed {len(workloads)} finance workloads"}
            elif operation == "list_tasks":
                tasks = await list_finance_tasks()
                return {"status": "completed", "tasks": tasks, "summary": f"Listed {len(tasks)} finance tasks"}
            elif operation == "status":
                status = await get_finance_status()
                return {"status": "completed", "status": status, "summary": "Finance status retrieved"}
            elif operation == "alerts":
                alerts = await get_finance_alerts()
                return {"status": "completed", "alerts": alerts, "summary": f"Retrieved {len(alerts)} finance alerts"}
            elif operation == "submit_report":
                result = await submit_finance_report(
                    role=task.get("role", "CFO"),
                    assistant_name=task.get("assistant_name", "Meridian"),
                    report_type=task.get("report_type", "operating_report"),
                    summary=task.get("summary", ""),
                    details=task.get("details"),
                    task_id=task.get("task_id"),
                    escalated=task.get("escalated", False),
                )
                if "error" in result:
                    return {"status": "failed", "error": result.get("error"), "summary": "Report submit failed"}
                return {"status": "completed", "result": result, "summary": "Finance report submitted"}
            else:
                return {"status": "failed", "error": f"Unknown finance operation: {operation}"}
        except Exception as e:
            logger.exception("run_finance_task failed: %s", e)
            return {"status": "failed", "error": str(e)}

    # ── Git / GitHub ─────────────────────────────────────────────

    async def run_git_operation(self, task: dict) -> dict:
        """Run a Git or GitHub CLI operation."""
        operation = task.get("operation", "status")
        repo = task.get("repo", str(self._mas_repo))

        commands = {
            "status": [self._git, "status", "--short"],
            "pull": [self._git, "pull", "origin", "main"],
            "log": [self._git, "log", "--oneline", "-10"],
            "branch": [self._git, "branch", "-a"],
            "pr_list": [self._gh, "pr", "list"],
            "issue_list": [self._gh, "issue", "list"],
        }

        cmd = commands.get(operation)
        if not cmd:
            # Custom command
            cmd = task.get("command", "").split()
            if not cmd:
                return {"status": "failed", "error": f"Unknown git operation: {operation}"}

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=repo,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()

        return {
            "status": "completed" if proc.returncode == 0 else "failed",
            "output": stdout.decode()[:3000],
            "error": stderr.decode()[:1000] if proc.returncode != 0 else None,
            "summary": f"Git {operation}",
        }

    # ── Deployment ───────────────────────────────────────────────

    async def run_deployment(self, task: dict) -> dict:
        """Run a deployment operation."""
        target = task.get("target", "")  # mas, mindex, website, myca
        action = task.get("action", "restart")  # restart, rebuild, update

        # Infer target from description if not set (e.g. Morgan: "deploy website to sandbox")
        if not target and task.get("type") == "deployment":
            desc = (task.get("description") or "") + " " + (task.get("title") or "")
            desc = desc.lower()
            if "website" in desc or "sandbox" in desc:
                target = "website"
            elif "mas" in desc or "orchestrator" in desc:
                target = "mas"
            elif "mindex" in desc:
                target = "mindex"

        if target == "myca":
            # Local deployment on VM 191
            cmd = [self._docker, "compose", "-f",
                   "/opt/myca/docker-compose.myca-workspace.yml",
                   "up", "-d", "--build"]
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()
            return {
                "status": "completed" if proc.returncode == 0 else "failed",
                "output": stdout.decode()[:2000],
                "summary": f"Deployed {target}: {action}",
            }
        elif target == "website":
            # Deploy website to Sandbox VM 187 (SSH, build, restart, Cloudflare purge)
            return await self._deploy_website_sandbox(task)
        elif target in ("mas", "mindex"):
            return {
                "status": "needs_approval",
                "summary": f"Deployment to {target} requires Morgan's approval",
                "target": target,
                "action": action,
            }
        elif not target:
            return {"status": "failed", "error": "Could not infer deployment target from task"}
        else:
            return {"status": "failed", "error": f"Unknown deployment target: {target}"}

    async def _deploy_website_sandbox(self, task: dict) -> dict:
        """Deploy website to Sandbox VM 187: pull, build, restart, purge Cloudflare."""
        import paramiko

        vm = os.getenv("SANDBOX_VM_IP", "192.168.0.187")
        user = os.getenv("VM_USER", "mycosoft")
        password = os.environ.get("VM_PASSWORD") or os.environ.get("VM_SSH_PASSWORD")

        if not password:
            return {
                "status": "failed",
                "error": "VM_PASSWORD or VM_SSH_PASSWORD not set — cannot SSH to Sandbox",
            }

        def _ssh_deploy():
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(vm, username=user, password=password, timeout=30)
            try:
                def run(cmd, timeout=600):
                    _, stdout, stderr = client.exec_command(cmd, timeout=timeout)
                    out = stdout.read().decode("utf-8", errors="replace")
                    err = stderr.read().decode("utf-8", errors="replace")
                    return stdout.channel.recv_exit_status(), out, err

                # 1. Pull
                ec, out, err = run("cd /opt/mycosoft/website && git fetch && git reset --hard origin/main && git log -1 --oneline")
                if ec != 0:
                    return False, f"Git pull failed: {err[:500]}"

                # 2. Build
                ec, out, err = run("cd /opt/mycosoft/website && docker build --no-cache -t mycosoft-always-on-mycosoft-website:latest . 2>&1", timeout=600)
                if ec != 0:
                    return False, f"Docker build failed: {err[:500]}"

                # 3. Stop/remove old container
                run("docker stop mycosoft-website 2>/dev/null; docker rm mycosoft-website 2>/dev/null; echo done")

                # 4. Start with NAS mount
                ec, out, err = run(
                    "docker run -d --name mycosoft-website -p 3000:3000 "
                    "-v /opt/mycosoft/media/website/assets:/app/public/assets:ro "
                    "--restart unless-stopped mycosoft-always-on-mycosoft-website:latest"
                )
                if ec != 0:
                    return False, f"Container start failed: {err[:500]}"

                return True, "Deployed"
            finally:
                client.close()

        try:
            success, msg = await asyncio.to_thread(_ssh_deploy)
        except Exception as e:
            return {"status": "failed", "error": str(e), "summary": "Website deployment failed"}

        if not success:
            return {"status": "failed", "error": msg, "summary": "Website deployment failed"}

        # 5. Purge Cloudflare
        purge_ok = await self._purge_cloudflare()

        summary = "Website deployed to sandbox.mycosoft.com. Container restarted with NAS mount."
        if purge_ok:
            summary += " Cloudflare cache purged."
        else:
            summary += " (Cloudflare purge skipped — set CLOUDFLARE_API_TOKEN and CLOUDFLARE_ZONE_ID to enable.)"

        return {
            "status": "completed",
            "output": msg,
            "summary": summary,
            "target": "website",
            "cloudflare_purged": purge_ok,
        }

    async def _purge_cloudflare(self) -> bool:
        """Purge Cloudflare cache (purge_everything). Returns True on success."""
        token = os.getenv("CLOUDFLARE_API_TOKEN")
        zone_id = os.getenv("CLOUDFLARE_ZONE_ID")
        if not token or not zone_id:
            logger.debug("Cloudflare purge skipped: CLOUDFLARE_API_TOKEN/CLOUDFLARE_ZONE_ID not set")
            return False
        try:
            import requests
            url = f"https://api.cloudflare.com/client/v4/zones/{zone_id}/purge_cache"
            resp = requests.post(
                url,
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                json={"purge_everything": True},
                timeout=20,
            )
            data = resp.json()
            return resp.ok and data.get("success") is True
        except Exception as e:
            logger.warning("Cloudflare purge failed: %s", e)
            return False

    # ── Desktop / Computer Use ───────────────────────────────────

    async def run_desktop_task(self, task: dict) -> dict:
        """Run desktop/computer-use tasks via desktop tools."""
        from mycosoft_mas.myca.os.desktop import (
            desktop_screenshot,
            desktop_click,
            desktop_type,
            desktop_key,
            app_launch,
            system_run,
        )
        action = task.get("action", "screenshot")
        if action == "screenshot":
            return await desktop_screenshot(task.get("path"))
        elif action == "click":
            x, y = task.get("x", 0), task.get("y", 0)
            return await desktop_click(x, y)
        elif action == "type":
            return await desktop_type(task.get("text", ""))
        elif action == "key":
            return await desktop_key(task.get("key_sequence", ""))
        elif action == "launch":
            return await app_launch(task.get("app_name", ""))
        elif action == "run":
            return await system_run(task.get("command", ""), task.get("timeout", 30))
        return {"status": "failed", "error": f"Unknown desktop action: {action}"}

    async def run_skill_task(self, task: dict) -> dict:
        """Run a skill by ID."""
        from mycosoft_mas.myca.os.skills_manager import run_skill
        skill_id = task.get("skill_id", task.get("skill", ""))
        args = task.get("args", {})
        return await run_skill(skill_id, args, self._os)

    # ── General Task ─────────────────────────────────────────────

    async def run_general_task(self, task: dict) -> dict:
        """Use Claude Code to figure out and execute a general task."""
        description = task.get("description", "")
        return await self.run_claude_code({
            "prompt": f"Execute this task autonomously: {description}",
            "allow_edit": True,
        })

    # ── Local Service Health ─────────────────────────────────────

    async def check_local_services(self) -> dict:
        """Check health of local services on VM 191.

        Returns dict of service_name -> bool. Health warnings are informational
        and must never cause the daemon to shut down.
        """
        services = {
            "workspace_api": [
                f"{self._workspace_url}/health",
                f"{self._workspace_url}/",
            ],
            "n8n": [
                f"{self._n8n_url}/healthz",
                f"{self._n8n_url}/",
            ],
        }

        results = {}
        for name, urls in services.items():
            ok = False
            for url in urls:
                try:
                    async with self._session.get(url, timeout=aiohttp.ClientTimeout(total=3)) as resp:
                        if resp.status < 500:
                            ok = True
                            break
                except Exception:
                    continue
            results[name] = ok

        # Check Docker via socket (faster than subprocess)
        try:
            proc = await asyncio.create_subprocess_exec(
                self._docker, "ps", "--format", "{{.Names}}",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=5)
            results["docker"] = proc.returncode == 0
            results["containers"] = stdout.decode().strip().split("\n") if stdout else []
        except Exception:
            results["docker"] = False

        return results

    # ── Tool Availability ────────────────────────────────────────

    async def _check_tool_availability(self) -> list:
        """Check which tools are available on this system."""
        available = []
        tools = {
            "claude_code": self._claude_code,
            "git": self._git,
            "gh": self._gh,
            "docker": self._docker,
            "playwright": "playwright",
            "python3": "python3",
        }

        for name, cmd in tools.items():
            try:
                proc = await asyncio.create_subprocess_exec(
                    cmd, "--version",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                await asyncio.wait_for(proc.communicate(), timeout=5)
                if proc.returncode == 0:
                    available.append(name)
            except Exception:
                pass

        return available
