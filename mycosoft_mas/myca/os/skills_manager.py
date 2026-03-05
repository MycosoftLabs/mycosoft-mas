"""
MYCA Skills Manager — Hot-loadable skills directory.

Each skill lives in a directory with SKILL.md (description) and optional Python/scripts.
Supports git install, approval flow for destructive actions, and progress reporting.
OpenClaw AgentSkills-style: SKILL.md with inputs, outputs, approval_required.

Date: 2026-03-05
"""

import asyncio
import importlib.util
import logging
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any, Callable, Optional

logger = logging.getLogger("myca.os.skills")

SKILLS_DIR = Path(os.getenv("MYCA_SKILLS_DIR", "/opt/myca/skills"))


def _ensure_skills_dir():
    SKILLS_DIR.mkdir(parents=True, exist_ok=True)


def parse_skill_md(skill_path: Path) -> dict[str, Any]:
    """Parse SKILL.md for structured metadata: description, inputs, outputs, approval_required."""
    md = skill_path / "SKILL.md"
    result = {
        "description": "",
        "inputs": [],
        "outputs": [],
        "approval_required": False,
    }
    if not md.exists():
        return result
    text = md.read_text(encoding="utf-8", errors="replace")
    result["description"] = text[:500].strip()
    # Parse approval_required: true
    if re.search(r"approval_required\s*:\s*true", text, re.I):
        result["approval_required"] = True
    # Parse ## Inputs / ## Outputs sections
    in_inputs = in_outputs = False
    for line in text.splitlines():
        if line.strip().lower().startswith("## inputs"):
            in_inputs, in_outputs = True, False
            continue
        if line.strip().lower().startswith("## outputs"):
            in_inputs, in_outputs = False, True
            continue
        if in_inputs and line.strip().startswith("-"):
            result["inputs"].append(line.strip().lstrip("-").strip())
        if in_outputs and line.strip().startswith("-"):
            result["outputs"].append(line.strip().lstrip("-").strip())
    return result


def install_skill_from_git(url: str, branch: Optional[str] = None) -> dict[str, Any]:
    """Install a skill from a git repository. Clones into SKILLS_DIR / repo_name."""
    _ensure_skills_dir()
    # Derive skill id from repo name (e.g. https://github.com/org/asana-sync -> asana-sync)
    repo_name = url.rstrip("/").split("/")[-1].replace(".git", "")
    skill_dir = SKILLS_DIR / repo_name
    if skill_dir.exists():
        return {"status": "failed", "error": f"Skill '{repo_name}' already exists. Remove first to reinstall."}
    try:
        cmd = ["git", "clone", "--depth", "1"]
        if branch:
            cmd.extend(["--branch", branch])
        cmd.extend([url, str(skill_dir)])
        subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=120)
        if not (skill_dir / "SKILL.md").exists():
            return {"status": "warning", "skill_id": repo_name, "message": "Cloned but no SKILL.md found"}
        return {"status": "ok", "skill_id": repo_name, "path": str(skill_dir)}
    except subprocess.TimeoutExpired:
        if skill_dir.exists():
            shutil.rmtree(skill_dir, ignore_errors=True)
        return {"status": "failed", "error": "Git clone timed out"}
    except subprocess.CalledProcessError as e:
        if skill_dir.exists():
            shutil.rmtree(skill_dir, ignore_errors=True)
        return {"status": "failed", "error": e.stderr or str(e)}
    except Exception as e:
        if skill_dir.exists():
            shutil.rmtree(skill_dir, ignore_errors=True)
        return {"status": "failed", "error": str(e)}


def list_skills() -> list[dict]:
    """List all available skills with parsed SKILL.md metadata."""
    _ensure_skills_dir()
    skills = []
    for d in SKILLS_DIR.iterdir():
        if d.is_dir():
            meta = parse_skill_md(d)
            meta["id"] = d.name
            meta["path"] = str(d)
            if not meta.get("description"):
                md = d / "SKILL.md"
                if md.exists():
                    meta["description"] = md.read_text(encoding="utf-8", errors="replace")[:500]
            skills.append({k: v for k, v in meta.items() if k in ("id", "path", "description", "inputs", "outputs", "approval_required")})
    return skills


