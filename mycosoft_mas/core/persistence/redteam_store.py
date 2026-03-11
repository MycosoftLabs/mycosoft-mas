"""
Durable store for red-team simulations.
Uses Supabase red_team_simulations when configured; falls back to in-memory.

Created: March 10, 2026
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from mycosoft_mas.core.persistence.supabase_client import (
    supabase_available,
    supabase_insert,
    supabase_select,
    supabase_update,
)

logger = logging.getLogger(__name__)

# In-memory fallback when Supabase not configured
_memory_simulations: Dict[str, Dict[str, Any]] = {}


class RedTeamStore:
    """Unified store for red-team simulations: Supabase when available, else in-memory."""

    def save(self, simulation: Dict[str, Any]) -> None:
        """Persist a simulation (insert or update)."""
        sim_id = simulation.get("simulation_id")
        if not sim_id:
            return
        row = {
            "simulation_id": sim_id,
            "simulation_type": simulation.get("simulation_type", ""),
            "status": simulation.get("status", ""),
            "target": simulation.get("target"),
            "options": simulation.get("options") or {},
            "description": simulation.get("description"),
            "requested_by": simulation.get("requested_by"),
            "approved_by": simulation.get("approved_by"),
            "approved_at": simulation.get("approved_at"),
            "soc_incident_id": simulation.get("soc_incident_id"),
            "findings": simulation.get("findings") or [],
            "metrics": simulation.get("metrics") or {},
            "recommendations": simulation.get("recommendations") or [],
            "error": simulation.get("error"),
            "started_at": simulation.get("started_at"),
            "completed_at": simulation.get("completed_at"),
        }
        if supabase_available():
            # Upsert by simulation_id
            existing = supabase_select("red_team_simulations", filters={"simulation_id": sim_id}, limit=1)
            if existing:
                supabase_update("red_team_simulations", {"updated_at": datetime.now(timezone.utc), **row}, {"simulation_id": sim_id})
            else:
                supabase_insert("red_team_simulations", {**row, "started_at": row["started_at"] or datetime.now(timezone.utc).isoformat()})
        _memory_simulations[sim_id] = simulation

    def get(self, simulation_id: str) -> Optional[Dict[str, Any]]:
        """Get a simulation by ID."""
        if supabase_available():
            rows = supabase_select("red_team_simulations", filters={"simulation_id": simulation_id}, limit=1)
            if rows:
                r = rows[0]
                return {
                    "simulation_id": r.get("simulation_id"),
                    "simulation_type": r.get("simulation_type"),
                    "status": r.get("status"),
                    "target": r.get("target"),
                    "options": r.get("options") or {},
                    "description": r.get("description"),
                    "started_at": r.get("started_at"),
                    "completed_at": r.get("completed_at"),
                    "findings": r.get("findings") or [],
                    "metrics": r.get("metrics") or {},
                    "recommendations": r.get("recommendations") or [],
                    "soc_incident_id": r.get("soc_incident_id"),
                    "error": r.get("error"),
                }
        return _memory_simulations.get(simulation_id)

    def list_all(
        self,
        status: Optional[str] = None,
        simulation_type: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """List simulations with optional filters. Ordered by started_at desc."""
        if supabase_available():
            rows = supabase_select(
                "red_team_simulations",
                order="started_at.desc",
                limit=limit,
            )
            results = []
            for r in rows:
                s = {
                    "simulation_id": r.get("simulation_id"),
                    "simulation_type": r.get("simulation_type"),
                    "status": r.get("status"),
                    "target": r.get("target"),
                    "options": r.get("options") or {},
                    "description": r.get("description"),
                    "started_at": r.get("started_at"),
                    "completed_at": r.get("completed_at"),
                    "findings": r.get("findings") or [],
                    "metrics": r.get("metrics") or {},
                    "recommendations": r.get("recommendations") or [],
                    "soc_incident_id": r.get("soc_incident_id"),
                    "error": r.get("error"),
                }
                if status and s.get("status") != status:
                    continue
                if simulation_type and s.get("simulation_type") != simulation_type:
                    continue
                results.append(s)
            return results[:limit]
        results = list(_memory_simulations.values())
        if status:
            results = [s for s in results if s.get("status") == status]
        if simulation_type:
            results = [s for s in results if s.get("simulation_type") == simulation_type]
        results.sort(key=lambda x: x.get("started_at", ""), reverse=True)
        return results[:limit]

    def update_status(
        self,
        simulation_id: str,
        status: str,
        completed_at: Optional[str] = None,
        findings: Optional[List[Dict[str, Any]]] = None,
        metrics: Optional[Dict[str, Any]] = None,
        recommendations: Optional[List[str]] = None,
        error: Optional[str] = None,
    ) -> None:
        """Update simulation status and related fields."""
        sim = self.get(simulation_id)
        if not sim:
            return
        sim["status"] = status
        if completed_at:
            sim["completed_at"] = completed_at
        if findings is not None:
            sim["findings"] = findings
        if metrics is not None:
            sim["metrics"] = metrics
        if recommendations is not None:
            sim["recommendations"] = recommendations
        if error is not None:
            sim["error"] = error
        self.save(sim)


redteam_store = RedTeamStore()
