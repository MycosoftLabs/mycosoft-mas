"""
Finance discovery and delegation layer — CFO-facing contract.

Dynamically discovers finance agents, services, workflows, and tasks from:
- Agent registry (AgentCategory.FINANCIAL)
- Integration clients (mercury, quickbooks, relay, etc.)
- n8n workflows (filtered by finance-related names/tags)
- C-Suite API (reports, escalations, CFO assistant status)

New finance capabilities become visible automatically without code changes.

Created: March 8, 2026
"""

import logging
import os
from importlib import import_module
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger("finance.discovery")

# Finance-related keywords for filtering n8n workflows and services
_FINANCE_KEYWORDS = {"finance", "financial", "budget", "invoice", "payment", "relay", "mercury", "quickbooks", "treasury", "cfo"}

# Known finance integration modules (discovered from integrations package)
_FINANCE_SERVICE_IDS = [
    "mercury_client",
    "quickbooks_client",
    "relay_client",
    "cap_table_service",
    "safe_agreement_client",
    "financial_markets_client",
]


def list_finance_agents() -> List[Dict[str, Any]]:
    """List all finance agents from the agent registry (dynamic discovery)."""
    try:
        from mycosoft_mas.core.agent_registry import get_agent_registry, AgentCategory
        registry = get_agent_registry()
        agents = registry.list_by_category(AgentCategory.FINANCIAL)
        return [
            {
                "agent_id": a.agent_id,
                "name": a.display_name or a.name,
                "description": a.description or "",
                "capabilities": [c.value for c in (a.capabilities or [])],
            }
            for a in agents
        ]
    except Exception as e:
        logger.warning("list_finance_agents failed: %s", e)
        return []


def list_finance_services() -> List[Dict[str, Any]]:
    """List finance-related integration services (from known integration modules)."""
    results = []
    for sid in _FINANCE_SERVICE_IDS:
        mod_path = f"mycosoft_mas.integrations.{sid}"
        try:
            import_module(mod_path)
            results.append({
                "service_id": sid,
                "available": True,
                "module": mod_path,
            })
        except ImportError:
            results.append({
                "service_id": sid,
                "available": False,
                "module": mod_path,
                "note": "module not found",
            })
    return results


async def list_finance_workloads() -> List[Dict[str, Any]]:
    """List finance-related n8n workflows (dynamic discovery)."""
    try:
        from mycosoft_mas.integrations.n8n_client import N8NClient
        async with N8NClient() as client:
            workflows = await client.get_workflows()
        finance_workloads = []
        for w in workflows:
            name = (w.get("name") or "").lower()
            tags = " ".join(w.get("tags", []) or []).lower()
            combined = f"{name} {tags}"
            if any(kw in combined for kw in _FINANCE_KEYWORDS):
                finance_workloads.append({
                    "id": w.get("id"),
                    "name": w.get("name"),
                    "active": w.get("active", False),
                    "createdAt": w.get("createdAt"),
                })
        return finance_workloads
    except Exception as e:
        logger.warning("list_finance_workloads failed: %s", e)
        return []


async def list_finance_tasks() -> List[Dict[str, Any]]:
    """List finance tasks from C-Suite CFO reports and recent activity."""
    try:
        base = os.getenv("MAS_API_URL", "http://192.168.0.188:8001")
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(f"{base}/api/csuite/assistants", params={"role": "CFO"})
            if r.status_code != 200:
                return []
            data = r.json()
            tasks = []
            for a in data.get("assistants", []):
                last_report = a.get("last_report")
                if last_report:
                    tasks.append({
                        "role": a.get("role"),
                        "assistant": a.get("assistant_name"),
                        "report_type": last_report.get("type"),
                        "summary": last_report.get("summary", "")[:200],
                        "task_id": last_report.get("task_id"),
                        "at": last_report.get("at"),
                    })
            return tasks
    except Exception as e:
        logger.warning("list_finance_tasks failed: %s", e)
        return []


