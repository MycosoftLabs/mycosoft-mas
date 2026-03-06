#!/usr/bin/env python3
"""
MYCA VM 191 — Full Workstation Status Check

Comprehensive status check for MYCA's workspace VM (192.168.0.191).
Checks everything needed for MYCA to operate as a fully automated employee:
  - VM reachability (SSH, ports)
  - Docker containers (workspace, postgres, redis, n8n, caddy, signal-api)
  - Service health endpoints
  - Desktop environment (XRDP, noVNC)
  - Platform credentials readiness
  - n8n workflow deployment status
  - MAS orchestrator connectivity

Run from any machine on the LAN (e.g., Sandbox 187, MAS 188):
    python3 scripts/check_myca_vm_status.py

Requires: pip install paramiko httpx (optional: rich for pretty output)
"""

import json
import logging
import os
import socket
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("myca-vm-check")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
MYCA_VM_IP = os.getenv("MYCA_VM_IP", "192.168.0.191")
MYCA_VM_USER = os.getenv("MYCA_VM_USER", "mycosoft")
MAS_IP = "192.168.0.188"
MINDEX_IP = "192.168.0.189"

# Expected services on VM 191
EXPECTED_CONTAINERS = [
    "myca-workspace",
    "myca-postgres",
    "myca-redis",
    "myca-n8n",
    "myca-caddy",
    "myca-signal-api",
]

EXPECTED_PORTS = {
    "SSH": 22,
    "HTTP (Caddy)": 80,
    "HTTPS (Caddy)": 443,
    "FastAPI Workspace": 8000,
    "n8n": 5678,
    "Redis": 6379,
    "Signal API": 8089,
    "XRDP": 3389,
    "noVNC": 6080,
}

HEALTH_ENDPOINTS = {
    "Workspace API": f"http://{MYCA_VM_IP}:8000/api/workspace/health",
    "Workspace Status": f"http://{MYCA_VM_IP}:8000/api/workspace/status",
    "n8n Health": f"http://{MYCA_VM_IP}:5678/healthz",
    "MAS Orchestrator": f"http://{MAS_IP}:8001/system/health",
    "MINDEX API": f"http://{MINDEX_IP}:8000/health",
}

MYCA_N8N_WORKFLOWS = [
    "myca-health-check.json",
    "myca-discord-to-mas.json",
    "myca-slack-to-mas.json",
    "myca-asana-to-mas.json",
    "myca-signal-to-mas.json",
    "myca-whatsapp-to-mas.json",
    "myca-gmail-to-mas.json",
    "myca-notion-sync.json",
    "myca-doc-query.json",
    "myca-response-router.json",
    "myca-daily-rhythm.json",
    "myca-send-email.json",
]

REQUIRED_CREDENTIALS = [
    "SLACK_BOT_TOKEN",
    "DISCORD_BOT_TOKEN",
    "NOTION_TOKEN",
    "ANTHROPIC_API_KEY",
    "ASANA_PAT",
    "SIGNAL_PHONE_NUMBER",
]

REPO_ROOT = Path(__file__).parent.parent


# ---------------------------------------------------------------------------
# Result tracking
# ---------------------------------------------------------------------------
@dataclass
class CheckResult:
    name: str
    status: str  # "pass", "fail", "warn", "skip"
    detail: str = ""
    latency_ms: float = 0.0


@dataclass
class StatusReport:
    timestamp: str = ""
    vm_ip: str = MYCA_VM_IP
    overall: str = "unknown"
    checks: List[CheckResult] = field(default_factory=list)
    summary: Dict[str, int] = field(default_factory=dict)

    def add(self, result: CheckResult):
        self.checks.append(result)

    def compute_overall(self):
        counts = {"pass": 0, "fail": 0, "warn": 0, "skip": 0}
        for c in self.checks:
            counts[c.status] = counts.get(c.status, 0) + 1
        self.summary = counts
        if counts["fail"] > 0:
            self.overall = "UNHEALTHY"
        elif counts["warn"] > 2:
            self.overall = "DEGRADED"
        elif counts["warn"] > 0:
            self.overall = "PARTIAL"
        else:
            self.overall = "HEALTHY"

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "vm_ip": self.vm_ip,
            "overall": self.overall,
            "summary": self.summary,
            "checks": [
                {"name": c.name, "status": c.status, "detail": c.detail, "latency_ms": c.latency_ms}
                for c in self.checks
            ],
        }


