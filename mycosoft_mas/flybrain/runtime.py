"""FlyBrain runtime (spec §10): sessions, tick loop, autopilot, JSONL recorder.

One process-wide :class:`FlyBrainRuntime` (``get_runtime()``) owns:

* the lazily loaded :class:`Connectome` (via ``connectome.get_connectome``;
  a missing FlyWire release raises :class:`ConnectomeUnavailable`, which the
  router maps to **503** with fetch instructions — no toy fallback);
* one :class:`FlyBrainEngine` + :class:`Atlas` + plug per session, guarded
  by a per-session ``asyncio.Lock`` (the engine is not thread-safe);
* the tick pipeline ``plug.observe() + request observations → encode →
  drive → engine.run() (in a worker thread) → BrainState → LocomotionDecoder
  → NavPath (navigating plugs) → plug.act()`` with a JSONL record under
  ``FLYBRAIN_RECORD_DIR/<session_id>/ticks.jsonl``;
* autopilot tasks that loop ``tick()`` at ``period_s`` (>= 0.2 s) and stop
  on error or session delete;
* ``health()`` / ``atlas_summary()`` that never force a connectome load.

Everything reported is ``origin="SIMULATED"``. numpy is imported inside
the functions that need it so this module is safe under ``MAS_LIGHT_IMPORT=1``.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Sequence, Tuple

from mycosoft_mas.flybrain import connectome as connectome_mod
from mycosoft_mas.flybrain.atlas import Atlas
from mycosoft_mas.flybrain.config import FlyBrainSettings, get_settings
from mycosoft_mas.flybrain.connectome import (
    Connectome,
    ConnectomeUnavailable,
    connectome_available,
    get_connectome,
    unavailable_manifest,
)
from mycosoft_mas.flybrain.decoders import LocomotionDecoder, PopulationClassifier
from mycosoft_mas.flybrain.encoders import encode
from mycosoft_mas.flybrain.model import (
    BackendUnavailable,
    FlyBrainEngine,
    cuda_available,
    resolve_backend,
    torch_available,
)
from mycosoft_mas.flybrain.plugs import PLUG_REGISTRY, FlyBrainPlug, PlugContext, get_plug
from mycosoft_mas.flybrain.plugs.itdx import ITDX_CHANNELS_SCHEMA_VERSION, itdx_channel_rows
from mycosoft_mas.flybrain.plugs.nlm import build_envelope
from mycosoft_mas.flybrain.schemas import (
    ORIGIN_SIMULATED,
    SCHEMA_VERSION,
    AtlasSummary,
    BrainState,
    ConnectomeManifest,
    DetectionFrame,
    FlyBrainHealth,
    MotorAction,
    NavPath,
    Observation,
    SessionConfig,
    SessionInfo,
    SpikeRecord,
    StimulusCommand,
    TickRequest,
    TickResult,
    VisionHealth,
    utc_now_iso,
)

if TYPE_CHECKING:  # pragma: no cover - typing only
    import numpy as np

logger = logging.getLogger(__name__)

RECORD_FILE = "ticks.jsonl"
MAX_SPIKE_RECORD = 200_000
# Per-session JSONL recorder caps (``FLYBRAIN_RECORD_MAX_BYTES`` / ``_MAX_TICKS``,
# 0 disables the cap). Autopilot can tick every 0.2 s indefinitely, so recording
# stops — and says so in ``SessionInfo.plug["recording"]`` and the tick notes —
# instead of filling the container's writable layer or the NAS.
DEFAULT_RECORD_MAX_BYTES = 64 * 1024 * 1024
DEFAULT_RECORD_MAX_TICKS = 20_000


def _env_int(name: str, default: int) -> int:
    raw = (os.getenv(name) or "").strip()
    if not raw:
        return default
    try:
        return max(0, int(raw))
    except ValueError:
        return default


def record_caps() -> Tuple[int, int]:
    """``(max_bytes, max_ticks)`` for the JSONL recorder; ``0`` means uncapped."""
    return (
        _env_int("FLYBRAIN_RECORD_MAX_BYTES", DEFAULT_RECORD_MAX_BYTES),
        _env_int("FLYBRAIN_RECORD_MAX_TICKS", DEFAULT_RECORD_MAX_TICKS),
    )


def _ao_of(map_slice: Any) -> Optional[Dict[str, Any]]:
    ao = map_slice.get("ao") if isinstance(map_slice, dict) else None
    return ao if isinstance(ao, dict) else None


def _num_list(value: Any) -> Optional[List[float]]:
    if isinstance(value, dict):
        try:
            return [float(value["lat"]), float(value["lon"])]
        except (KeyError, TypeError, ValueError):
            return None
    if isinstance(value, (list, tuple)):
        try:
            return [float(v) for v in value]
        except (TypeError, ValueError):
            return None
    return None


def _ao_differs(requested: Any, planned: Any, tol: float = 1e-6) -> bool:
    """True when the request's AO (name / center / bbox) names a different area
    than the slice the session actually planned on. Fields absent on either side
    are not compared; a request without an ``ao`` never mismatches."""
    req = _ao_of(requested)
    got = _ao_of(planned)
    if not req or not got:
        return False
    req_name = str(req.get("name") or req.get("place") or "").strip().lower()
    got_name = str(got.get("name") or got.get("place") or "").strip().lower()
    if req_name and got_name and req_name != got_name:
        return True
    for key in ("center", "bbox"):
        a, b = _num_list(req.get(key)), _num_list(got.get(key))
        if a is None or b is None:
            continue
        if len(a) != len(b) or any(abs(x - y) > tol for x, y in zip(a, b)):
            return True
    return False


class SessionNotFound(KeyError):
    """Unknown session id (router → 404)."""


class SessionLimitReached(RuntimeError):
    """``FLYBRAIN_MAX_SESSIONS`` reached (router → 429)."""


@dataclass
class Session:
    info: SessionInfo
    engine: FlyBrainEngine
    atlas: Atlas
    plug: FlyBrainPlug
    decoder: LocomotionDecoder
    classifier: PopulationClassifier = field(default_factory=PopulationClassifier)
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    group_local: Dict[str, Any] = field(default_factory=dict)  # group → np.ndarray local idx
    group_outside: Dict[str, int] = field(default_factory=dict)  # group → n outside subgraph
    manual_rates: Dict[int, float] = field(default_factory=dict)  # local idx → Hz (stimulate)
    manual_labels: Dict[str, float] = field(default_factory=dict)  # label → Hz (for BrainState)
    silenced_labels: List[str] = field(default_factory=list)
    encoded_rates: Dict[str, float] = field(default_factory=dict)
    last_tick: Optional[TickResult] = None
    last_nav: Optional[NavPath] = None
    last_detections: Optional[DetectionFrame] = None
    autopilot_task: Optional["asyncio.Task[None]"] = None
    autopilot_period_s: float = 1.0
    record_path: Optional[Path] = None
    record_bytes: int = 0
    record_ticks: int = 0
    record_stopped_reason: Optional[str] = None

    @property
    def id(self) -> str:
        return self.info.session_id

    @property
    def config(self) -> SessionConfig:
        return self.info.config


class FlyBrainRuntime:
    """Session manager for the FlyBrain engine (spec §10)."""

    def __init__(self, settings: Optional[FlyBrainSettings] = None) -> None:
        self.settings: FlyBrainSettings = settings or get_settings()
        self._sessions: Dict[str, Session] = {}
        self._atlas_cache: Dict[int, Atlas] = {}
        self._lock = threading.RLock()
        self._pending_sessions = 0  # slots reserved by create_session() calls in flight

    # ------------------------------------------------------------------
    # Connectome / atlas access
    # ------------------------------------------------------------------

    def cached_connectome(self) -> Optional[Connectome]:
        """The process-wide connectome if it is already loaded (never loads)."""
        return getattr(connectome_mod, "_CACHED", None)

    def connectome(self) -> Connectome:
        """Load (once) or return the cached connectome; raises ``ConnectomeUnavailable``."""
        return get_connectome(self.settings)

    def atlas_for(self, connectome: Optional[Connectome]) -> Atlas:
        key = id(connectome) if connectome is not None else 0
        with self._lock:
            atlas = self._atlas_cache.get(key)
            if atlas is None:
                atlas = Atlas.load(self.settings.atlas_path, connectome=connectome)
                self._atlas_cache[key] = atlas
            return atlas

    def connectome_manifest(self) -> ConnectomeManifest:
        """Manifest without forcing a load: loaded → real manifest; on disk but not
        loaded → ``loaded=False`` with the lazy-load reason; absent → fetch instructions."""
        cached = self.cached_connectome()
        if cached is not None:
            try:
                return cached.manifest(verify=True)
            except Exception as exc:  # noqa: BLE001
                return unavailable_manifest(f"manifest failed: {exc}", cached.data_dir)
        ok, reason = connectome_available(self.settings)
        data_dir = Path(self.settings.data_dir)
        if not ok:
            return unavailable_manifest(reason, data_dir)
        npz = self.settings.connectivity_npz_path
        parquet = self.settings.connectivity_parquet_path
        return ConnectomeManifest(
            loaded=False,
            data_dir=str(data_dir),
            completeness_path=str(self.settings.completeness_path),
            connectivity_path=str(npz if npz.is_file() else parquet),
            reason="FlyWire files present on disk; loaded lazily on the first session",
        )

    # ------------------------------------------------------------------
    # Sessions
    # ------------------------------------------------------------------

    def list_sessions(self) -> List[SessionInfo]:
        with self._lock:
            return [self._sync_info(s) for s in self._sessions.values()]

    def get_session(self, session_id: str) -> SessionInfo:
        return self._sync_info(self._session(session_id))

    def _session(self, session_id: str) -> Session:
        session = self._sessions.get(session_id)
        if session is None:
            raise SessionNotFound(session_id)
        return session

    def _sync_info(self, session: Session) -> SessionInfo:
        info = session.info
        info.t_ms = float(session.engine.t_ms)
        info.autopilot = session.autopilot_task is not None and not session.autopilot_task.done()
        return info

    def create_session(self, cfg: SessionConfig) -> SessionInfo:
        """Build engine + atlas + plug. Raises ``ConnectomeUnavailable`` (→ 503),
        ``BackendUnavailable`` (→ 503), ``SessionLimitReached`` (→ 429)."""
        cap = max(1, int(self.settings.max_sessions))
        # Reserve the slot atomically: the engine build below takes seconds and
        # ~130 MB per full-brain session, so the cap must count creates in flight.
        with self._lock:
            if len(self._sessions) + self._pending_sessions >= cap:
                raise SessionLimitReached(
                    f"FLYBRAIN_MAX_SESSIONS={self.settings.max_sessions} reached; delete a session first"
                )
            self._pending_sessions += 1
        try:
            session = self._build_session(cfg)
            with self._lock:
                self._sessions[session.id] = session
        finally:
            with self._lock:
                self._pending_sessions -= 1
        info = session.info
        engine = session.engine
        logger.info(
            "FlyBrain session %s: plug=%s backend=%s neurons=%d synapses=%d",
            info.session_id,
            cfg.plug,
            engine.backend,
            engine.n_neurons,
            engine.n_synapses,
        )
        return info

    def _build_session(self, cfg: SessionConfig) -> Session:
        connectome = self.connectome()  # ConnectomeUnavailable propagates
        atlas = self.atlas_for(connectome)
        backend = cfg.backend if cfg.backend != "auto" else (self.settings.backend or "auto")
        engine = FlyBrainEngine(
            connectome,
            dt_ms=cfg.dt_ms,
            seed=cfg.seed,
            backend=backend,
            subgraph=cfg.subgraph,
            atlas=atlas,
            torch_threads=self.settings.torch_threads,
        )
        plug = get_plug(cfg.plug, cfg, self.settings)
        decoder = LocomotionDecoder(atlas.sensorimotor)
        info = SessionInfo(
            config=cfg,
            status="ready",
            backend=engine.backend,
            n_neurons=engine.n_neurons,
            n_synapses=engine.n_synapses,
            subgraph=dict(engine.subgraph_info) if engine.subgraph_info else None,
            plug=plug.describe(),
        )
        session = Session(info=info, engine=engine, atlas=atlas, plug=plug, decoder=decoder)
        self._index_groups(session)
        if cfg.record:
            session.record_path = Path(self.settings.record_dir) / info.session_id / RECORD_FILE
            info.plug["recording"] = self._recording_status(session)
        return session

    def pending_sessions(self) -> int:
        """Creates in flight that hold a reserved slot against ``FLYBRAIN_MAX_SESSIONS``."""
        with self._lock:
            return self._pending_sessions

    async def acreate_session(self, cfg: SessionConfig) -> SessionInfo:
        return await asyncio.to_thread(self.create_session, cfg)

    def _index_groups(self, session: Session) -> None:
        import numpy as np

        engine = session.engine
        for name, group in session.atlas.groups.items():
            if not group.indices:
                session.group_local[name] = np.empty(0, dtype=np.int64)
                continue
            global_idx = np.asarray(group.indices, dtype=np.int64)
            local = engine.to_local(global_idx)
            session.group_local[name] = np.asarray(local, dtype=np.int64)
            outside = int(global_idx.size - local.size)
            if outside:
                session.group_outside[name] = outside

    async def delete_session(self, session_id: str) -> SessionInfo:
        session = self._session(session_id)
        await self._stop_autopilot(session)
        try:
            await session.plug.close()
        except Exception as exc:  # noqa: BLE001
            logger.warning("FlyBrain plug close failed for %s: %s", session_id, exc)
        with self._lock:
            self._sessions.pop(session_id, None)
        session.info.status = "stopped"
        return self._sync_info(session)

    # ------------------------------------------------------------------
    # Drive helpers
    # ------------------------------------------------------------------

    def _resolve_command_indices(
        self, session: Session, cmd: StimulusCommand
    ) -> Tuple["np.ndarray", str, List[str]]:
        """Local engine indices for a stimulus command plus a label and notes."""
        import numpy as np

        notes: List[str] = []
        if cmd.group:
            if not session.atlas.has_group(cmd.group):
                raise ValueError(f"unknown atlas group {cmd.group!r}")
            local = session.group_local.get(cmd.group)
            local = local if local is not None else np.empty(0, dtype=np.int64)
            if local.size == 0:
                notes.append(f"group {cmd.group!r} resolves to no neurons in this engine")
            outside = session.group_outside.get(cmd.group)
            if outside:
                notes.append(f"group {cmd.group!r}: {outside} neurons outside the subgraph ignored")
            return local, cmd.group, notes
        if cmd.flywire_ids:
            found, missing = session.engine.connectome.indices_for_ids(cmd.flywire_ids)
            if missing:
                notes.append(f"{len(missing)} flywire ids not in the connectome: {missing[:5]}")
            global_idx = np.asarray(found, dtype=np.int64)
            local = session.engine.to_local(global_idx) if global_idx.size else global_idx
            outside = int(global_idx.size - local.size)
            if outside:
                notes.append(f"{outside} flywire ids outside the subgraph ignored")
            return np.asarray(local, dtype=np.int64), f"flywire_ids[{len(cmd.flywire_ids)}]", notes
        raise ValueError("StimulusCommand needs a group or flywire_ids")

    def _apply_stimuli(self, session: Session, stimuli: Sequence[StimulusCommand]) -> List[str]:
        engine = session.engine
        notes: List[str] = []
        for cmd in stimuli:
            local, label, cmd_notes = self._resolve_command_indices(session, cmd)
            notes.extend(cmd_notes)
            idx = local.tolist()
            if cmd.mode == "poisson":
                if cmd.rate_hz > 0 and idx:
                    for i in idx:
                        session.manual_rates[i] = float(cmd.rate_hz)
                    session.manual_labels[label] = float(cmd.rate_hz)
                    engine.set_rates(idx, float(cmd.rate_hz))
                else:
                    for i in idx:
                        session.manual_rates.pop(i, None)
                    session.manual_labels.pop(label, None)
                    if idx:
                        engine.clear_rates(idx)
            elif cmd.mode == "clear":
                for i in idx:
                    session.manual_rates.pop(i, None)
                session.manual_labels.pop(label, None)
                if idx:
                    engine.clear_rates(idx)
            elif cmd.mode == "silence":
                if idx:
                    engine.silence(idx)
                if label not in session.silenced_labels:
                    session.silenced_labels.append(label)
            elif cmd.mode == "unsilence":
                if idx:
                    engine.unsilence(idx)
                if label in session.silenced_labels:
                    session.silenced_labels.remove(label)
        return notes

    def _apply_encoded_drive(self, session: Session, rates: Dict[str, float]) -> List[str]:
        """Replace the previous tick's encoded drive: clear everything, re-apply the
        persistent manual stimuli, then the encoded group rates (max per neuron)."""
        import numpy as np

        engine = session.engine
        notes: List[str] = []
        engine.clear_rates(None)
        combined: Dict[int, float] = dict(session.manual_rates)
        for group, hz in rates.items():
            local = session.group_local.get(group)
            if local is None:
                notes.append(f"encoded group {group!r} is not in the atlas; ignored")
                continue
            if local.size == 0:
                notes.append(f"encoded group {group!r} has no neurons in this engine; no drive")
                continue
            outside = session.group_outside.get(group)
            if outside:
                notes.append(f"encoded group {group!r}: {outside} neurons outside the subgraph")
            for i in local.tolist():
                combined[i] = max(combined.get(i, 0.0), float(hz))
        if combined:
            idx = np.asarray(sorted(combined), dtype=np.int64)
            hz_arr = np.asarray([combined[int(i)] for i in idx], dtype=np.float64)
            engine.set_rates(idx, hz_arr)
        session.encoded_rates = dict(rates)
        return notes

    # ------------------------------------------------------------------
    # State
    # ------------------------------------------------------------------

    def _group_rates(self, session: Session, window_ms: float) -> Dict[str, float]:
        """Mean Hz per neuron for every atlas group with neurons in this engine
        (same estimator as ``FlyBrainEngine.mean_rates``)."""
        import numpy as np

        engine = session.engine
        _, idx = engine.spikes_in_window(window_ms)
        counts = np.bincount(idx, minlength=engine.n_neurons) if idx.size else None
        elapsed_s = min(float(window_ms), max(engine.t_ms, engine.dt_ms)) / 1000.0
        rates: Dict[str, float] = {}
        for name, local in session.group_local.items():
            if local.size == 0:
                continue
            if counts is None:
                rates[name] = 0.0
            else:
                rates[name] = float(counts[local].sum()) / float(local.size) / elapsed_s
        return rates

    def _brain_state(self, session: Session, window_ms: float) -> BrainState:
        engine = session.engine
        snap = engine.snapshot(window_ms)
        stimulated = dict(session.encoded_rates)
        for label, hz in session.manual_labels.items():
            stimulated[label] = max(stimulated.get(label, 0.0), hz)
        return BrainState(
            session_id=session.id,
            t_ms=float(engine.t_ms),
            step=int(engine.step_count),
            n_neurons=int(engine.n_neurons),
            n_active=int(snap["n_active"]),
            spike_count_window=int(snap["spike_count_window"]),
            window_ms=float(window_ms),
            rates_hz=self._group_rates(session, window_ms),
            stimulated_hz=stimulated,
            silenced=list(session.silenced_labels),
            backend=engine.backend,
            realtime_ratio=snap.get("realtime_ratio"),
            subgraph=snap.get("subgraph"),
        )

    async def state(self, session_id: str, window_ms: Optional[float] = None) -> BrainState:
        session = self._session(session_id)
        window = float(window_ms or session.config.window_ms)
        async with session.lock:
            return self._brain_state(session, window)

    async def stimulate(self, session_id: str, cmds: Sequence[StimulusCommand]) -> BrainState:
        session = self._session(session_id)
        async with session.lock:
            self._apply_stimuli(session, list(cmds))
            return self._brain_state(session, session.config.window_ms)

    async def spikes(self, session_id: str, limit: int = 10_000) -> SpikeRecord:
        session = self._session(session_id)
        limit = max(0, min(int(limit), MAX_SPIKE_RECORD))
        async with session.lock:
            engine = session.engine
            times, local = engine.recent_spikes(limit)
            global_idx = engine.to_global(local) if local.size else local
            ids = engine.connectome.ids_for_indices(global_idx) if global_idx.size else []
            total = engine.history.total
            return SpikeRecord(
                session_id=session.id,
                from_ms=float(times[0]) if times.size else float(engine.t_ms),
                to_ms=float(engine.t_ms),
                count=int(local.size),
                times_ms=[float(t) for t in times.tolist()],
                neuron_indices=[int(i) for i in global_idx.tolist()],
                flywire_ids=[int(i) for i in ids],
                truncated=bool(total > local.size or engine.history.dropped > 0),
            )

    async def reset(self, session_id: str) -> SessionInfo:
        session = self._session(session_id)
        async with session.lock:
            session.engine.reset(keep_stimuli=True, reseed=True)
            session.info.ticks = 0
            session.info.t_ms = 0.0
            session.info.error = None
            if session.info.status == "error":
                session.info.status = "ready"
            session.last_tick = None
            session.last_nav = None
            session.last_detections = None
            return self._sync_info(session)

    # ------------------------------------------------------------------
    # Tick
    # ------------------------------------------------------------------

    def _context(self, session: Session, tick: int) -> PlugContext:
        settings = self.settings
        return PlugContext(
            session_id=session.id,
            config=session.config,
            settings=settings,
            atlas=session.atlas,
            tick=tick,
            t_ms=float(session.engine.t_ms),
            engine_snapshot=session.engine.snapshot(session.config.window_ms),
            get_detector=lambda: self._detector(),
        )

    def _detector(self) -> Any:
        from mycosoft_mas.flybrain.vision.detector import get_detector

        return get_detector(self.settings)

    def _sensorimotor_for_encode(self, session: Session) -> Dict[str, Any]:
        mapping = dict(session.atlas.sensorimotor)
        mapping["all_groups"] = session.atlas.names()
        return mapping

    @staticmethod
    def _detection_frame(
        observations: Sequence[Observation],
    ) -> Tuple[Optional[DetectionFrame], List[str]]:
        notes: List[str] = []
        frame: Optional[DetectionFrame] = None
        for obs in observations:
            if obs.kind != "detections":
                continue
            try:
                frame = DetectionFrame.model_validate(obs.payload)
            except Exception as exc:  # noqa: BLE001
                notes.append(f"detections observation is not a DetectionFrame: {exc}")
        return frame, notes

    @staticmethod
    def _label_from(observations: Sequence[Observation]) -> Optional[str]:
        for obs in observations:
            label = obs.payload.get("label") if isinstance(obs.payload, dict) else None
            if isinstance(label, str) and label.strip():
                return label.strip()
        return None

    async def tick(self, session_id: str, req: Optional[TickRequest] = None) -> TickResult:
        session = self._session(session_id)
        req = req or TickRequest()
        async with session.lock:
            t0 = time.perf_counter()
            engine = session.engine
            plug = session.plug
            tick_no = session.info.ticks + 1
            window = float(req.window_ms or session.config.window_ms)
            ctx = self._context(session, tick_no)
            notes: List[str] = []
            session.info.status = "running"

            # 1. observe (plug first, then the request's observations)
            plug_obs: List[Observation] = []
            try:
                plug_obs = list(await plug.observe(ctx) or [])
            except Exception as exc:  # noqa: BLE001
                notes.append(f"plug.observe failed: {type(exc).__name__}: {exc}")
            notes.extend(ctx.notes)
            ctx.notes = []
            observations: List[Observation] = plug_obs + list(req.observations)

            # 2. encode → drive
            rates, enc_notes = encode(observations, self._sensorimotor_for_encode(session))
            notes.extend(enc_notes)
            notes.extend(self._apply_encoded_drive(session, rates))
            if req.stimuli:
                try:
                    notes.extend(self._apply_stimuli(session, req.stimuli))
                except ValueError as exc:
                    notes.append(f"stimuli: {exc}")
            ctx.encoded_rates_hz = dict(rates)

            # 3. simulate
            try:
                await asyncio.to_thread(engine.run, window, False)
            except Exception as exc:
                session.info.status = "error"
                session.info.error = f"{type(exc).__name__}: {exc}"
                raise
            brain = self._brain_state(session, window)
            ctx.brain = brain
            ctx.t_ms = brain.t_ms
            ctx.engine_snapshot = engine.snapshot(window)

            # 4. decode
            action: MotorAction = session.decoder.decode(brain.rates_hz, brain.spike_count_window)
            label = self._label_from(observations)
            session.classifier.observe(brain.rates_hz, label)
            prediction = session.classifier.predict(brain.rates_hz)
            if prediction is not None:
                action.evidence["population_class"] = prediction
            elif label is None and session.classifier.state()["n_labels"] == 0:
                action.evidence["population_class"] = None

            # 5. detections + navigation
            detections, det_notes = self._detection_frame(observations)
            notes.extend(det_notes)
            nav: Optional[NavPath] = None
            if plug.navigates:
                try:
                    nav = await plug.navigate(ctx, action, detections)
                except Exception as exc:  # noqa: BLE001
                    notes.append(f"plug.navigate failed: {type(exc).__name__}: {exc}")
                    nav = NavPath(feasible=False, note=f"navigate failed: {exc}")
            notes.extend(ctx.notes)
            ctx.notes = []

            # 6. act
            plug_result: Dict[str, Any] = {}
            avani: Optional[Dict[str, Any]] = None
            if req.act:
                try:
                    plug_result = dict(await plug.act(ctx, action, nav, detections) or {})
                except Exception as exc:  # noqa: BLE001
                    notes.append(f"plug.act failed: {type(exc).__name__}: {exc}")
                    plug_result = {"error": f"{type(exc).__name__}: {exc}", "actuated": False}
                raw_avani = plug_result.get("avani")
                avani = raw_avani if isinstance(raw_avani, dict) else None
            else:
                plug_result = {"skipped": "act=false", "actuated": False}
            notes.extend(ctx.notes)

            wall_ms = (time.perf_counter() - t0) * 1000.0
            result = TickResult(
                session_id=session.id,
                tick=tick_no,
                t_ms=brain.t_ms,
                brain=brain,
                action=action,
                nav=nav,
                detections=detections,
                plug=session.config.plug,
                dry_run=bool(session.config.dry_run),
                plug_result=plug_result,
                avani=avani,
                encoded_rates_hz=dict(rates),
                notes=notes,
                wall_ms=wall_ms,
            )
            session.info.ticks = tick_no
            session.info.t_ms = brain.t_ms
            session.info.status = "ready"
            session.last_tick = result
            session.last_nav = nav
            session.last_detections = detections
            if session.record_path is not None:
                stopped = self._record(session, result)
                if stopped:
                    result.notes.append(f"recording stopped: {stopped}")
            return result

    def _recording_status(self, session: Session) -> Dict[str, Any]:
        max_bytes, max_ticks = record_caps()
        return {
            "path": str(session.record_path) if session.record_path is not None else None,
            "active": session.record_path is not None and session.record_stopped_reason is None,
            "bytes": session.record_bytes,
            "ticks": session.record_ticks,
            "max_bytes": max_bytes,
            "max_ticks": max_ticks,
            "stopped_reason": session.record_stopped_reason,
        }

    def _record(self, session: Session, result: TickResult) -> Optional[str]:
        """Append one tick record; returns the stop reason when a cap was hit on
        this tick (recording is then off for the rest of the session)."""
        path = session.record_path
        if path is None or session.record_stopped_reason is not None:
            return None
        max_bytes, max_ticks = record_caps()
        line = json.dumps(result.model_dump(mode="json"), separators=(",", ":")) + "\n"
        size = len(line.encode("utf-8"))
        reason: Optional[str] = None
        if max_ticks and session.record_ticks >= max_ticks:
            reason = f"FLYBRAIN_RECORD_MAX_TICKS={max_ticks} reached"
        elif max_bytes and session.record_bytes + size > max_bytes:
            reason = f"FLYBRAIN_RECORD_MAX_BYTES={max_bytes} would be exceeded"
        if reason is None:
            try:
                path.parent.mkdir(parents=True, exist_ok=True)
                with open(path, "a", encoding="utf-8") as handle:
                    handle.write(line)
                session.record_bytes += size
                session.record_ticks += 1
            except Exception as exc:  # noqa: BLE001 - recording never fails a tick
                logger.warning("FlyBrain record write failed for %s: %s", session.id, exc)
        else:
            session.record_stopped_reason = reason
            logger.warning(
                "FlyBrain recording stopped for %s after %d ticks / %d bytes: %s",
                session.id,
                session.record_ticks,
                session.record_bytes,
                reason,
            )
        session.info.plug["recording"] = self._recording_status(session)
        return reason

    # ------------------------------------------------------------------
    # Autopilot
    # ------------------------------------------------------------------

    async def set_autopilot(
        self, session_id: str, enabled: bool, period_s: float = 1.0
    ) -> SessionInfo:
        session = self._session(session_id)
        if not enabled:
            await self._stop_autopilot(session)
            return self._sync_info(session)
        period = max(float(period_s or 0.0), float(self.settings.autopilot_min_period_s))
        session.autopilot_period_s = period  # the loop reads this every iteration
        if session.autopilot_task is not None and not session.autopilot_task.done():
            return self._sync_info(session)
        session.info.error = None
        session.autopilot_task = asyncio.create_task(
            self._autopilot_loop(session), name=f"flybrain-autopilot-{session.id}"
        )
        return self._sync_info(session)

    async def _stop_autopilot(self, session: Session) -> None:
        task = session.autopilot_task
        if task is None:
            return
        if not task.done():
            task.cancel()
            try:
                await task
            except (asyncio.CancelledError, Exception):  # noqa: BLE001
                pass
        session.autopilot_task = None
        session.info.autopilot = False

    async def _autopilot_loop(self, session: Session) -> None:
        session.info.autopilot = True
        try:
            while session.id in self._sessions:
                t0 = time.perf_counter()
                await self.tick(session.id, TickRequest())
                elapsed = time.perf_counter() - t0
                # Re-read each iteration so set_autopilot(enabled=True, period_s=...)
                # on a running loop takes effect without a restart.
                period_s = max(
                    float(session.autopilot_period_s), float(self.settings.autopilot_min_period_s)
                )
                await asyncio.sleep(max(0.0, period_s - elapsed))
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001
            logger.exception("FlyBrain autopilot for %s stopped on error", session.id)
            session.info.status = "error"
            session.info.error = f"autopilot stopped: {type(exc).__name__}: {exc}"
        finally:
            session.info.autopilot = False
            session.autopilot_task = None

    def autopilot_count(self) -> int:
        return sum(
            1
            for s in self._sessions.values()
            if s.autopilot_task is not None and not s.autopilot_task.done()
        )

    # ------------------------------------------------------------------
    # Health / atlas
    # ------------------------------------------------------------------

    def vision_health(self) -> VisionHealth:
        try:
            return self._detector().health()
        except Exception as exc:  # noqa: BLE001
            return VisionHealth(
                available=False, reason=f"detector probe failed: {type(exc).__name__}: {exc}"
            )

    def health(self) -> FlyBrainHealth:
        manifest = self.connectome_manifest()
        vision = self.vision_health()
        try:
            backend = resolve_backend(self.settings.backend)
        except BackendUnavailable as exc:
            backend = f"unavailable ({exc})"
        except ValueError as exc:
            backend = f"invalid ({exc})"
        on_disk = manifest.loaded or connectome_available(self.settings)[0]
        notes: List[str] = []
        if not on_disk:
            status = "unavailable"
            notes.append(manifest.reason or "no connectome on disk")
        else:
            status = "healthy" if vision.available else "degraded"
            if not manifest.loaded:
                notes.append(manifest.reason)
            if not vision.available:
                notes.append(f"vision unavailable: {vision.reason or 'no detector backend'}")
            if manifest.loaded and manifest.sha256_ok is False:
                status = "degraded"
                notes.append("connectome SHA-256 mismatch against KNOWN_SHA256")
        return FlyBrainHealth(
            status=status,  # type: ignore[arg-type]
            schema_version=SCHEMA_VERSION,
            connectome=manifest,
            vision=vision,
            backend=backend,
            torch_available=torch_available(),
            cuda_available=cuda_available(),
            sessions=len(self._sessions),
            autopilots=self.autopilot_count(),
            plugs=list(PLUG_REGISTRY.keys()),
            note="; ".join(n for n in notes if n)
            + (f" | origin={ORIGIN_SIMULATED}" if notes else f"origin={ORIGIN_SIMULATED}"),
        )

    def atlas_summary(self) -> AtlasSummary:
        """Atlas description against the cached connectome (never forces a load)."""
        return self.atlas_for(self.cached_connectome()).summary()

    # ------------------------------------------------------------------
    # Endpoint helpers (spec §10 table)
    # ------------------------------------------------------------------

    def itdx_channels(
        self,
        map_slice: Optional[Dict[str, Any]],
        session_id: Optional[str] = None,
        detections: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """``/itdx/channels`` payload from the session's last tick (or honest NOT_SUPPLIED)."""
        brain = action = nav = None
        frame: Optional[DetectionFrame] = None
        if detections is not None:
            try:
                frame = (
                    detections
                    if isinstance(detections, DetectionFrame)
                    else DetectionFrame.model_validate(detections)
                )
            except Exception:  # noqa: BLE001
                frame = None
        tick_no: Optional[int] = None
        label_slice = map_slice
        ao_source = "request map_slice"
        ao_mismatch: Optional[str] = None
        if session_id:
            session = self._session(session_id)
            plug_slice = getattr(session.plug, "map_slice", None)
            plug_slice = plug_slice if isinstance(plug_slice, dict) and plug_slice else None
            if session.last_tick is not None:
                tick_no = session.last_tick.tick
                brain = session.last_tick.brain
                action = session.last_tick.action
                nav = session.last_tick.nav
                if frame is None:
                    frame = session.last_tick.detections
            if plug_slice is not None:
                # The numbers (blocked/total cells, cost, feasibility) were computed
                # on the plug's slice, so that is the slice the rows are labelled with.
                label_slice = plug_slice
                ao_source = "session plug map_slice"
                if _ao_differs(map_slice, plug_slice):
                    ao_mismatch = (
                        "session planned on a different AO; tick the session with this "
                        "map_slice first"
                    )
            elif map_slice is not None:
                ao_source = "request map_slice (session has not observed a map slice)"
        if ao_mismatch is not None:
            # Never assert a computed quantity for an AO it was not computed on.
            rows = itdx_channel_rows(label_slice, brain, action, None, frame)
            for key in ("navigation", "pathways"):
                rows[key]["reason"] = ao_mismatch
            nav_out = None
        else:
            rows = itdx_channel_rows(label_slice, brain, action, nav, frame)
            nav_out = nav.model_dump() if nav is not None else None
        step = brain.step if brain is not None else None
        for row in rows.values():
            live = row.setdefault("live", {})
            live["step"] = step  # engine step count (dt-sized); not the tick number
            live["tick"] = tick_no
            live["ao_source"] = ao_source
        return {
            "schema_version": ITDX_CHANNELS_SCHEMA_VERSION,
            "origin": ORIGIN_SIMULATED,
            "channels": rows,
            "nav": nav_out,
            "session_id": session_id,
            "tick": tick_no,
            "step": step,
            "ao_source": ao_source,
            "ao_mismatch": ao_mismatch,
            "generated_at": utc_now_iso(),
        }

    async def nlm_observation(
        self, session_id: str, cutoff: Optional[Any] = None
    ) -> Dict[str, Any]:
        """``/nlm/observation``: envelope of the session's current rates → pipeline."""
        from datetime import datetime, timezone

        from mycosoft_mas.nlm.formspace.observation_pipeline import get_observation_pipeline

        session = self._session(session_id)
        async with session.lock:
            brain = self._brain_state(session, session.config.window_ms)
        envelope = build_envelope(session.id, session.info.ticks, brain.rates_hz, t_ms=brain.t_ms)
        if cutoff is None:
            cutoff_dt = envelope.available_at
        elif isinstance(cutoff, datetime):
            cutoff_dt = cutoff if cutoff.tzinfo else cutoff.replace(tzinfo=timezone.utc)
        else:
            cutoff_dt = datetime.fromisoformat(str(cutoff).replace("Z", "+00:00"))
            if cutoff_dt.tzinfo is None:
                cutoff_dt = cutoff_dt.replace(tzinfo=timezone.utc)
        result = get_observation_pipeline().process(envelope, cutoff=cutoff_dt)
        return {
            "origin": ORIGIN_SIMULATED,
            "session_id": session.id,
            "tick": session.info.ticks,
            "envelope": envelope.model_dump(mode="json"),
            "pipeline_result": result,
            "forecast": {
                "support_status": "UNSUPPORTED",
                "note": "FlyBrain never emits a probability",
            },
        }

    async def droid_guidance(
        self, device_id: str, session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """``/droid/{device_id}/guidance``: read-only view of the last tick's guidance.

        This call never actuates (``actuated_by_this_call=False``), but it reports
        the last tick's ``actuated`` / ``dry_run`` / ``reason`` exactly as recorded —
        an operator checking whether the Psathyrella was commanded must not be told
        "nothing actuated" after a tick that pushed waypoints."""
        from mycosoft_mas.flybrain.plugs.droid import DroidPlug

        if session_id:
            session = self._session(session_id)
            last = session.last_tick
            plug = session.plug
            session_dry_run = bool(session.config.dry_run)
            if isinstance(plug, DroidPlug) and last is not None:
                guidance = dict(plug.last_guidance or {})
                guidance.setdefault("dry_run", session_dry_run)
                guidance.setdefault("actuated", False)
                guidance.setdefault("avani", None)
                guidance.setdefault("reason", "last tick recorded no reason")
                guidance["device_id"] = device_id
                guidance["session_id"] = session.id
                guidance["tick"] = last.tick
                guidance.update(self._guidance_call_fields(session_dry_run, guidance["actuated"]))
                return guidance
            if last is not None:
                return {
                    "mode": "flybrain_locomotion" if last.action.kind == "locomotion" else "hold",
                    "origin": ORIGIN_SIMULATED,
                    "device_id": device_id,
                    "session_id": session.id,
                    "tick": last.tick,
                    "heading_delta_deg": last.action.heading_delta_deg,
                    "throttle_pct": last.action.throttle_pct,
                    "waypoints": (
                        [w.model_dump() for w in last.nav.waypoints]
                        if last.nav and last.nav.feasible
                        else []
                    ),
                    "camera_point_at": None,
                    "dry_run": session_dry_run,
                    "actuated": False,
                    "avani": None,
                    "reason": f"session plug is {session.config.plug!r}, not droid; guidance derived from its last action",
                    **self._guidance_call_fields(session_dry_run, False),
                }
            return {
                "mode": "hold",
                "origin": ORIGIN_SIMULATED,
                "device_id": device_id,
                "session_id": session.id,
                "tick": 0,
                "heading_delta_deg": 0.0,
                "throttle_pct": 0.0,
                "waypoints": [],
                "camera_point_at": None,
                "dry_run": session_dry_run,
                "actuated": False,
                "avani": None,
                "reason": "session has not ticked yet; no guidance",
                **self._guidance_call_fields(session_dry_run, False),
            }
        return {
            "mode": "hold",
            "origin": ORIGIN_SIMULATED,
            "device_id": device_id,
            "session_id": None,
            "tick": None,
            "heading_delta_deg": 0.0,
            "throttle_pct": 0.0,
            "waypoints": [],
            "camera_point_at": None,
            "dry_run": True,
            "actuated": False,
            "avani": None,
            "reason": "no session_id given; create a droid session and tick it first",
            **self._guidance_call_fields(True, False),
        }

    @staticmethod
    def _guidance_call_fields(session_dry_run: bool, last_tick_actuated: Any) -> Dict[str, Any]:
        """Fields that distinguish this read-only call from the tick history."""
        return {
            "actuated_by_this_call": False,
            "session_dry_run": bool(session_dry_run),
            "last_tick_actuated": bool(last_tick_actuated),
            "endpoint_note": (
                "guidance endpoint is read-only; this call actuated nothing. "
                "actuated/dry_run/reason are the last tick's recorded values"
            ),
        }

    # ------------------------------------------------------------------
    # Shutdown
    # ------------------------------------------------------------------

    async def close(self) -> None:
        for session_id in list(self._sessions):
            try:
                await self.delete_session(session_id)
            except Exception:  # noqa: BLE001
                pass


# ----------------------------------------------------------------------
# Singleton
# ----------------------------------------------------------------------

_RUNTIME: Optional[FlyBrainRuntime] = None
_RUNTIME_LOCK = threading.Lock()


def get_runtime() -> FlyBrainRuntime:
    global _RUNTIME
    with _RUNTIME_LOCK:
        if _RUNTIME is None:
            _RUNTIME = FlyBrainRuntime()
        return _RUNTIME


def reset_runtime_for_tests(settings: Optional[FlyBrainSettings] = None) -> FlyBrainRuntime:
    """Drop the singleton (cancelling nothing — call ``await runtime.close()`` first
    when autopilots may be running) and build a fresh one from the current env."""
    global _RUNTIME
    with _RUNTIME_LOCK:
        _RUNTIME = FlyBrainRuntime(settings)
        return _RUNTIME


__all__ = [
    "BackendUnavailable",
    "ConnectomeUnavailable",
    "FlyBrainRuntime",
    "RECORD_FILE",
    "Session",
    "SessionLimitReached",
    "SessionNotFound",
    "get_runtime",
    "reset_runtime_for_tests",
]
