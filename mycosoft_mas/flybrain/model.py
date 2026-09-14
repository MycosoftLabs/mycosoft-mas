"""FlyBrain LIF engine (spec §4): event-driven numpy port of the Shiu et al. 2024
whole-brain leaky integrate-and-fire model (MIT ``model.py`` equations and
``default_params``), with an optional interface-identical torch backend.

Per step (``dt = 0.1 ms``, float32 state of length N)::

    refrac    = where(spikes_prev > 0, 0, refrac + 1)
    gate      = refrac >= refrac_steps          # 22 steps; 0 for externally driven neurons
    g_new     = g * (1 - dt/tauSyn) + delayed_input * gate
    delayed_input: circular ring realising steps_delay = round(1.8/dt) = 18 steps
                   (Brian2 timing: a spike at step s raises g at s+18 and moves v at s+19)
    v         = v + wScale * poisson * scalePoisson       # only driven neurons
    v         = v + (dt/tauMem) * (g_old - (v - vRest))   # g BEFORE this step's update
    spike     = v > vThreshold ; v[spike] = vReset ; g_new[spike] = 0
    recurrent_input[post] = wScale * sum_{pre spiked, not silenced} W[post, pre]

The recurrent input is gathered from the CSC columns of the neurons that
spiked (event-driven), which is what makes the full 138k-neuron brain run
at hundreds of steps per second on a CPU.

Delay timing (which reference the port claims): the ring is allocated with
``steps_delay - 1`` slots because the gather at step ``k`` already consumes
one step (it uses the spikes of step ``k - 1``). The result matches the
Brian2 CPU ground truth: a pre spike at step ``s`` is delivered to ``g`` at
``s + steps_delay`` and first moves ``v`` at ``s + steps_delay + 1``
(earliest post-synaptic spike 1.9 ms after the pre spike at dt = 0.1 ms).
The GPL ``run_pytorch.py`` benchmark backend uses a ``steps_delay + 1`` roll
buffer and is therefore two steps (0.2 ms) later than this port on every
recurrent spike; population statistics are unaffected.

The engine is not thread-safe; the runtime guards each session with a lock.
All numeric imports are lazy so this module imports under
``MAS_LIGHT_IMPORT=1`` and without torch.
"""

from __future__ import annotations

import logging
import time
from collections import deque
from dataclasses import asdict, dataclass
from typing import (
    TYPE_CHECKING,
    Any,
    Deque,
    Dict,
    List,
    Optional,
    Sequence,
    Tuple,
    Union,
)

from mycosoft_mas.flybrain.connectome import Connectome, _ragged_ranges
from mycosoft_mas.flybrain.schemas import SubgraphSpec

if TYPE_CHECKING:  # pragma: no cover - typing only
    import numpy as np

    from mycosoft_mas.flybrain.atlas import Atlas

logger = logging.getLogger(__name__)

SPIKE_HISTORY_CAP = 2_000_000
BACKEND_NUMPY = "numpy"
BACKEND_TORCH_CPU = "torch:cpu"
BACKEND_TORCH_CUDA = "torch:cuda"


class BackendUnavailable(RuntimeError):
    """An explicitly requested backend cannot run on this host."""


# ---------------------------------------------------------------------------
# Parameters
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LIFParams:
    """Published defaults (Shiu et al. 2024; Kakaria & de Bivort 2017; Lazar 2021;
    Paul 2015; Jürgensen 2021). Units: ms and mV."""

    tau_syn_ms: float = 5.0
    t_delay_ms: float = 1.8
    v0_mv: float = -52.0
    v_reset_mv: float = -52.0
    v_rest_mv: float = -52.0
    v_threshold_mv: float = -45.0
    tau_mem_ms: float = 20.0
    t_refrac_ms: float = 2.2
    scale_poisson: float = 250.0
    w_scale_mv: float = 0.275

    def steps_delay(self, dt_ms: float) -> int:
        return max(1, int(round(self.t_delay_ms / dt_ms)))

    def refrac_steps(self, dt_ms: float) -> int:
        return max(0, int(round(self.t_refrac_ms / dt_ms)))

    @property
    def stim_mv(self) -> float:
        """Voltage jump per Poisson event: ``wScale * scalePoisson`` (68.75 mV)."""
        return self.w_scale_mv * self.scale_poisson

    def as_dict(self) -> Dict[str, float]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Backend detection
# ---------------------------------------------------------------------------


def _try_import_torch() -> Any:
    try:
        import torch  # type: ignore

        return torch
    except Exception:  # ImportError or a broken install
        return None


def torch_available() -> bool:
    return _try_import_torch() is not None