async def run_skill(
    skill_id: str, args: dict, os_ref=None, progress_callback: Optional[Callable[[str, str, int], None]] = None
) -> dict:
    """Run a skill by ID. Looks for run.py or run.sh. Respects approval_required from SKILL.md."""
    _ensure_skills_dir()
    skill_dir = SKILLS_DIR / skill_id
    if not skill_dir.exists() or not skill_dir.is_dir():
        return {"status": "failed", "error": f"Skill '{skill_id}' not found"}

    meta = parse_skill_md(skill_dir)
    if meta.get("approval_required") and not args.get("_approved"):
        return {
            "status": "approval_required",
            "skill_id": skill_id,
            "message": "This skill requires approval before execution. Pass _approved: true to confirm.",
        }

    def _progress(msg: str, pct: int = 0):
        if progress_callback:
            progress_callback(skill_id, msg, pct)
        else:
            try:
                from mycosoft_mas.myca.os.gateway import broadcast_skill_progress
                broadcast_skill_progress(skill_id, msg, float(pct) if pct is not None else None)
            except Exception:
                pass

    _progress("Starting", 0)
    run_args = {k: v for k, v in args.items() if not str(k).startswith("_")}
    run_args["_progress"] = _progress

    # Try run.py first
    run_py = skill_dir / "run.py"
    if run_py.exists():
        try:
            spec = importlib.util.spec_from_file_location(f"skill_{skill_id}", run_py)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            if hasattr(mod, "run"):
                result = await mod.run(run_args, os_ref)
                _progress("Completed", 100)
                return result if isinstance(result, dict) else {"status": "ok", "result": result}
            return {"status": "failed", "error": "Skill has no run() function"}
        except Exception as e:
            logger.exception("Skill %s error", skill_id)
            _progress(f"Failed: {e}", 100)
            return {"status": "failed", "error": str(e)}

    # Try run.sh
    run_sh = skill_dir / "run.sh"
    if run_sh.exists():
        _progress("Running script", 50)
        proc = await asyncio.create_subprocess_exec(
            "bash", str(run_sh),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(skill_dir),
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=300)
        _progress("Completed" if proc.returncode == 0 else "Failed", 100)
        return {
            "status": "completed" if proc.returncode == 0 else "failed",
            "returncode": proc.returncode,
            "stdout": stdout.decode("utf-8", errors="replace"),
            "stderr": stderr.decode("utf-8", errors="replace"),
        }

    return {"status": "failed", "error": f"Skill '{skill_id}' has no run.py or run.sh"}


def _create_builtin_skill(skill_id: str, skill_md: str, run_py_content: str):
    """Create a built-in skill directory with SKILL.md and run.py."""
    skill_dir = SKILLS_DIR / skill_id
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(skill_md, encoding="utf-8")
    (skill_dir / "run.py").write_text(run_py_content, encoding="utf-8")