# ---------------------------------------------------------------------------
# Check functions
# ---------------------------------------------------------------------------

def _load_credentials() -> dict:
    """Load credentials from .credentials.local or environment."""
    cred_paths = [
        REPO_ROOT / ".credentials.local",
        Path.home() / ".mycosoft-credentials",
        Path("/opt/myca/credentials/.env"),
    ]
    for p in cred_paths:
        if p.exists():
            for line in p.read_text().splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ.setdefault(key.strip(), value.strip())
            break
    return {
        "vm_password": os.getenv("VM_PASSWORD", os.getenv("VM_SSH_PASSWORD", "")),
    }


def check_port_reachability(report: StatusReport):
    """Check if expected ports are open on VM 191."""
    logger.info("=== Port Reachability ===")
    for name, port in EXPECTED_PORTS.items():
        start = time.time()
        try:
            sock = socket.create_connection((MYCA_VM_IP, port), timeout=5)
            sock.close()
            ms = (time.time() - start) * 1000
            report.add(CheckResult(f"Port: {name} ({port})", "pass", "open", ms))
            logger.info("  [PASS] %-25s port %d open (%.0fms)", name, port, ms)
        except (socket.timeout, ConnectionRefusedError, OSError) as e:
            ms = (time.time() - start) * 1000
            report.add(CheckResult(f"Port: {name} ({port})", "fail", str(e), ms))
            logger.info("  [FAIL] %-25s port %d closed", name, port)


def check_health_endpoints(report: StatusReport):
    """Check HTTP health endpoints."""
    logger.info("=== Health Endpoints ===")
    try:
        import httpx
    except ImportError:
        try:
            from urllib.request import urlopen, Request
            from urllib.error import URLError
            for name, url in HEALTH_ENDPOINTS.items():
                start = time.time()
                try:
                    req = Request(url, headers={"User-Agent": "myca-check/1.0"})
                    resp = urlopen(req, timeout=5)
                    ms = (time.time() - start) * 1000
                    body = resp.read().decode()[:200]
                    report.add(CheckResult(f"HTTP: {name}", "pass", f"{resp.status} - {body}", ms))
                    logger.info("  [PASS] %-25s %d (%.0fms)", name, resp.status, ms)
                except Exception as e:
                    ms = (time.time() - start) * 1000
                    report.add(CheckResult(f"HTTP: {name}", "fail", str(e)[:100], ms))
                    logger.info("  [FAIL] %-25s %s", name, str(e)[:60])
            return
        except ImportError:
            for name in HEALTH_ENDPOINTS:
                report.add(CheckResult(f"HTTP: {name}", "skip", "no http library"))
            return

    client = httpx.Client(timeout=5, verify=False)
    for name, url in HEALTH_ENDPOINTS.items():
        start = time.time()
        try:
            resp = client.get(url)
            ms = (time.time() - start) * 1000
            body = resp.text[:200]
            status = "pass" if resp.status_code < 400 else "warn"
            report.add(CheckResult(f"HTTP: {name}", status, f"{resp.status_code} - {body}", ms))
            logger.info("  [%s] %-25s %d (%.0fms)", status.upper(), name, resp.status_code, ms)
        except Exception as e:
            ms = (time.time() - start) * 1000
            report.add(CheckResult(f"HTTP: {name}", "fail", str(e)[:100], ms))
            logger.info("  [FAIL] %-25s %s", name, str(e)[:60])
    client.close()