def cuda_available() -> bool:
    torch = _try_import_torch()
    if torch is None:
        return False
    try:
        return bool(torch.cuda.is_available())
    except Exception:
        return False


def resolve_backend(name: Optional[str]) -> str:
    """Map a requested backend to one of numpy / torch:cpu / torch:cuda.

    ``auto`` picks torch only when CUDA is present (on a CPU the event-driven
    numpy path is faster than a dense sparse matmul); with no torch installed
    it silently resolves to numpy. An explicit ``torch`` request on a host
    without torch raises :class:`BackendUnavailable`.
    """
    requested = (name or "auto").strip().lower() or "auto"
    torch = _try_import_torch()
    has_cuda = False
    if torch is not None:
        try:
            has_cuda = bool(torch.cuda.is_available())
        except Exception:
            has_cuda = False

    if requested == BACKEND_NUMPY:
        return BACKEND_NUMPY
    if requested == "auto":
        return BACKEND_TORCH_CUDA if (torch is not None and has_cuda) else BACKEND_NUMPY
    if requested in {"torch", BACKEND_TORCH_CPU, BACKEND_TORCH_CUDA}:
        if torch is None:
            raise BackendUnavailable("backend 'torch' requested but torch is not installed")
        if requested == BACKEND_TORCH_CUDA and not has_cuda:
            raise BackendUnavailable("backend 'torch:cuda' requested but CUDA is not available")
        if requested == BACKEND_TORCH_CPU:
            return BACKEND_TORCH_CPU
        return BACKEND_TORCH_CUDA if has_cuda else BACKEND_TORCH_CPU
    raise ValueError(f"unknown backend {name!r} (expected auto|numpy|torch)")


# ---------------------------------------------------------------------------
# Spike history ring
# ---------------------------------------------------------------------------


class SpikeHistory:
    """Ring of recent spikes: one ``(t_ms, indices)`` chunk per step that spiked,
    capped at ``cap`` spike entries (oldest chunks dropped first)."""

    def __init__(self, cap: int = SPIKE_HISTORY_CAP) -> None:
        self.cap = int(cap)
        self._chunks: Deque[Tuple[float, "np.ndarray"]] = deque()
        self.total = 0
        self.dropped = 0
        self.oldest_t_ms: Optional[float] = None

    def clear(self) -> None:
        self._chunks.clear()
        self.total = 0
        self.dropped = 0
        self.oldest_t_ms = None

    def append(self, t_ms: float, indices: "np.ndarray") -> None:
        n = int(indices.shape[0])
        if n == 0:
            return
        self._chunks.append((t_ms, indices))
        self.total += n
        while self.total > self.cap and self._chunks:
            _, old = self._chunks.popleft()
            self.total -= int(old.shape[0])
            self.dropped += int(old.shape[0])
        self.oldest_t_ms = self._chunks[0][0] if self._chunks else None

    def since(self, t_start_ms: float) -> Tuple["np.ndarray", "np.ndarray"]:
        """Spikes with ``t >= t_start_ms`` (chronological)."""
        import numpy as np

        selected: List[Tuple[float, "np.ndarray"]] = []
        for t, idx in reversed(self._chunks):
            if t < t_start_ms:
                break
            selected.append((t, idx))
        if not selected:
            return np.empty(0, dtype=np.float64), np.empty(0, dtype=np.int64)
        selected.reverse()
        times = np.concatenate([np.full(idx.shape[0], t, dtype=np.float64) for t, idx in selected])
        indices = np.concatenate([idx for _, idx in selected]).astype(np.int64, copy=False)
        return times, indices

    def last(self, limit: int) -> Tuple["np.ndarray", "np.ndarray"]:
        import numpy as np

        limit = max(0, int(limit))
        if limit == 0 or not self._chunks:
            return np.empty(0, dtype=np.float64), np.empty(0, dtype=np.int64)
        selected: List[Tuple[float, "np.ndarray"]] = []
        count = 0
        for t, idx in reversed(self._chunks):
            selected.append((t, idx))
            count += int(idx.shape[0])
            if count >= limit:
                break
        selected.reverse()
        times = np.concatenate([np.full(idx.shape[0], t, dtype=np.float64) for t, idx in selected])
        indices = np.concatenate([idx for _, idx in selected]).astype(np.int64, copy=False)
        return times[-limit:], indices[-limit:]

    def covers(self, t_start_ms: float) -> bool:
        """True when nothing from ``t_start_ms`` onward has been evicted."""
        return self.dropped == 0 or (
            self.oldest_t_ms is not None and self.oldest_t_ms <= t_start_ms
        )


# ---------------------------------------------------------------------------
# numpy core
# ---------------------------------------------------------------------------