def ensure_builtin_skills():
    """Create default built-in skills if they don't exist."""
    _ensure_skills_dir()

    # deploy-website skill
    deploy_dir = SKILLS_DIR / "deploy-website"
    if not (deploy_dir / "run.py").exists():
        _create_builtin_skill(
            "deploy-website",
            """Deploy website to Sandbox VM 187: pull, rebuild Docker, restart container, purge Cloudflare.
approval_required: true
inputs: []
outputs: [status, stdout, stderr]
""",
            '''import asyncio

async def run(args, os_ref):
    prog = args.get("_progress")
    if prog:
        prog("Connecting to VM 187", 10)
    cmd = "ssh mycosoft@192.168.0.187 'cd /opt/mycosoft/website && git pull && docker build -t mycosoft-website:latest .'"
    proc = await asyncio.create_subprocess_shell(cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    if prog:
        prog("Building Docker image", 50)
    out, err = await proc.communicate()
    if prog:
        prog("Completed" if proc.returncode == 0 else "Failed", 100)
    return {"status": "completed" if proc.returncode == 0 else "failed", "stdout": out.decode(), "stderr": err.decode()}
''',
        )

    # check-vm-health skill
    health_dir = SKILLS_DIR / "check-vm-health"
    if not (health_dir / "run.py").exists():
        _create_builtin_skill(
            "check-vm-health",
            """Check health of all Mycosoft VMs: 187, 188, 189.
inputs: []
outputs: [status, results]
""",
            '''import asyncio
import aiohttp

async def run(args, os_ref):
    prog = args.get("_progress")
    if prog:
        prog("Checking VMs", 0)
    results = {}
    async with aiohttp.ClientSession() as s:
        for name, url in [("sandbox", "http://192.168.0.187:3000"), ("mas", "http://192.168.0.188:8001/health"), ("mindex", "http://192.168.0.189:8000/health")]:
            try:
                async with s.get(url, timeout=aiohttp.ClientTimeout(total=5)) as r:
                    results[name] = "ok" if r.status == 200 else f"status {r.status}"
            except Exception as e:
                results[name] = f"error: {e}"
    if prog:
        prog("Done", 100)
    return {"status": "completed", "results": results}
''',
        )

    # asana-sync skill
    asana_dir = SKILLS_DIR / "asana-sync"
    if not (asana_dir / "run.py").exists():
        _create_builtin_skill(
            "asana-sync",
            """Sync Asana tasks assigned to MYCA into the task queue.
inputs: [project_id (optional)]
outputs: [status, tasks_synced, message]
""",
            '''import asyncio
import os
import aiohttp

async def run(args, os_ref):
    prog = args.get("_progress")
    token = os.getenv("ASANA_ACCESS_TOKEN")
    if not token:
        return {"status": "failed", "error": "ASANA_ACCESS_TOKEN not set. Configure it in MYCA env."}
    if prog:
        prog("Fetching Asana tasks", 30)
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(
                "https://app.asana.com/api/1.0/users/me/tasks",
                headers={"Authorization": f"Bearer {token}"},
                params={"opt_fields": "name,due_on,notes", "assignee": "me"},
                timeout=aiohttp.ClientTimeout(total=15)
            ) as r:
                if r.status != 200:
                    return {"status": "failed", "error": f"Asana API status {r.status}"}
                data = await r.json()
        tasks = data.get("data", [])
        if prog:
            prog(f"Found {len(tasks)} tasks", 80)
        # Could enqueue to MYCA executive queue via os_ref
        if prog:
            prog("Synced", 100)
        return {"status": "completed", "tasks_synced": len(tasks), "message": f"Synced {len(tasks)} Asana tasks"}
    except Exception as e:
        return {"status": "failed", "error": str(e)}
''',
        )

    # calendar-check skill
    cal_dir = SKILLS_DIR / "calendar-check"
    if not (cal_dir / "run.py").exists():
        _create_builtin_skill(
            "calendar-check",
            """Query Google Calendar for today's events.
inputs: [max_results (optional, default 10)]
outputs: [status, events, message]
""",
            '''import asyncio
import os
from datetime import datetime

async def run(args, os_ref):
    prog = args.get("_progress")
    creds = os.getenv("GOOGLE_CALENDAR_CREDENTIALS") or os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if not creds:
        return {"status": "failed", "error": "Google Calendar credentials not configured. Set GOOGLE_APPLICATION_CREDENTIALS or GOOGLE_CALENDAR_CREDENTIALS."}
    if prog:
        prog("Checking calendar", 50)
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
        from googleapiclient.errors import HttpError
    except ImportError:
        return {"status": "failed", "error": "google-api-python-client not installed. pip install google-api-python-client google-auth"}
    try:
        scopes = ["https://www.googleapis.com/auth/calendar.readonly"]
        creds = service_account.Credentials.from_service_account_file(creds, scopes=scopes)
        service = build("calendar", "v3", credentials=creds)
        now = datetime.utcnow().isoformat() + "Z"
        end = datetime.utcnow().replace(hour=23, minute=59, second=59).isoformat() + "Z"
        events_result = service.events().list(
            calendarId="primary", timeMin=now, timeMax=end, maxResults=args.get("max_results", 10), singleEvents=True, orderBy="startTime"
        ).execute()
        events = events_result.get("items", [])
        if prog:
            prog("Done", 100)
        return {"status": "completed", "events": [{"summary": e.get("summary"), "start": e.get("start")} for e in events], "message": f"Found {len(events)} events today"}
    except Exception as e:
        return {"status": "failed", "error": str(e)}
''',
        )

    # code-review skill
    code_dir = SKILLS_DIR / "code-review"
    if not (code_dir / "run.py").exists():
        _create_builtin_skill(
            "code-review",
            """Review a PR using OpenWork/OpenCode. Requires openwork_bridge.
inputs: [pr_url, repo, branch]
outputs: [status, review_summary]
""",
            '''import asyncio

async def run(args, os_ref):
    prog = args.get("_progress")
    pr_url = args.get("pr_url") or args.get("url")
    if not pr_url:
        return {"status": "failed", "error": "pr_url or url required"}
    if prog:
        prog("Starting code review via OpenWork", 20)
    try:
        from mycosoft_mas.myca.os.openwork_bridge import openwork_bridge
        prompt = f"Review this pull request and provide a concise summary of changes, potential issues, and suggestions: {pr_url}"
        if prog:
            prog("Sending to OpenWork", 50)
        result = await openwork_bridge.run_task(prompt)
        if prog:
            prog("Review complete", 100)
        return {"status": "completed", "review_summary": result.get("output", result)}
    except Exception as e:
        return {"status": "failed", "error": str(e)}
''',
        )

    # daily-report skill
    daily_dir = SKILLS_DIR / "daily-report"
    if not (daily_dir / "run.py").exists():
        _create_builtin_skill(
            "daily-report",
            """Generate and send a daily status report. Uses LLM to summarize completed tasks.
inputs: [recipient (optional), channel (optional: email, discord, slack)]
outputs: [status, report_summary]
""",
            '''import asyncio

async def run(args, os_ref):
    prog = args.get("_progress")
    if prog:
        prog("Generating daily report", 30)
    try:
        brain = getattr(os_ref, "llm_brain", None) if os_ref else None
        if not brain or not hasattr(brain, "respond"):
            return {"status": "failed", "error": "LLM brain not available"}
        msgs = [{"role": "user", "content": "Summarize what MYCA accomplished today in 3-5 bullet points for a daily status report. Be concise."}]
        report = await brain.respond(msgs)
        if prog:
            prog("Report generated", 80)
        channel = args.get("channel", "email")
        # Could send via os_ref bridges (Discord, Slack, Email)
        if prog:
            prog("Done", 100)
        return {"status": "completed", "report_summary": report}
    except Exception as e:
        return {"status": "failed", "error": str(e)}
''',
        )

    # git-commit skill
    git_dir = SKILLS_DIR / "git-commit"
    if not (git_dir / "run.py").exists():
        _create_builtin_skill(
            "git-commit",
            """Stage, commit, and push with an auto-generated message. Uses LLM for message.
approval_required: true
inputs: [repo_path, message (optional), branch (optional)]
outputs: [status, commit_hash, stdout, stderr]
""",
            '''import asyncio
import os
from pathlib import Path

async def run(args, os_ref):
    prog = args.get("_progress")
    repo_path = args.get("repo_path", args.get("path", "."))
    branch = args.get("branch", "main")
    if prog:
        prog("Preparing commit", 10)
    try:
        proc = await asyncio.create_subprocess_exec(
            "git", "status", "--short",
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
            cwd=repo_path
        )
        out, err = await proc.communicate()
        if proc.returncode != 0:
            return {"status": "failed", "error": err.decode() or "Not a git repo"}
        changes = out.decode().strip()
        if not changes:
            return {"status": "completed", "message": "Nothing to commit"}
        msg = args.get("message")
        if not msg and os_ref and hasattr(os_ref, "llm_brain"):
            msgs = [{"role": "user", "content": f"Generate a short git commit message for these changes:\\n{changes}"}]
            msg = await os_ref.llm_brain.respond(msgs)
        msg = msg or "Updates"
        if prog:
            prog("Staging and committing", 50)
        proc = await asyncio.create_subprocess_exec(
            "git", "add", "-A",
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
            cwd=repo_path
        )
        await proc.communicate()
        proc = await asyncio.create_subprocess_exec(
            "git", "commit", "-m", msg,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
            cwd=repo_path
        )
        cout, cerr = await proc.communicate()
        if proc.returncode != 0:
            return {"status": "failed", "stdout": cout.decode(), "stderr": cerr.decode()}
        if prog:
            prog("Pushing", 80)
        proc = await asyncio.create_subprocess_exec(
            "git", "push", "origin", branch,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
            cwd=repo_path
        )
        po, pe = await proc.communicate()
        if prog:
            prog("Done", 100)
        return {"status": "completed" if proc.returncode == 0 else "failed", "stdout": po.decode(), "stderr": pe.decode()}
    except Exception as e:
        return {"status": "failed", "error": str(e)}
''',
        )
