"""FlyBrain agent — the FlyWire whole-brain LIF module as a MAS agent (spec §3, §10).

``FlyBrainAgent`` (agent_id ``flybrain``) exposes the runtime, the YOLO26+SAHI
detector, the A* navigator, the ITDX channel provider and the NLM coupling
through ``process_task``:

============================  ==================================================
type                          what it does
============================  ==================================================
``status``                    health + sessions (status ``unavailable`` without a connectome)
``create_session``            ``SessionConfig`` (``config`` or top-level keys) → ``SessionInfo``
``tick``                      one tick of ``session_id`` with a ``TickRequest``
``detect``                    YOLO26+SAHI on ``image_path`` / ``image_b64`` / remote ``snapshot``
``navigate``                  A* over ``start``/``goal`` (+ obstacles) or a session's last path
``assess_situation``          ITDX channel rows for ``map_slice`` (session-backed or one-off)
``couple_nlm``                ``formspace.observation/v1`` envelope of a session's rates
``stop_session``              delete ``session_id`` (cancels its autopilot)
============================  ==================================================

Every failure is returned, never raised, as
``{"status": "error", "message": ..., "unavailable": bool}`` where
``unavailable=True`` marks a missing connectome / detector / backend (spec §11:
unavailable means unavailable — no toy fallback, no synthetic detections).
Everything the agent returns is ``origin="SIMULATED"``.
"""

from __future__ import annotations

import asyncio
import base64
import binascii
import logging
from typing import Any, Dict, List, Mapping, Optional

from mycosoft_mas.agents.base_agent import BaseAgent
from mycosoft_mas.agents.enums import AgentStatus

logger = logging.getLogger(__name__)

AGENT_ID = "flybrain"
CAPABILITIES = {
    "flybrain_simulate",
    "flybrain_navigate",
    "flybrain_detect",
    "flybrain_classify",
    "flybrain_nlm_couple",
    "flybrain_itdx_channels",
}
TASK_TYPES = (
    "status",
    "create_session",
    "tick",
    "detect",
    "navigate",
    "assess_situation",
    "couple_nlm",
    "stop_session",
)
IMAGE_MAX_BYTES = 8 * 1024 * 1024


def _unavailable_types() -> tuple:
    from mycosoft_mas.flybrain.model import BackendUnavailable
    from mycosoft_mas.flybrain.runtime import ConnectomeUnavailable
    from mycosoft_mas.flybrain.vision.detector import DetectorUnavailable

    return (ConnectomeUnavailable, BackendUnavailable, DetectorUnavailable)


def _error(message: str, *, unavailable: bool = False, **extra: Any) -> Dict[str, Any]:
    out: Dict[str, Any] = {
        "status": "error",
        "message": str(message),
        "unavailable": bool(unavailable),
        "origin": "SIMULATED",
    }
    out.update(extra)
    return out


def _error_from(exc: BaseException, **extra: Any) -> Dict[str, Any]:
    unavailable = isinstance(exc, _unavailable_types())
    return _error(
        f"{type(exc).__name__}: {exc}",
        unavailable=unavailable,
        error_type=type(exc).__name__,
        **extra,
    )


def _dump(model: Any) -> Any:
    return model.model_dump(mode="json") if hasattr(model, "model_dump") else model


def _geo(raw: Any) -> Optional[Any]:
    from mycosoft_mas.flybrain.schemas import GeoPoint

    if isinstance(raw, GeoPoint):
        return raw
    if isinstance(raw, Mapping):
        lat = raw.get("lat", raw.get("latitude"))
        lon = raw.get("lon", raw.get("lng", raw.get("longitude")))
        try:
            if lat is not None and lon is not None:
                return GeoPoint(lat=float(lat), lon=float(lon))
        except (TypeError, ValueError):
            return None
    if isinstance(raw, (list, tuple)) and len(raw) >= 2:
        try:
            return GeoPoint(lat=float(raw[0]), lon=float(raw[1]))
        except (TypeError, ValueError):
            return None
    return None