def check_ssh_deep(report: StatusReport, password: str):
    """SSH into VM and run deep checks (containers, disk, memory, services)."""
    logger.info("=== SSH Deep Check ===")
    try:
        import paramiko
    except ImportError:
        report.add(CheckResult("SSH Deep Check", "skip", "paramiko not installed"))
        logger.info("  [SKIP] paramiko not installed — pip install paramiko")
        return

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    # Try SSH key first, then password
    key_path = os.path.expanduser("~/.ssh/myca_vm191")
    try:
        if os.path.exists(key_path):
            ssh.connect(MYCA_VM_IP, username=MYCA_VM_USER,
                        pkey=paramiko.Ed25519Key.from_private_key_file(key_path), timeout=15)
        elif password:
            ssh.connect(MYCA_VM_IP, username=MYCA_VM_USER, password=password, timeout=15)
        else:
            report.add(CheckResult("SSH Connection", "fail", "No SSH key or password available"))
            logger.info("  [FAIL] No SSH credentials available")
            return
        report.add(CheckResult("SSH Connection", "pass", f"connected as {MYCA_VM_USER}"))
        logger.info("  [PASS] SSH connected as %s", MYCA_VM_USER)
    except Exception as e:
        report.add(CheckResult("SSH Connection", "fail", str(e)[:100]))
        logger.info("  [FAIL] SSH: %s", str(e)[:80])
        return

    def run(cmd: str) -> str:
        _, stdout, stderr = ssh.exec_command(cmd, timeout=30)
        return stdout.read().decode(errors="replace").strip()

    try:
        # System info
        uptime = run("uptime")
        report.add(CheckResult("VM Uptime", "pass", uptime))
        logger.info("  [PASS] Uptime: %s", uptime[:80])

        # Memory
        mem = run("free -h | grep Mem")
        report.add(CheckResult("VM Memory", "pass", mem))
        logger.info("  [PASS] Memory: %s", mem)

        # Disk
        disk = run("df -h / | tail -1")
        usage_pct = int(disk.split()[-2].replace("%", "")) if disk else 0
        status = "pass" if usage_pct < 80 else ("warn" if usage_pct < 90 else "fail")
        report.add(CheckResult("VM Disk", status, disk))
        logger.info("  [%s] Disk: %s", status.upper(), disk)

        # CPU cores
        cores = run("nproc")
        report.add(CheckResult("VM CPU Cores", "pass", f"{cores} cores"))
        logger.info("  [PASS] CPU: %s cores", cores)

        # Docker containers
        logger.info("  --- Docker Containers ---")
        containers = run("docker ps --format '{{.Names}}|{{.Status}}|{{.Ports}}' 2>/dev/null")
        if containers:
            running_names = []
            for line in containers.splitlines():
                parts = line.split("|")
                cname = parts[0] if parts else "unknown"
                cstatus = parts[1] if len(parts) > 1 else "unknown"
                running_names.append(cname)
                is_healthy = "healthy" in cstatus.lower() or "up" in cstatus.lower()
                s = "pass" if is_healthy else "warn"
                report.add(CheckResult(f"Container: {cname}", s, cstatus))
                logger.info("    [%s] %-25s %s", s.upper(), cname, cstatus[:50])

            # Check for missing containers
            for expected in EXPECTED_CONTAINERS:
                if expected not in running_names:
                    report.add(CheckResult(f"Container: {expected}", "fail", "NOT RUNNING"))
                    logger.info("    [FAIL] %-25s NOT RUNNING", expected)
        else:
            report.add(CheckResult("Docker", "fail", "No containers running or docker not available"))
            logger.info("    [FAIL] No docker containers found")

        # Docker compose status
        compose = run("cd /opt/myca && docker compose ps --format json 2>/dev/null || echo 'no-compose'")
        if "no-compose" not in compose:
            report.add(CheckResult("Docker Compose", "pass", "active at /opt/myca/"))
        else:
            report.add(CheckResult("Docker Compose", "warn", "docker compose not found at /opt/myca/"))

        # Desktop environment
        logger.info("  --- Desktop Environment ---")
        xrdp = run("systemctl is-active xrdp 2>/dev/null || echo 'inactive'")
        report.add(CheckResult("XRDP (Remote Desktop)", "pass" if xrdp == "active" else "warn", xrdp))
        logger.info("  [%s] XRDP: %s", "PASS" if xrdp == "active" else "WARN", xrdp)

        novnc = run("systemctl is-active novnc 2>/dev/null || echo 'inactive'")
        report.add(CheckResult("noVNC (Web Desktop)", "pass" if novnc == "active" else "warn", novnc))
        logger.info("  [%s] noVNC: %s", "PASS" if novnc == "active" else "WARN", novnc)

        # GUI apps
        for app, cmd in [("Chrome", "which google-chrome"), ("VS Code", "which code"), ("Node.js", "node -v"), ("GitHub CLI", "gh --version | head -1")]:
            result = run(cmd)
            s = "pass" if result else "warn"
            report.add(CheckResult(f"App: {app}", s, result or "not found"))
            logger.info("  [%s] %s: %s", s.upper(), app, result[:60] if result else "not found")

        # Claude Code
        claude = run("which claude 2>/dev/null || echo 'not found'")
        report.add(CheckResult("App: Claude Code", "pass" if "not found" not in claude else "warn", claude))

        # n8n workflow files
        logger.info("  --- n8n Workflows ---")
        wf_dir = run("ls /opt/myca/n8n/workflows/ 2>/dev/null || echo 'empty'")
        if wf_dir and "empty" not in wf_dir:
            wf_files = wf_dir.splitlines()
            report.add(CheckResult("n8n Workflow Files", "pass", f"{len(wf_files)} workflows deployed"))
            logger.info("  [PASS] %d n8n workflow files found", len(wf_files))
        else:
            report.add(CheckResult("n8n Workflow Files", "fail", "No workflows in /opt/myca/n8n/workflows/"))
            logger.info("  [FAIL] No n8n workflow files found")

        # Credentials check
        logger.info("  --- Credential Files ---")
        cred_dirs = run("ls -d /opt/myca/credentials/*/ 2>/dev/null || echo 'none'")
        if "none" not in cred_dirs:
            report.add(CheckResult("Credential Directories", "pass", cred_dirs.replace("\n", ", ")))
        else:
            report.add(CheckResult("Credential Directories", "warn", "No credential directories found"))

        # Env file
        env_exists = run("test -f /opt/myca/.env && echo 'yes' || echo 'no'")
        report.add(CheckResult("Env File (/opt/myca/.env)", "pass" if env_exists == "yes" else "fail", env_exists))

        # Check if credentials are actually populated (not placeholder)
        for cred_var in REQUIRED_CREDENTIALS:
            val = run(f"grep -c '^{cred_var}=.' /opt/myca/.env 2>/dev/null || echo '0'")
            has_value = val.strip() != "0"
            s = "pass" if has_value else "warn"
            report.add(CheckResult(f"Credential: {cred_var}", s, "configured" if has_value else "MISSING"))
            logger.info("  [%s] %s: %s", s.upper(), cred_var, "configured" if has_value else "MISSING")

        # MAS repo
        repo = run("cd /opt/myca/mycosoft-mas && git log --oneline -1 2>/dev/null || echo 'no-repo'")
        if "no-repo" not in repo:
            report.add(CheckResult("MAS Repo", "pass", repo))
            logger.info("  [PASS] MAS repo: %s", repo[:60])
        else:
            report.add(CheckResult("MAS Repo", "warn", "Not cloned at /opt/myca/mycosoft-mas"))

        # Firewall
        ufw = run("sudo ufw status 2>/dev/null | head -5 || echo 'unknown'")
        report.add(CheckResult("Firewall (UFW)", "pass", ufw.replace("\n", " ")[:100]))

    finally:
        ssh.close()


