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
import subprocess
from typing import Optional
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
        self._workspace_url = os.getenv("MYCA_WORKSPACE_URL", "http://localhost:8000")

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

    # ── Claude Code ──────────────────────────────────────────────

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

    # Known workflow name → webhook path (from n8n/workflows/*.json)
    _N8N_WEBHOOK_PATHS: dict[str, str] = {
        "MYCA Ethics Evaluation": "myca/ethics/evaluate-recommendation",
        "MYCA Proactive Monitor": "myca/monitor/check",
        "MYCA Intent Orchestrator": "myca/intent/orchestrator",
    }

    def _get_webhook_path_from_nodes(self, nodes: list) -> Optional[str]:
        """Extract webhook path from workflow nodes."""
        for node in nodes or []:
            if node.get("type") == "n8n-nodes-base.webhook":
                params = node.get("parameters", {})
                path = params.get("path") or params.get("webhookPath")
                if path:
                    return path
        return None

    async def trigger_n8n_workflow(self, task: dict) -> dict:
        """Execute an n8n workflow via webhook trigger (or activate if no webhook).

        Task params:
          - workflow: Workflow name
          - webhook_path: Optional. If set, used directly (skips lookup)
          - data: Payload to POST to webhook (default {})
        """
        workflow_name = task.get("workflow", "")
        webhook_path = task.get("webhook_path", "")
        data = task.get("data", {})

        if not workflow_name and not webhook_path:
            return {"status": "failed", "error": "Missing workflow name or webhook_path"}

        if not self._n8n_api_key:
            return {"status": "failed", "error": "MYCA n8n API key not configured"}

        headers = {"X-N8N-API-KEY": self._n8n_api_key, "Content-Type": "application/json"}

        try:
            # Resolve webhook path
            if webhook_path:
                path = webhook_path
                wf_id = None
            elif workflow_name:
                # Find workflow by name
                async with self._session.get(
                    f"{self._n8n_url}/api/v1/workflows",
                    headers=headers,
                ) as resp:
                    workflows = (await resp.json()).get("data", [])
                    wf = next((w for w in workflows if w["name"] == workflow_name), None)

                if not wf:
                    return {"status": "failed", "error": f"Workflow '{workflow_name}' not found"}

                wf_id = wf["id"]

                # Prefer static map, else fetch workflow and parse nodes
                path = self._N8N_WEBHOOK_PATHS.get(workflow_name)
                if not path:
                    async with self._session.get(
                        f"{self._n8n_url}/api/v1/workflows/{wf_id}",
                        headers=headers,
                    ) as wf_resp:
                        wf_detail = await wf_resp.json()
                        nodes = wf_detail.get("data", {}).get("nodes", [])
                    path = self._get_webhook_path_from_nodes(nodes)

                if not path:
                    # No webhook — activate only (workflow will listen for manual/scheduled triggers)
                    async with self._session.post(
                        f"{self._n8n_url}/api/v1/workflows/{wf_id}/activate",
                        headers=headers,
                    ) as act_resp:
                        pass
                    return {
                        "status": "completed",
                        "summary": f"Activated workflow '{workflow_name}' (no webhook trigger)",
                        "workflow_id": wf_id,
                        "note": "Workflow has no webhook. Use webhook_path for workflows with webhook nodes.",
                    }

                # Ensure workflow is activated so webhook is listening
                async with self._session.post(
                    f"{self._n8n_url}/api/v1/workflows/{wf_id}/activate",
                    headers=headers,
                ) as act_resp:
                    pass
            else:
                return {"status": "failed", "error": "Missing workflow name or webhook_path"}

            # Execute via webhook POST
            webhook_url = f"{self._n8n_url.rstrip('/')}/webhook/{path.lstrip('/')}"
            payload = data if isinstance(data, dict) else {"body": data}

            async with self._session.post(
                webhook_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=aiohttp.ClientTimeout(total=60),
            ) as web_resp:
                body = await web_resp.text()
                try:
                    result = json.loads(body) if body else {}
                except json.JSONDecodeError:
                    result = {"raw": body[:1000]}

            out = {
                "status": "completed",
                "summary": f"Executed workflow via webhook: {path}",
                "webhook_path": path,
                "response": result,
            }
            if wf_id is not None:
                out["workflow_id"] = wf_id
            return out
        except aiohttp.ClientError as e:
            return {"status": "failed", "error": f"n8n request failed: {e}"}
        except Exception as e:
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

        if target == "myca":
            # Local deployment on VM 191
            cmd = [self._docker, "compose", "-f",
                   "/opt/myca/docker-compose.myca-workspace.yml",
                   "up", "-d", "--build"]
        elif target in ("mas", "mindex", "website"):
            # Remote deployment via SSH (needs approval)
            return {
                "status": "needs_approval",
                "summary": f"Deployment to {target} requires Morgan's approval",
                "target": target,
                "action": action,
            }
        else:
            return {"status": "failed", "error": f"Unknown deployment target: {target}"}

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
        """Check health of local services on VM 191."""
        services = {
            "workspace_api": f"{self._workspace_url}/api/workspace/health",
            "n8n": f"{self._n8n_url}/healthz",
        }

        results = {}
        for name, url in services.items():
            try:
                async with self._session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                    results[name] = resp.status == 200
            except Exception:
                results[name] = False

        # Check Docker
        try:
            proc = await asyncio.create_subprocess_exec(
                self._docker, "ps", "--format", "{{.Names}}",
                stdout=asyncio.subprocess.PIPE,
            )
            stdout, _ = await proc.communicate()
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