class FlyBrainAgent(BaseAgent):
    """FlyWire whole-brain LIF simulation, vision, navigation and coupling agent."""

    def __init__(
        self,
        agent_id: str = AGENT_ID,
        name: str = "FlyBrain Agent",
        config: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(agent_id=agent_id, name=name, config=config or {})
        self.capabilities.update(CAPABILITIES)
        self._runtime: Any = None
        self._proc: Any = None  # psutil.Process handle, kept so cpu_percent() deltas are real

    # -- BaseAgent service hooks (same shape as CultureVisionAgent) ------------

    def _get_runtime(self) -> Any:
        if self._runtime is None:
            from mycosoft_mas.flybrain.runtime import get_runtime

            self._runtime = get_runtime()
        return self._runtime

    async def _initialize_services(self) -> None:
        self.status = AgentStatus.ACTIVE

    async def _check_services_health(self) -> Dict[str, Any]:
        try:
            health = await asyncio.to_thread(self._get_runtime().health)
        except Exception as exc:  # noqa: BLE001
            return {"status": "error", "message": f"{type(exc).__name__}: {exc}"}
        return {
            "status": health.status,
            "connectome_loaded": health.connectome.loaded,
            "vision_available": health.vision.available,
            "backend": health.backend,
            "sessions": health.sessions,
            "autopilots": health.autopilots,
            "origin": "SIMULATED",
        }

    async def _check_resource_usage(self) -> Dict[str, Any]:
        """Process-level CPU/RSS via psutil plus the engines' estimated footprint.

        ``BaseAgent.health_check()`` publishes this verbatim, so nothing here is invented:
        without psutil ``cpu``/``memory`` are ``None`` with ``note="not measured"``; the
        first psutil sample only primes ``cpu_percent()`` (psutil documents that reading
        as meaningless) so ``cpu`` is ``None`` until the second call.
        """
        sessions = 0
        neurons = 0
        synapses = 0
        try:
            infos = self._get_runtime().list_sessions()
            sessions = len(infos)
            neurons = sum(int(i.n_neurons) for i in infos)
            synapses = sum(int(i.n_synapses) for i in infos)
        except Exception:  # noqa: BLE001
            pass
        out: Dict[str, Any] = {
            "cpu": None,
            "memory": None,
            "cpu_unit": "percent",
            "memory_unit": "bytes_rss",
            "sessions": sessions,
            "neurons_simulated": neurons,
            "synapses_simulated": synapses,
            # ~8 bytes per synapse (float32 weight + int32 index in the CSC matrices)
            "estimated_engine_bytes": synapses * 8,
        }
        try:
            import psutil
        except Exception:  # noqa: BLE001 - psutil missing: say so instead of reporting 0
            out["note"] = "not measured (psutil unavailable)"
            return out
        try:
            primed = self._proc is not None
            if not primed:
                self._proc = psutil.Process()
            out["memory"] = int(self._proc.memory_info().rss)
            cpu = float(self._proc.cpu_percent(interval=None))
            if primed:
                out["cpu"] = cpu
            else:
                out["note"] = "cpu not measured yet (first sample primes psutil; call again)"
        except Exception as exc:  # noqa: BLE001
            out["note"] = f"not measured ({type(exc).__name__}: {exc})"
        return out

    async def _handle_error_type(self, error_type: str, error: str) -> Dict[str, Any]:
        return {"status": "error", "type": error_type, "message": error}

    async def _handle_notification(self, notification: Any) -> Dict[str, Any]:
        return {"status": "received", "notification": notification}

    # -- task dispatch ----------------------------------------------------------

    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        task_type = str((task or {}).get("type") or "").strip()
        handlers = {
            "status": self._task_status,
            "create_session": self._task_create_session,
            "tick": self._task_tick,
            "detect": self._task_detect,
            "navigate": self._task_navigate,
            "assess_situation": self._task_assess_situation,
            "couple_nlm": self._task_couple_nlm,
            "stop_session": self._task_stop_session,
        }
        handler = handlers.get(task_type)
        if handler is None:
            return _error(
                f"Unknown task type: {task_type!r}; known: {', '.join(TASK_TYPES)}",
                task_type=task_type,
            )
        try:
            result = await handler(task or {})
        except Exception as exc:  # noqa: BLE001 - never raise out of process_task
            logger.warning("FlyBrainAgent %s failed: %s", task_type, exc)
            result = _error_from(exc, task_type=task_type)
        self.metrics["tasks_processed"] = int(self.metrics.get("tasks_processed", 0)) + 1
        return result

    # -- status ---------------------------------------------------------------------

    async def _task_status(self, task: Dict[str, Any]) -> Dict[str, Any]:
        runtime = self._get_runtime()
        health = await asyncio.to_thread(runtime.health)
        sessions = [_dump(info) for info in runtime.list_sessions()]
        session_id = task.get("session_id")
        session: Optional[Dict[str, Any]] = None
        if session_id:
            session = _dump(runtime.get_session(str(session_id)))
        return {
            "status": "unavailable" if health.status == "unavailable" else "success",
            "agent_id": self.agent_id,
            "origin": "SIMULATED",
            "health": _dump(health),
            "flybrain_status": health.status,
            "sessions": sessions,
            "session": session,
            "capabilities": sorted(self.capabilities),
            "task_types": list(TASK_TYPES),
            "fetch": (
                f"poetry run python scripts/flybrain_fetch_connectome.py "
                f"--dest {runtime.settings.data_dir}"
                if not health.connectome.loaded
                else None
            ),
        }

    # -- sessions -----------------------------------------------------------------

    async def _task_create_session(self, task: Dict[str, Any]) -> Dict[str, Any]:
        from mycosoft_mas.flybrain.schemas import SessionConfig

        raw = task.get("config")
        if not isinstance(raw, Mapping):
            raw = {k: v for k, v in task.items() if k in SessionConfig.model_fields}
        try:
            cfg = SessionConfig.model_validate(dict(raw))
        except Exception as exc:  # noqa: BLE001
            return _error(f"invalid SessionConfig: {str(exc)[:400]}", task_type="create_session")
        info = await self._get_runtime().acreate_session(cfg)
        return {"status": "success", "origin": "SIMULATED", "session": _dump(info)}

    async def _task_stop_session(self, task: Dict[str, Any]) -> Dict[str, Any]:
        session_id = task.get("session_id")
        if not session_id:
            return _error("session_id is required", task_type="stop_session")
        info = await self._get_runtime().delete_session(str(session_id))
        return {"status": "success", "origin": "SIMULATED", "session": _dump(info)}

    async def _task_tick(self, task: Dict[str, Any]) -> Dict[str, Any]:
        from mycosoft_mas.flybrain.schemas import TickRequest

        session_id = task.get("session_id")
        if not session_id:
            return _error("session_id is required", task_type="tick")
        raw = task.get("request")
        if not isinstance(raw, Mapping):
            raw = {k: v for k, v in task.items() if k in TickRequest.model_fields}
        try:
            req = TickRequest.model_validate(dict(raw))
        except Exception as exc:  # noqa: BLE001
            return _error(f"invalid TickRequest: {str(exc)[:400]}", task_type="tick")
        result = await self._get_runtime().tick(str(session_id), req)
        return {"status": "success", "origin": "SIMULATED", "result": _dump(result)}

    # -- vision -------------------------------------------------------------------

    async def _task_detect(self, task: Dict[str, Any]) -> Dict[str, Any]:
        runtime = self._get_runtime()
        detector = runtime._detector()
        health = await asyncio.to_thread(detector.health)
        if not health.available:
            return _error(
                f"detector unavailable: {health.reason or 'no detector backend'}",
                unavailable=True,
                task_type="detect",
                vision=_dump(health),
            )
        pose = task.get("pose") if isinstance(task.get("pose"), Mapping) else None
        sahi = task.get("sahi")
        conf = task.get("conf")
        source = str(task.get("source") or "image")
        if task.get("snapshot"):
            frame = await detector.asnapshot(task.get("camera_source"), pose=pose)
        else:
            image: Any = task.get("image_path") or task.get("frame_ref")
            if not image and task.get("image_b64"):
                text = str(task["image_b64"]).strip()
                if text.startswith("data:") and "," in text:
                    text = text.split(",", 1)[1]
                try:
                    image = base64.b64decode(text, validate=True)
                except (binascii.Error, ValueError) as exc:
                    return _error(f"image_b64 invalid: {exc}", task_type="detect")
                if len(image) > IMAGE_MAX_BYTES:
                    return _error(f"image exceeds {IMAGE_MAX_BYTES} bytes", task_type="detect")
            if not image:
                return _error(
                    "image_path, frame_ref, image_b64 or snapshot=true is required",
                    task_type="detect",
                )
            frame = await detector.adetect(
                image,
                sahi=None if sahi is None else bool(sahi),
                conf=None if conf is None else float(conf),
                pose=dict(pose) if pose else None,
                source=source,
            )
        if not frame.available:
            return _error(
                f"detector reported unavailable: {frame.note or 'no reason'}",
                unavailable=True,
                task_type="detect",
                frame=_dump(frame),
            )
        return {
            "status": "success",
            "origin": "SIMULATED",
            "frame": _dump(frame),
            "n_detections": len(frame.detections),
        }

    # -- navigation ---------------------------------------------------------------

    async def _task_navigate(self, task: Dict[str, Any]) -> Dict[str, Any]:
        runtime = self._get_runtime()
        session_id = task.get("session_id")
        if session_id and task.get("goal") is None:
            session = runtime._session(str(session_id))
            nav = session.last_nav
            if nav is None:
                return _error(
                    "session has no navigation path yet (tick a navigating plug first)",
                    task_type="navigate",
                    session_id=str(session_id),
                )
            return {
                "status": "success",
                "origin": "SIMULATED",
                "session_id": str(session_id),
                "nav": _dump(nav),
                "feasible": bool(nav.feasible),
            }
        start = _geo(task.get("start"))
        goal = _geo(task.get("goal"))
        if start is None or goal is None:
            return _error(
                "start {lat, lon} and goal {lat, lon} are required (or session_id alone)",
                task_type="navigate",
            )
        turn_bias = 0.0
        turn_source = "none (no brain state supplied)"
        if session_id:
            session = runtime._session(str(session_id))
            if session.last_tick is not None:
                turn_bias = float(session.last_tick.action.turn)
                turn_source = f"session {session_id} tick {session.last_tick.tick}"
        elif task.get("turn_bias") is not None:
            try:
                turn_bias = max(-1.0, min(1.0, float(task["turn_bias"])))
                turn_source = "task.turn_bias"
            except (TypeError, ValueError):
                return _error("turn_bias must be a number in [-1, 1]", task_type="navigate")
        nav = await asyncio.to_thread(
            self._plan,
            start,
            goal,
            turn_bias,
            task.get("obstacles") or [],
            task.get("detections"),
            task.get("grid_size_m"),
            task.get("cell_m"),
        )
        nav.note = (
            f"{nav.note}; turn_bias from {turn_source}"
            if nav.note
            else (f"turn_bias from {turn_source}")
        )
        return {
            "status": "success",
            "origin": "SIMULATED",
            "session_id": str(session_id) if session_id else None,
            "nav": _dump(nav),
            "feasible": bool(nav.feasible),
        }

    @staticmethod
    def _plan(
        start: Any,
        goal: Any,
        turn_bias: float,
        obstacles: List[Any],
        detections: Any,
        grid_size_m: Any,
        cell_m: Any,
    ) -> Any:
        import math

        from mycosoft_mas.flybrain.navigation import OccupancyGrid, enu_from_geo, plan
        from mycosoft_mas.flybrain.schemas import DetectionFrame, GeoPoint

        east, north = enu_from_geo(goal.lat, goal.lon, start)
        distance = math.hypot(east, north)
        try:
            size = float(grid_size_m) if grid_size_m else 0.0
        except (TypeError, ValueError):
            size = 0.0
        try:
            cell = float(cell_m) if cell_m else 5.0
        except (TypeError, ValueError):
            cell = 5.0
        cell = max(cell, 1.0)
        size = max(size, 2.2 * distance + 4 * cell, 20.0 * cell)
        centre = GeoPoint(lat=(start.lat + goal.lat) / 2.0, lon=(start.lon + goal.lon) / 2.0)
        grid = OccupancyGrid(centre, size_m=size, cell_m=cell)
        for obstacle in obstacles or []:
            if isinstance(obstacle, Mapping) and obstacle.get("perimeter"):
                grid.add_perimeter(obstacle["perimeter"])
                continue
            pt = _geo(obstacle)
            if pt is None:
                continue
            radius = 0.0
            if isinstance(obstacle, Mapping):
                try:
                    radius = float(obstacle.get("radius_m") or 0.0)
                except (TypeError, ValueError):
                    radius = 0.0
            grid.add_point(pt.lat, pt.lon, radius)
        if detections is not None:
            try:
                frame = (
                    detections
                    if isinstance(detections, DetectionFrame)
                    else DetectionFrame.model_validate(detections)
                )
            except Exception:  # noqa: BLE001
                frame = None
            if frame is not None and frame.available:
                for det in frame.detections:
                    if det.perimeter:
                        grid.add_perimeter(det.perimeter)
                    elif det.location is not None:
                        grid.add_point(det.location.lat, det.location.lon, 5.0)
        return plan(grid, start, goal, turn_bias=turn_bias)

    # -- ITDX / NLM -----------------------------------------------------------------

    async def _task_assess_situation(self, task: Dict[str, Any]) -> Dict[str, Any]:
        from mycosoft_mas.core.routers.flybrain_api import plan_one_off
        from mycosoft_mas.flybrain.plugs.itdx import ITDX_CHANNELS_SCHEMA_VERSION, itdx_channel_rows
        from mycosoft_mas.flybrain.schemas import DetectionFrame, utc_now_iso

        runtime = self._get_runtime()
        map_slice = task.get("map_slice")
        if not isinstance(map_slice, Mapping):
            return _error(
                "map_slice {ao: {bbox|center}, ...} is required", task_type="assess_situation"
            )
        frame: Optional[DetectionFrame] = None
        if task.get("detections") is not None:
            try:
                frame = DetectionFrame.model_validate(task["detections"])
            except Exception as exc:  # noqa: BLE001
                return _error(
                    f"detections is not a DetectionFrame: {str(exc)[:300]}",
                    task_type="assess_situation",
                )
        session_id = task.get("session_id")
        if session_id:
            payload = runtime.itdx_channels(
                dict(map_slice), session_id=str(session_id), detections=frame
            )
        else:
            nav = await asyncio.to_thread(plan_one_off, dict(map_slice), frame)
            payload = {
                "schema_version": ITDX_CHANNELS_SCHEMA_VERSION,
                "origin": "SIMULATED",
                "channels": itdx_channel_rows(map_slice, None, None, nav, frame),
                "nav": _dump(nav),
                "session_id": None,
                "tick": None,
                "generated_at": utc_now_iso(),
                "note": "one-off: no session, no brain state; brain-derived fields are NOT_SUPPLIED",
            }
        payload["status"] = "success"
        return payload

    async def _task_couple_nlm(self, task: Dict[str, Any]) -> Dict[str, Any]:
        session_id = task.get("session_id")
        if not session_id:
            return _error("session_id is required", task_type="couple_nlm")
        payload = await self._get_runtime().nlm_observation(str(session_id), task.get("cutoff"))
        payload["status"] = "success"
        payload["emits_probability"] = False
        return payload

    async def process(self) -> None:
        await asyncio.sleep(0.1)


__all__ = ["AGENT_ID", "CAPABILITIES", "FlyBrainAgent", "TASK_TYPES"]