def check_credentials_local(report: StatusReport):
    """Check if credential env vars are set locally (for deployment)."""
    logger.info("=== Local Credential Vars ===")
    for var in REQUIRED_CREDENTIALS:
        val = os.getenv(var, "")
        s = "pass" if val else "warn"
        report.add(CheckResult(f"Local Env: {var}", s, "set" if val else "NOT SET"))
        if not val:
            logger.info("  [WARN] %s not set in local env", var)


def check_workflow_files(report: StatusReport):
    """Check that all expected n8n workflow JSON files exist in the repo."""
    logger.info("=== Workflow Files (repo) ===")
    wf_dir = REPO_ROOT / "workflows" / "n8n"
    for wf in MYCA_N8N_WORKFLOWS:
        path = wf_dir / wf
        s = "pass" if path.exists() else "warn"
        report.add(CheckResult(f"Workflow: {wf}", s, "exists" if path.exists() else "MISSING from repo"))
        if not path.exists():
            logger.info("  [WARN] %s not in repo", wf)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    import argparse
    parser = argparse.ArgumentParser(description="MYCA VM 191 — Full Workstation Status Check")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--skip-ssh", action="store_true", help="Skip SSH deep checks")
    parser.add_argument("--quick", action="store_true", help="Port check only (fastest)")
    args = parser.parse_args()

    report = StatusReport(timestamp=datetime.now(timezone.utc).isoformat())

    creds = _load_credentials()

    logger.info("=" * 65)
    logger.info("  MYCA VM 191 — Full Workstation Status Check")
    logger.info("  Target: %s | Time: %s", MYCA_VM_IP, report.timestamp)
    logger.info("=" * 65)

    # Phase 1: Port reachability (always)
    check_port_reachability(report)

    if args.quick:
        report.compute_overall()
        _output(report, args.json)
        return

    # Phase 2: HTTP health endpoints
    check_health_endpoints(report)

    # Phase 3: Workflow files in repo
    check_workflow_files(report)

    # Phase 4: Local credential env vars
    check_credentials_local(report)

    # Phase 5: SSH deep check (containers, disk, desktop, n8n, creds)
    if not args.skip_ssh:
        check_ssh_deep(report, creds.get("vm_password", ""))

    report.compute_overall()
    _output(report, args.json)