async def delegate_finance_task(
    agent_id: str,
    task: Dict[str, Any],
) -> Dict[str, Any]:
    """Delegate a task to a finance agent. Instantiates agent from registry and runs process_task."""
    try:
        from mycosoft_mas.core.agent_registry import get_agent_registry, AgentCategory
        registry = get_agent_registry()
        # Resolve alias (e.g. financial_agent -> financial)
        defn = registry.get(agent_id)
        if not defn:
            # Try finding by keyword
            agents = registry.list_by_category(AgentCategory.FINANCIAL)
            defn = next((a for a in agents if a.agent_id == agent_id), None)
        if not defn:
            return {"status": "error", "error": f"agent not found: {agent_id}"}

        module = import_module(defn.module_path)
        cls = getattr(module, defn.class_name)
        config = {}
        instance = cls(
            agent_id=defn.agent_id,
            name=defn.display_name or defn.name,
            config=config,
        )
        task_payload = {"type": task.get("type", "execute"), **task}
        result = await instance.process_task(task_payload)
        return {"status": "ok", "agent_id": agent_id, "result": result}
    except Exception as e:
        logger.exception("delegate_finance_task failed for %s: %s", agent_id, e)
        return {"status": "error", "agent_id": agent_id, "error": str(e)}


async def submit_finance_report(
    role: str = "CFO",
    assistant_name: str = "Meridian",
    report_type: str = "operating_report",
    summary: str = "",
    details: Optional[Dict[str, Any]] = None,
    task_id: Optional[str] = None,
    escalated: bool = False,
) -> Dict[str, Any]:
    """Submit a finance report to the C-Suite API (persists and routes to MYCA/Meridian)."""
    try:
        base = os.getenv("MAS_API_URL", "http://192.168.0.188:8001")
        payload = {
            "role": role,
            "assistant_name": assistant_name,
            "report_type": report_type,
            "summary": summary,
            "details": details,
            "task_id": task_id,
            "escalated": escalated,
        }
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(f"{base}/api/csuite/report", json=payload)
            r.raise_for_status()
            return r.json()
    except Exception as e:
        logger.warning("submit_finance_report failed: %s", e)
        return {"status": "error", "error": str(e)}


async def get_finance_status() -> Dict[str, Any]:
    """Aggregate finance status: agents, services, CFO assistant, last reports."""
    agents = list_finance_agents()
    services = list_finance_services()
    workloads = await list_finance_workloads()
    tasks = await list_finance_tasks()

    cfo_status = None
    try:
        base = os.getenv("MAS_API_URL", "http://192.168.0.188:8001")
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(f"{base}/api/csuite/assistants", params={"role": "CFO"})
            if r.status_code == 200:
                data = r.json()
                assistants = data.get("assistants", [])
                if assistants:
                    cfo_status = assistants[0]
    except Exception as e:
        logger.debug("get_finance_status cfo fetch failed: %s", e)

    return {
        "agents_count": len(agents),
        "agents": agents,
        "services_count": len(services),
        "services": services,
        "workloads_count": len(workloads),
        "workloads": workloads,
        "recent_tasks_count": len(tasks),
        "recent_tasks": tasks,
        "cfo_assistant": cfo_status,
    }


async def get_finance_alerts() -> List[Dict[str, Any]]:
    """Return finance-related alerts: escalations, stale reports, etc."""
    alerts = []
    try:
        base = os.getenv("MAS_API_URL", "http://192.168.0.188:8001")
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(f"{base}/api/csuite/assistants", params={"role": "CFO"})
            if r.status_code != 200:
                return alerts
            data = r.json()
            for a in data.get("assistants", []):
                last_esc = a.get("last_escalation")
                if last_esc:
                    alerts.append({
                        "type": "escalation",
                        "role": a.get("role"),
                        "assistant": a.get("assistant_name"),
                        "subject": last_esc.get("subject"),
                        "urgency": last_esc.get("urgency"),
                        "at": last_esc.get("at"),
                    })
                # Stale heartbeat check (e.g. >2 min)
                last_hb = a.get("last_heartbeat")
                if last_hb:
                    from datetime import datetime, timezone
                    try:
                        dt = datetime.fromisoformat(last_hb.replace("Z", "+00:00"))
                        age_sec = (datetime.now(timezone.utc) - dt).total_seconds()
                        if age_sec > 120:
                            alerts.append({
                                "type": "stale_heartbeat",
                                "role": a.get("role"),
                                "assistant": a.get("assistant_name"),
                                "age_seconds": int(age_sec),
                                "last_heartbeat": last_hb,
                            })
                    except Exception:
                        pass
    except Exception as e:
        logger.warning("get_finance_alerts failed: %s", e)
    return alerts
