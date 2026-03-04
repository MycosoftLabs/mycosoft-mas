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
        action = task.get("action", "read")  # read, search, fill_form, screenshot
        query = task.get("query", "")

        try:
            if action == "search":
                return await self._browser_search(query)
            elif action == "read":
                return await self._browser_read(url)
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

    # ── n8n Workflows ────────────────────────────────────────────

    async def trigger_n8n_workflow(self, task: dict) -> dict:
        """Trigger an n8n workflow on MYCA's personal n8n (VM 191)."""
        workflow_name = task.get("workflow", "")
        data = task.get("data", {})

        if not self._n8n_api_key:
            return {"status": "failed", "error": "MYCA n8n API key not configured"}

        headers = {"X-N8N-API-KEY": self._n8n_api_key}

        try:
            # Find workflow by name
            async with self._session.get(
                f"{self._n8n_url}/api/v1/workflows",
                headers=headers,
            ) as resp:
                workflows = (await resp.json()).get("data", [])
                wf = next((w for w in workflows if w["name"] == workflow_name), None)

            if not wf:
                return {"status": "failed", "error": f"Workflow '{workflow_name}' not found"}

            # Trigger via webhook or execution
            async with self._session.post(
                f"{self._n8n_url}/api/v1/workflows/{wf['id']}/activate",
                headers=headers,
            ) as resp:
                pass

            return {
                "status": "completed",
                "summary": f"Triggered workflow: {workflow_name}",
                "workflow_id": wf["id"],
            }
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