def _output(report: StatusReport, as_json: bool):
    """Print the final report."""
    if as_json:
        print(json.dumps(report.to_dict(), indent=2))
        return

    logger.info("")
    logger.info("=" * 65)
    logger.info("  OVERALL STATUS: %s", report.overall)
    logger.info("  Pass: %d | Fail: %d | Warn: %d | Skip: %d",
                report.summary.get("pass", 0),
                report.summary.get("fail", 0),
                report.summary.get("warn", 0),
                report.summary.get("skip", 0))
    logger.info("=" * 65)

    # Print failures and warnings
    failures = [c for c in report.checks if c.status == "fail"]
    warnings = [c for c in report.checks if c.status == "warn"]

    if failures:
        logger.info("")
        logger.info("  FAILURES (must fix):")
        for c in failures:
            logger.info("    [FAIL] %s: %s", c.name, c.detail[:80])

    if warnings:
        logger.info("")
        logger.info("  WARNINGS (should fix):")
        for c in warnings:
            logger.info("    [WARN] %s: %s", c.name, c.detail[:80])

    if not failures and not warnings:
        logger.info("")
        logger.info("  All checks passed! MYCA is fully operational.")

    # Exit code: 0 = healthy, 1 = degraded, 2 = unhealthy
    if report.overall == "UNHEALTHY":
        sys.exit(2)
    elif report.overall in ("DEGRADED", "PARTIAL"):
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