class _NumpyCore:
    """State + one-step update on numpy arrays (event-driven CSC gather)."""

    name = BACKEND_NUMPY

    def __init__(self, csc: Any, params: LIFParams, dt_ms: float, rng: Any) -> None:
        import numpy as np

        self.np = np
        self.n = int(csc.shape[0])
        self.params = params
        self.dt = float(dt_ms)
        self.rng = rng
        self.indptr = np.asarray(csc.indptr, dtype=np.int64)
        self.indices = np.asarray(csc.indices, dtype=np.int64)
        self.data = np.asarray(csc.data, dtype=np.float32)
        self.steps_delay = params.steps_delay(dt_ms)
        # Brian2 timing: the gather at step k uses spikes of step k-1, so a ring of
        # steps_delay-1 slots delivers a spike from step s into g at s+steps_delay.
        self.ring_slots = max(1, self.steps_delay - 1)
        self.base_refrac = params.refrac_steps(dt_ms)
        self.decay = np.float32(1.0 - dt_ms / params.tau_syn_ms)
        self.tf = np.float32(dt_ms / params.tau_mem_ms)
        self.v_rest = np.float32(params.v_rest_mv)
        self.v_reset = np.float32(params.v_reset_mv)
        self.v_th = np.float32(params.v_threshold_mv)
        self.stim = np.float32(params.stim_mv)
        self.w_scale = float(params.w_scale_mv)

        self.refrac_steps = np.full(self.n, self.base_refrac, dtype=np.int64)
        self.silenced_mask = np.zeros(self.n, dtype=bool)
        self.any_silenced = False
        self.driven_idx = np.empty(0, dtype=np.int64)
        self.driven_p = np.empty(0, dtype=np.float64)
        self.reset()

    def reset(self) -> None:
        np = self.np
        self.v = np.full(self.n, self.params.v0_mv, dtype=np.float32)
        self.g = np.zeros(self.n, dtype=np.float32)
        self.buf = np.zeros((self.ring_slots, self.n), dtype=np.float32)
        self.refrac_until = np.zeros(self.n, dtype=np.int64)
        self.last_spikes = np.empty(0, dtype=np.int64)
        self.last_spike_step = -(10**9)

    # configuration ----------------------------------------------------

    def set_drive(self, driven_idx: "np.ndarray", driven_p: "np.ndarray") -> None:
        np = self.np
        self.driven_idx = np.asarray(driven_idx, dtype=np.int64)
        self.driven_p = np.asarray(driven_p, dtype=np.float64)
        self.refrac_steps[:] = self.base_refrac
        if self.driven_idx.size:
            self.refrac_steps[self.driven_idx] = 0

    def set_silenced(self, mask: "np.ndarray") -> None:
        self.silenced_mask = mask
        self.any_silenced = bool(mask.any())

    # dynamics ---------------------------------------------------------

    def _gather(self, pre: "np.ndarray") -> Optional["np.ndarray"]:
        np = self.np
        if pre.size == 0:
            return None
        if self.any_silenced:
            pre = pre[~self.silenced_mask[pre]]
            if pre.size == 0:
                return None
        offs = _ragged_ranges(self.indptr[pre], self.indptr[pre + 1])
        if offs.size == 0:
            return None
        rec = np.bincount(self.indices[offs], weights=self.data[offs], minlength=self.n)
        rec *= self.w_scale
        return rec.astype(np.float32, copy=False)

    def step(self, k: int) -> "np.ndarray":
        np = self.np
        slot = k % self.ring_slots
        delayed = self.buf[slot]  # view; written at step k - ring_slots (spikes of k - steps_delay)

        # Refractory gate on the delayed synaptic input.
        if k - self.last_spike_step <= self.base_refrac:
            blocked = np.flatnonzero(self.refrac_until > k)
            if blocked.size:
                delayed[blocked] = 0.0

        g_old = self.g
        g_new = g_old * self.decay
        g_new += delayed

        # Recurrent input from last step's spikes goes into the slot we just consumed.
        rec = self._gather(self.last_spikes)
        if rec is None:
            delayed[:] = 0.0
        else:
            self.buf[slot] = rec

        v = self.v
        if self.driven_idx.size:
            hits = self.rng.random(self.driven_idx.size) < self.driven_p
            if hits.any():
                v[self.driven_idx[hits]] += self.stim

        # v += tf * (g_old - (v - v_rest))
        v *= np.float32(1.0) - self.tf
        v += self.tf * g_old
        v += self.tf * self.v_rest

        spk = np.flatnonzero(v > self.v_th)
        if spk.size:
            v[spk] = self.v_reset
            g_new[spk] = 0.0
            self.refrac_until[spk] = k + 1 + self.refrac_steps[spk]
            self.last_spike_step = k
        self.g = g_new
        self.last_spikes = spk
        return spk

    def voltages(self) -> "np.ndarray":
        return self.v


# ---------------------------------------------------------------------------
# torch core (optional; mirrors _NumpyCore)
# ---------------------------------------------------------------------------


class _TorchCore:
    """Same update on torch tensors (dense state vectors, sparse CSR matmul)."""

    def __init__(
        self,
        csc: Any,
        params: LIFParams,
        dt_ms: float,
        seed: Optional[int],
        device: str,
        threads: Optional[int] = None,
    ) -> None:
        import numpy as np
        import torch  # type: ignore

        self.np = np
        self.torch = torch
        self.device = torch.device(device)
        self.name = BACKEND_TORCH_CUDA if self.device.type == "cuda" else BACKEND_TORCH_CPU
        if threads and self.device.type == "cpu":
            try:
                torch.set_num_threads(int(threads))
            except Exception:  # pragma: no cover - best effort
                pass
        self.n = int(csc.shape[0])
        self.params = params
        self.dt = float(dt_ms)
        self.steps_delay = params.steps_delay(dt_ms)
        self.ring_slots = max(1, self.steps_delay - 1)  # same Brian2 timing as _NumpyCore
        self.base_refrac = params.refrac_steps(dt_ms)
        self.decay = float(1.0 - dt_ms / params.tau_syn_ms)
        self.tf = float(dt_ms / params.tau_mem_ms)
        self.v_rest = float(params.v_rest_mv)
        self.v_reset = float(params.v_reset_mv)
        self.v_th = float(params.v_threshold_mv)
        self.stim = float(params.stim_mv)
        self.w_scale = float(params.w_scale_mv)

        csr = csc.tocsr()
        csr.sort_indices()
        self.weights = torch.sparse_csr_tensor(
            torch.from_numpy(np.asarray(csr.indptr, dtype=np.int64)),
            torch.from_numpy(np.asarray(csr.indices, dtype=np.int64)),
            torch.from_numpy(np.asarray(csr.data, dtype=np.float32)),
            size=(self.n, self.n),
        ).to(self.device)
        self.gen = torch.Generator(device=self.device)
        if seed is not None:
            self.gen.manual_seed(int(seed))
        else:
            self.gen.seed()

        self.refrac_steps = torch.full(
            (self.n,), self.base_refrac, dtype=torch.int64, device=self.device
        )
        self.silence_vec = torch.ones(self.n, dtype=torch.float32, device=self.device)
        self.driven_idx = torch.empty(0, dtype=torch.int64, device=self.device)
        self.driven_p = torch.empty(0, dtype=torch.float32, device=self.device)
        self.reset()

    def reset(self) -> None:
        torch = self.torch
        self.v = torch.full((self.n,), self.params.v0_mv, dtype=torch.float32, device=self.device)
        self.g = torch.zeros(self.n, dtype=torch.float32, device=self.device)
        self.buf = torch.zeros((self.ring_slots, self.n), dtype=torch.float32, device=self.device)
        self.refrac_until = torch.zeros(self.n, dtype=torch.int64, device=self.device)
        self.spike_vec = torch.zeros(self.n, dtype=torch.float32, device=self.device)
        self.last_spike_step = -(10**9)

    def set_drive(self, driven_idx: "np.ndarray", driven_p: "np.ndarray") -> None:
        torch = self.torch
        self.driven_idx = torch.as_tensor(
            self.np.asarray(driven_idx, dtype=self.np.int64), device=self.device
        )
        self.driven_p = torch.as_tensor(
            self.np.asarray(driven_p, dtype=self.np.float32), device=self.device
        )
        self.refrac_steps.fill_(self.base_refrac)
        if self.driven_idx.numel():
            self.refrac_steps[self.driven_idx] = 0

    def set_silenced(self, mask: "np.ndarray") -> None:
        keep = (~self.np.asarray(mask, dtype=bool)).astype(self.np.float32)
        self.silence_vec = self.torch.as_tensor(keep, device=self.device)

    def step(self, k: int) -> "np.ndarray":
        torch = self.torch
        slot = k % self.ring_slots
        delayed = self.buf[slot]
        if k - self.last_spike_step <= self.base_refrac:
            delayed = delayed * (self.refrac_until <= k).to(torch.float32)

        g_old = self.g
        g_new = g_old * self.decay + delayed

        # recurrent input from last step's spikes (silenced pre neurons contribute 0)
        if bool(self.spike_vec.any()):
            src = (self.spike_vec * self.silence_vec).unsqueeze(1)
            rec = torch.sparse.mm(self.weights, src).squeeze(1) * self.w_scale
            self.buf[slot] = rec
        else:
            self.buf[slot].zero_()

        v = self.v
        if self.driven_idx.numel():
            hits = torch.rand(self.driven_idx.numel(), generator=self.gen, device=self.device)
            hits = hits < self.driven_p
            if bool(hits.any()):
                v[self.driven_idx[hits]] += self.stim
        v = v + self.tf * (g_old - (v - self.v_rest))
        spike = v > self.v_th
        self.spike_vec = spike.to(torch.float32)
        if bool(spike.any()):
            v = torch.where(spike, torch.full_like(v, self.v_reset), v)
            g_new = torch.where(spike, torch.zeros_like(g_new), g_new)
            idx = torch.nonzero(spike, as_tuple=False).squeeze(1)
            self.refrac_until[idx] = k + 1 + self.refrac_steps[idx]
            self.last_spike_step = k
            out = idx.detach().cpu().numpy().astype(self.np.int64)
        else:
            out = self.np.empty(0, dtype=self.np.int64)
        self.v = v
        self.g = g_new
        return out

    def voltages(self) -> "np.ndarray":
        return self.v.detach().cpu().numpy()


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------


SubgraphArg = Union[None, SubgraphSpec, Tuple[Any, "np.ndarray"]]


class FlyBrainEngine:
    """Whole-brain (or subgraph) LIF simulator over a :class:`Connectome`.

    Indices passed to / returned by the engine are **engine-local**; in full
    brain mode they equal connectome indices, in subgraph mode use
    :meth:`to_global` / :meth:`to_local`.
    """

    def __init__(
        self,
        connectome: Connectome,
        params: Optional[LIFParams] = None,
        dt_ms: float = 0.1,
        seed: Optional[int] = None,
        backend: str = "auto",
        subgraph: SubgraphArg = None,
        atlas: Optional["Atlas"] = None,
        seed_indices: Optional[Sequence[int]] = None,
        spike_history_cap: int = SPIKE_HISTORY_CAP,
        torch_threads: Optional[int] = None,
    ) -> None:
        import numpy as np

        if dt_ms <= 0:
            raise ValueError("dt_ms must be > 0")
        self.connectome = connectome
        self.params = params or LIFParams()
        self.dt_ms = float(dt_ms)
        self.seed = seed
        self._rng = np.random.default_rng(seed)

        # Subgraph resolution -------------------------------------------------
        self.subgraph_info: Optional[Dict[str, Any]] = None
        self._local_to_global: Optional["np.ndarray"] = None
        self._global_to_local: Optional["np.ndarray"] = None
        matrix = connectome.csc
        if subgraph is not None:
            local_csc, local_to_global, info = self._resolve_subgraph(
                connectome, subgraph, atlas, seed_indices
            )
            matrix = local_csc
            self._local_to_global = np.asarray(local_to_global, dtype=np.int64)
            g2l = np.full(connectome.n_neurons, -1, dtype=np.int64)
            g2l[self._local_to_global] = np.arange(self._local_to_global.size, dtype=np.int64)
            self._global_to_local = g2l
            self.subgraph_info = info

        self.matrix = matrix
        self.n_neurons = int(matrix.shape[0])
        self.n_synapses = int(matrix.nnz)

        # Backend -------------------------------------------------------------
        resolved = resolve_backend(backend)
        if resolved == BACKEND_NUMPY:
            self._core: Any = _NumpyCore(matrix, self.params, self.dt_ms, self._rng)
        else:
            device = "cuda" if resolved == BACKEND_TORCH_CUDA else "cpu"
            self._core = _TorchCore(
                matrix, self.params, self.dt_ms, seed, device, threads=torch_threads
            )
        self.backend: str = self._core.name

        # Stimulation / silencing state (local indices) ------------------------
        self._rates: Dict[int, float] = {}
        self._silenced: set = set()
        self._silenced_mask = np.zeros(self.n_neurons, dtype=bool)

        self.step_count = 0
        self.t_ms = 0.0
        self.history = SpikeHistory(spike_history_cap)
        self.total_spikes = 0
        self.last_run_wall_s: Optional[float] = None
        self.last_run_steps: int = 0

    # ------------------------------------------------------------------
    # Subgraph helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _resolve_subgraph(
        connectome: Connectome,
        subgraph: SubgraphArg,
        atlas: Optional["Atlas"],
        seed_indices: Optional[Sequence[int]],
    ) -> Tuple[Any, "np.ndarray", Dict[str, Any]]:
        import numpy as np

        if isinstance(subgraph, SubgraphSpec):
            seeds: List[int] = []
            if atlas is not None and subgraph.seed_groups:
                seeds = atlas.indices(subgraph.seed_groups)
            if not seeds and seed_indices is not None:
                seeds = [int(i) for i in seed_indices]
            if not seeds:
                raise ValueError(
                    "SubgraphSpec resolves to no seed neurons: pass an atlas whose seed_groups "
                    "exist in this connectome, or explicit seed_indices"
                )
            local_csc, local_to_global = connectome.subgraph(
                seeds,
                hops=subgraph.hops,
                min_weight=subgraph.min_weight,
                max_neurons=subgraph.max_neurons,
            )
            info = {
                "seed_groups": list(subgraph.seed_groups),
                "n_seeds": len(set(seeds)),
                "hops": subgraph.hops,
                "min_weight": subgraph.min_weight,
                "max_neurons": subgraph.max_neurons,
                "n_neurons": int(local_csc.shape[0]),
                "n_synapses": int(local_csc.nnz),
                "capped": bool(local_csc.shape[0] >= subgraph.max_neurons),
            }
            return local_csc, local_to_global, info
        if isinstance(subgraph, tuple) and len(subgraph) == 2:
            local_csc, local_to_global = subgraph
            local_to_global = np.asarray(local_to_global, dtype=np.int64)
            if local_csc.shape != (local_to_global.size, local_to_global.size):
                raise ValueError("subgraph tuple: matrix shape does not match local_to_global")
            info = {
                "seed_groups": [],
                "n_seeds": 0,
                "hops": None,
                "min_weight": None,
                "max_neurons": None,
                "n_neurons": int(local_csc.shape[0]),
                "n_synapses": int(local_csc.nnz),
                "capped": False,
            }
            return local_csc, local_to_global, info
        raise TypeError(
            "subgraph must be None, a SubgraphSpec or a (local_csc, local_to_global) tuple"
        )

    @property
    def is_subgraph(self) -> bool:
        return self._local_to_global is not None

    @property
    def local_to_global(self) -> "np.ndarray":
        import numpy as np

        if self._local_to_global is None:
            return np.arange(self.n_neurons, dtype=np.int64)
        return self._local_to_global

    def to_global(self, indices: Sequence[int]) -> "np.ndarray":
        """Local → connectome indices (identity in full-brain mode)."""
        import numpy as np

        idx = np.asarray(indices, dtype=np.int64)
        if self._local_to_global is None:
            return idx
        return self._local_to_global[idx]

    def to_local(self, global_indices: Sequence[int]) -> "np.ndarray":
        """Connectome → local indices. Neurons outside the subgraph are omitted;
        use :meth:`missing_from_subgraph` to see which ones."""
        import numpy as np

        idx = np.asarray(global_indices, dtype=np.int64)
        if self._global_to_local is None:
            return idx
        local = self._global_to_local[idx]
        return local[local >= 0]

    def missing_from_subgraph(self, global_indices: Sequence[int]) -> "np.ndarray":
        import numpy as np

        idx = np.asarray(global_indices, dtype=np.int64)
        if self._global_to_local is None:
            return np.empty(0, dtype=np.int64)
        return idx[self._global_to_local[idx] < 0]

    def flywire_ids(self, local_indices: Sequence[int]) -> List[int]:
        return self.connectome.ids_for_indices(self.to_global(local_indices))

    # ------------------------------------------------------------------
    # Stimulation
    # ------------------------------------------------------------------

    def _check_indices(self, indices: Sequence[int]) -> "np.ndarray":
        import numpy as np

        idx = np.unique(np.asarray(list(indices), dtype=np.int64))
        if idx.size and (idx.min() < 0 or idx.max() >= self.n_neurons):
            raise IndexError(f"neuron index out of range 0..{self.n_neurons - 1}")
        return idx

    def _push_drive(self) -> None:
        import numpy as np

        if self._rates:
            idx = np.fromiter(self._rates.keys(), dtype=np.int64, count=len(self._rates))
            hz = np.fromiter(self._rates.values(), dtype=np.float64, count=len(self._rates))
            order = np.argsort(idx)
            idx = idx[order]
            p = np.clip(hz[order] * self.dt_ms / 1000.0, 0.0, 1.0)
        else:
            idx = np.empty(0, dtype=np.int64)
            p = np.empty(0, dtype=np.float64)
        self._core.set_drive(idx, p)

    def set_rates(self, indices: Sequence[int], rate_hz: Union[float, Sequence[float]]) -> None:
        """Persistent Poisson drive ``bernoulli(rate_hz * dt / 1000)`` per step.

        Driven neurons have their refractory period set to 0 (as in the
        published model). ``rate_hz`` may be a scalar or one value per index;
        a rate of 0 removes the drive.
        """
        import numpy as np

        # Pair each rate with the caller's index BEFORE any sorting/de-duplication
        # (np.unique in _check_indices would reorder them). Duplicates: last write wins.
        raw = np.asarray(list(indices), dtype=np.int64)
        if raw.size and (raw.min() < 0 or raw.max() >= self.n_neurons):
            raise IndexError(f"neuron index out of range 0..{self.n_neurons - 1}")
        rates = np.broadcast_to(np.asarray(rate_hz, dtype=np.float64), raw.shape)
        if np.any(rates < 0):
            raise ValueError("rate_hz must be >= 0")
        for i, r in zip(raw.tolist(), rates.tolist()):
            if r > 0:
                self._rates[i] = float(r)
            else:
                self._rates.pop(i, None)
        self._push_drive()

    def clear_rates(self, indices: Optional[Sequence[int]] = None) -> None:
        if indices is None:
            self._rates.clear()
        else:
            for i in self._check_indices(indices).tolist():
                self._rates.pop(i, None)
        self._push_drive()

    @property
    def rates(self) -> Dict[int, float]:
        return dict(self._rates)

    @property
    def driven_indices(self) -> List[int]:
        return sorted(self._rates)

    def silence(self, indices: Sequence[int]) -> None:
        """Zero every outgoing synapse of ``indices`` (they may still spike)."""
        idx = self._check_indices(indices)
        self._silenced.update(idx.tolist())
        self._silenced_mask[idx] = True
        self._core.set_silenced(self._silenced_mask)

    def unsilence(self, indices: Optional[Sequence[int]] = None) -> None:
        if indices is None:
            self._silenced.clear()
            self._silenced_mask[:] = False
        else:
            idx = self._check_indices(indices)
            self._silenced.difference_update(idx.tolist())
            self._silenced_mask[idx] = False
        self._core.set_silenced(self._silenced_mask)

    @property
    def silenced(self) -> List[int]:
        return sorted(self._silenced)

    # ------------------------------------------------------------------
    # Simulation
    # ------------------------------------------------------------------

    def step(self) -> "np.ndarray":
        """Advance one ``dt``; returns the local indices that spiked."""
        k = self.step_count
        spikes = self._core.step(k)
        t_spike = k * self.dt_ms
        self.step_count = k + 1
        self.t_ms = self.step_count * self.dt_ms
        if spikes.size:
            self.history.append(t_spike, spikes)
            self.total_spikes += int(spikes.size)
        return spikes

    def run(self, duration_ms: float, record: bool = True) -> Tuple["np.ndarray", "np.ndarray"]:
        """Run ``duration_ms`` (rounded to whole steps). Returns concatenated
        ``(times_ms, indices)`` of the spikes in this run (empty when
        ``record=False``; the rate history is always maintained)."""
        import numpy as np

        n_steps = int(round(float(duration_ms) / self.dt_ms))
        if n_steps <= 0:
            return np.empty(0, dtype=np.float64), np.empty(0, dtype=np.int64)
        times: List["np.ndarray"] = []
        idxs: List["np.ndarray"] = []
        t0 = time.perf_counter()
        for _ in range(n_steps):
            t_spike = self.step_count * self.dt_ms
            spikes = self.step()
            if record and spikes.size:
                times.append(np.full(spikes.size, t_spike, dtype=np.float64))
                idxs.append(spikes)
        wall = time.perf_counter() - t0
        self.last_run_wall_s = wall
        self.last_run_steps = n_steps
        if not times:
            return np.empty(0, dtype=np.float64), np.empty(0, dtype=np.int64)
        return np.concatenate(times), np.concatenate(idxs).astype(np.int64, copy=False)

    @property
    def steps_per_second(self) -> Optional[float]:
        if not self.last_run_wall_s or self.last_run_wall_s <= 0:
            return None
        return self.last_run_steps / self.last_run_wall_s

    @property
    def realtime_ratio(self) -> Optional[float]:
        """Simulated ms per wall ms of the last run (>1 = faster than real time)."""
        if not self.last_run_wall_s or self.last_run_wall_s <= 0:
            return None
        return (self.last_run_steps * self.dt_ms) / (self.last_run_wall_s * 1000.0)

    # ------------------------------------------------------------------
    # Read-outs
    # ------------------------------------------------------------------

    def _window(self, window_ms: float) -> Tuple[float, float]:
        window_ms = float(window_ms)
        if window_ms <= 0:
            raise ValueError("window_ms must be > 0")
        t_start = max(0.0, self.t_ms - window_ms)
        return t_start, max(window_ms, 1e-9)

    def spikes_in_window(self, window_ms: float) -> Tuple["np.ndarray", "np.ndarray"]:
        t_start, _ = self._window(window_ms)
        return self.history.since(t_start)

    def mean_rates(self, indices: Optional[Sequence[int]], window_ms: float) -> float:
        """Mean firing rate (Hz per neuron) of ``indices`` over the last
        ``window_ms`` of simulated time (all neurons when ``indices`` is None).
        Returns 0.0 for an empty index set."""
        import numpy as np

        t_start, span = self._window(window_ms)
        _, idx = self.history.since(t_start)
        if indices is None:
            n = self.n_neurons
            count = int(idx.size)
        else:
            sel = self._check_indices(indices)
            n = int(sel.size)
            if n == 0:
                return 0.0
            count = int(np.isin(idx, sel).sum()) if idx.size else 0
        elapsed = min(span, max(self.t_ms, self.dt_ms))
        return count / n / (elapsed / 1000.0)

    def rates_by_neuron(self, indices: Sequence[int], window_ms: float) -> "np.ndarray":
        """Per-neuron Hz over the window, aligned with ``indices``."""
        import numpy as np

        t_start, span = self._window(window_ms)
        _, idx = self.history.since(t_start)
        sel = np.asarray(list(indices), dtype=np.int64)
        if sel.size == 0:
            return np.empty(0, dtype=np.float64)
        counts = np.bincount(idx, minlength=self.n_neurons)[sel] if idx.size else np.zeros(sel.size)
        elapsed = min(span, max(self.t_ms, self.dt_ms))
        return counts / (elapsed / 1000.0)

    def recent_spikes(self, limit: int = 10_000) -> Tuple["np.ndarray", "np.ndarray"]:
        return self.history.last(limit)

    def voltages(self) -> "np.ndarray":
        return self._core.voltages()

    def snapshot(self, window_ms: float = 50.0) -> Dict[str, Any]:
        import numpy as np

        t_start, _ = self._window(window_ms)
        _, idx = self.history.since(t_start)
        n_active = int(np.unique(idx).size) if idx.size else 0
        return {
            "backend": self.backend,
            "t_ms": self.t_ms,
            "step_count": self.step_count,
            "dt_ms": self.dt_ms,
            "n_neurons": self.n_neurons,
            "n_synapses": self.n_synapses,
            "n_driven": len(self._rates),
            "n_silenced": len(self._silenced),
            "window_ms": float(window_ms),
            "spike_count_window": int(idx.size),
            "n_active": n_active,
            "total_spikes": self.total_spikes,
            "history_covers_window": self.history.covers(t_start),
            "history_size": self.history.total,
            "steps_per_second": self.steps_per_second,
            "realtime_ratio": self.realtime_ratio,
            "subgraph": dict(self.subgraph_info) if self.subgraph_info else None,
            "params": self.params.as_dict(),
        }

    # ------------------------------------------------------------------
    # Reset
    # ------------------------------------------------------------------

    def reset(self, keep_stimuli: bool = True, reseed: bool = True) -> None:
        """Restore ``t=0``: membrane/synaptic state, delay buffer, refractory
        timers and spike history. Drive/silence configuration is kept unless
        ``keep_stimuli=False``. With ``reseed=True`` the RNG restarts from the
        construction seed so a seeded run is reproducible after reset."""
        import numpy as np

        if reseed:
            self._rng = np.random.default_rng(self.seed)
            if isinstance(self._core, _NumpyCore):
                self._core.rng = self._rng
            elif self.seed is not None:  # torch
                self._core.gen.manual_seed(int(self.seed))
        self._core.reset()
        self.step_count = 0
        self.t_ms = 0.0
        self.history.clear()
        self.total_spikes = 0
        self.last_run_wall_s = None
        self.last_run_steps = 0
        if not keep_stimuli:
            self._rates.clear()
            self._silenced.clear()
            self._silenced_mask[:] = False
            self._core.set_silenced(self._silenced_mask)
        self._push_drive()

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return (
            f"FlyBrainEngine(n_neurons={self.n_neurons}, n_synapses={self.n_synapses}, "
            f"backend={self.backend!r}, t_ms={self.t_ms:.1f})"
        )


def bernoulli_expected_spikes(rate_hz: float, duration_ms: float, dt_ms: float = 0.1) -> float:
    """Expected number of Poisson-drive events for a driven neuron (test helper)."""
    p = min(1.0, max(0.0, rate_hz * dt_ms / 1000.0))
    return p * int(round(duration_ms / dt_ms))


__all__ = [
    "BACKEND_NUMPY",
    "BACKEND_TORCH_CPU",
    "BACKEND_TORCH_CUDA",
    "BackendUnavailable",
    "FlyBrainEngine",
    "LIFParams",
    "SPIKE_HISTORY_CAP",
    "SpikeHistory",
    "bernoulli_expected_spikes",
    "cuda_available",
    "resolve_backend",
    "torch_available",
]
