"""FlyWire v783 connectome loader (spec §1).

Loads the two FlyWire public-release files into a sparse float32 weight
matrix and an id<->index mapping:

* ``2025_Completeness_783.csv`` — header ``,Completed``; the first column is
  the FlyWire root id; row order defines the neuron index used by the
  connectivity file (exactly as in the MIT ``model.py`` of Shiu et al.).
* ``2025_Connectivity_783.npz`` (preferred; produced by
  ``scripts/flybrain_fetch_connectome.py`` from the parquet) with keys
  ``pre``, ``post``, ``weight``, ``n_neurons``, ``source_sha256`` — or, as a
  fallback, ``2025_Connectivity_783.parquet`` via pyarrow/pandas when one of
  them is importable.

Honesty: when the files are missing the loader raises
:class:`ConnectomeUnavailable`; there is no toy fallback in production
paths. Tests build an explicit in-memory connectome with
:meth:`Connectome.from_arrays`.

Heavy imports (numpy, scipy) are performed inside functions so that
``import mycosoft_mas.flybrain.connectome`` is safe under
``MAS_LIGHT_IMPORT=1``.
"""

from __future__ import annotations

import hashlib
import logging
import threading
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, Iterable, List, Optional, Sequence, Tuple, Union

from mycosoft_mas.flybrain.config import (
    COMPLETENESS_FILE,
    CONNECTIVITY_NPZ,
    CONNECTIVITY_PARQUET,
    KNOWN_SHA256,
    FlyBrainSettings,
    get_settings,
)
from mycosoft_mas.flybrain.schemas import ConnectomeManifest

if TYPE_CHECKING:  # pragma: no cover - typing only
    import numpy as np
    import scipy.sparse as sp

logger = logging.getLogger(__name__)

FETCH_SCRIPT = "scripts/flybrain_fetch_connectome.py"
PARQUET_PRE_COL = "Presynaptic_Index"
PARQUET_POST_COL = "Postsynaptic_Index"
PARQUET_WEIGHT_COL = "Excitatory x Connectivity"


class ConnectomeUnavailable(RuntimeError):
    """Raised when the FlyWire files are not on disk (or cannot be read)."""


def sha256_of_file(path: Union[str, Path], chunk_size: int = 1 << 20) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _ragged_ranges(starts: "np.ndarray", ends: "np.ndarray") -> "np.ndarray":
    """Concatenate ``arange(s, e)`` for every (s, e) pair without a Python loop."""
    import numpy as np

    lengths = ends - starts
    total = int(lengths.sum())
    if total == 0:
        return np.empty(0, dtype=np.int64)
    # Offset of each segment inside the concatenated output.
    seg_offsets = np.cumsum(lengths) - lengths
    return np.repeat(starts - seg_offsets, lengths) + np.arange(total, dtype=np.int64)


class Connectome:
    """Sparse FlyWire connectome: ``csc`` has shape ``(post, pre)``.

    ``csc[:, j]`` therefore lists the postsynaptic targets of presynaptic
    neuron ``j`` (column gather = event-driven propagation), and ``csr[i, :]``
    lists the presynaptic inputs of neuron ``i``.
    """

    def __init__(
        self,
        flywire_ids: "np.ndarray",
        csc: "sp.csc_matrix",
        data_dir: Optional[Path] = None,
        completeness_path: Optional[Path] = None,
        connectivity_path: Optional[Path] = None,
        source_sha256: Optional[str] = None,
        origin: str = "arrays",
    ) -> None:
        import numpy as np

        self.flywire_ids: "np.ndarray" = np.asarray(flywire_ids, dtype=np.int64)
        self.n_neurons: int = int(self.flywire_ids.shape[0])
        if csc.shape != (self.n_neurons, self.n_neurons):
            raise ValueError(
                f"connectivity shape {csc.shape} does not match {self.n_neurons} neurons"
            )
        self.csc = csc
        self.n_synapses: int = int(csc.nnz)
        self.id_to_index: Dict[int, int] = {
            int(fid): idx for idx, fid in enumerate(self.flywire_ids.tolist())
        }
        self.data_dir: Optional[Path] = Path(data_dir) if data_dir else None
        self.completeness_path = Path(completeness_path) if completeness_path else None
        self.connectivity_path = Path(connectivity_path) if connectivity_path else None
        self.source_sha256 = source_sha256
        self.origin = origin
        self._csr: Optional["sp.csr_matrix"] = None
        self._manifest: Optional[ConnectomeManifest] = None
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    @classmethod
    def from_arrays(
        cls,
        flywire_ids: Sequence[int],
        pre_idx: Sequence[int],
        post_idx: Sequence[int],
        weights: Sequence[float],
        **kwargs: Any,
    ) -> "Connectome":
        """Build a connectome from COO triplets (test fixtures, synthetic graphs).

        Duplicate ``(pre, post)`` pairs are summed, matching the behaviour of the
        upstream sparse construction.
        """
        import numpy as np
        import scipy.sparse as sp

        ids = np.asarray(flywire_ids, dtype=np.int64)
        n = int(ids.shape[0])
        pre = np.asarray(pre_idx, dtype=np.int64)
        post = np.asarray(post_idx, dtype=np.int64)
        w = np.asarray(weights, dtype=np.float32)
        if not (pre.shape == post.shape == w.shape):
            raise ValueError("pre_idx, post_idx and weights must have the same length")
        if pre.size and (pre.min() < 0 or pre.max() >= n or post.min() < 0 or post.max() >= n):
            raise ValueError("synapse indices out of range for the given neuron ids")
        csc = sp.csc_matrix((w, (post, pre)), shape=(n, n), dtype=np.float32)
        csc.sum_duplicates()
        csc.sort_indices()
        return cls(ids, csc, **kwargs)

    @classmethod
    def load(
        cls,
        source: Union[FlyBrainSettings, str, Path, None] = None,
    ) -> "Connectome":
        """Load from ``FlyBrainSettings`` or a data directory path.

        Order: npz (numpy only) → parquet (pyarrow or pandas, if importable) →
        :class:`ConnectomeUnavailable`.
        """
        import numpy as np
        import scipy.sparse as sp

        if source is None:
            settings = get_settings()
            data_dir = settings.data_dir
        elif isinstance(source, FlyBrainSettings):
            data_dir = source.data_dir
        else:
            data_dir = Path(source).expanduser()

        completeness = data_dir / COMPLETENESS_FILE
        npz_path = data_dir / CONNECTIVITY_NPZ
        parquet_path = data_dir / CONNECTIVITY_PARQUET

        if not completeness.is_file():
            raise ConnectomeUnavailable(
                f"FlyWire completeness file not found: {completeness}. "
                f"Fetch the FlyWire v783 release with `poetry run python {FETCH_SCRIPT} "
                f"--dest {data_dir}` and set FLYBRAIN_DATA_DIR."
            )

        flywire_ids = cls.read_completeness_ids(completeness)
        n = int(flywire_ids.shape[0])

        source_sha: Optional[str] = None
        if npz_path.is_file():
            pre, post, weight, n_npz, source_sha = cls._read_npz(npz_path)
            connectivity_path = npz_path
            if n_npz is not None and n_npz != n:
                raise ConnectomeUnavailable(
                    f"{npz_path.name} declares {n_npz} neurons but {completeness.name} "
                    f"lists {n}; the files do not belong to the same release."
                )
        elif parquet_path.is_file():
            pre, post, weight = cls._read_parquet(parquet_path)
            connectivity_path = parquet_path
        else:
            raise ConnectomeUnavailable(
                f"FlyWire connectivity not found in {data_dir} (expected {CONNECTIVITY_NPZ} "
                f"or {CONNECTIVITY_PARQUET}). Fetch and convert it with "
                f"`poetry run python {FETCH_SCRIPT} --dest {data_dir}`."
            )

        if pre.size and (pre.min() < 0 or pre.max() >= n or post.min() < 0 or post.max() >= n):
            raise ConnectomeUnavailable(
                f"{connectivity_path.name} references neuron indices outside 0..{n - 1}"
            )

        csc = sp.csc_matrix(
            (weight.astype(np.float32, copy=False), (post, pre)), shape=(n, n), dtype=np.float32
        )
        csc.sum_duplicates()
        csc.sort_indices()
        logger.info(
            "FlyBrain connectome loaded: %d neurons, %d synapses from %s",
            n,
            csc.nnz,
            connectivity_path,
        )
        return cls(
            flywire_ids,
            csc,
            data_dir=data_dir,
            completeness_path=completeness,
            connectivity_path=connectivity_path,
            source_sha256=source_sha,
            origin="disk",
        )

    @staticmethod
    def read_completeness_ids(path: Union[str, Path]) -> "np.ndarray":
        """Parse ``,Completed`` CSV (first column = FlyWire id) with numpy only."""
        import numpy as np

        ids = np.loadtxt(
            path, delimiter=",", skiprows=1, usecols=0, dtype=np.int64, ndmin=1, encoding="utf-8"
        )
        if ids.size == 0:
            raise ConnectomeUnavailable(f"completeness file {path} contains no neuron ids")
        return ids

    @staticmethod
    def _read_npz(
        path: Path,
    ) -> Tuple["np.ndarray", "np.ndarray", "np.ndarray", Optional[int], Optional[str]]:
        import numpy as np

        with np.load(path, allow_pickle=False) as archive:
            keys = set(archive.files)
            missing = {"pre", "post", "weight"} - keys
            if missing:
                raise ConnectomeUnavailable(
                    f"{path} lacks keys {sorted(missing)}; regenerate it with {FETCH_SCRIPT}"
                )
            pre = np.asarray(archive["pre"]).astype(np.int64, copy=False)
            post = np.asarray(archive["post"]).astype(np.int64, copy=False)
            weight = np.asarray(archive["weight"]).astype(np.float32, copy=False)
            n_npz = int(archive["n_neurons"]) if "n_neurons" in keys else None
            source_sha = str(archive["source_sha256"]) if "source_sha256" in keys else None
        return pre, post, weight, n_npz, source_sha or None

    @staticmethod
    def _read_parquet(path: Path) -> Tuple["np.ndarray", "np.ndarray", "np.ndarray"]:
        import numpy as np

        cols = [PARQUET_PRE_COL, PARQUET_POST_COL, PARQUET_WEIGHT_COL]
        try:
            import pyarrow.parquet as pq  # type: ignore

            table = pq.read_table(str(path), columns=cols)
            pre = table.column(PARQUET_PRE_COL).to_numpy()
            post = table.column(PARQUET_POST_COL).to_numpy()
            weight = table.column(PARQUET_WEIGHT_COL).to_numpy()
        except ImportError:
            try:
                import pandas as pd  # type: ignore
            except ImportError as exc:
                raise ConnectomeUnavailable(
                    f"{path.name} is present but neither pyarrow nor pandas is installed; "
                    f"convert it to {CONNECTIVITY_NPZ} with {FETCH_SCRIPT} on a host that has "
                    "pyarrow."
                ) from exc
            frame = pd.read_parquet(path, columns=cols)
            pre = frame[PARQUET_PRE_COL].to_numpy()
            post = frame[PARQUET_POST_COL].to_numpy()
            weight = frame[PARQUET_WEIGHT_COL].to_numpy()
        return (
            np.asarray(pre).astype(np.int64, copy=False),
            np.asarray(post).astype(np.int64, copy=False),
            np.asarray(weight).astype(np.float32, copy=False),
        )

    # ------------------------------------------------------------------
    # Views
    # ------------------------------------------------------------------

    @property
    def csr(self) -> "sp.csr_matrix":
        """Row-major view (post, pre): ``csr[i]`` = presynaptic inputs of ``i``."""
        if self._csr is None:
            with self._lock:
                if self._csr is None:
                    csr = self.csc.tocsr()
                    csr.sort_indices()
                    self._csr = csr
        return self._csr

    def index_of(self, flywire_id: int) -> Optional[int]:
        return self.id_to_index.get(int(flywire_id))

    def indices_for_ids(self, flywire_ids: Iterable[int]) -> Tuple[List[int], List[int]]:
        """Resolve ids → (indices, missing_ids); order preserved, nothing dropped silently."""
        found: List[int] = []
        missing: List[int] = []
        for fid in flywire_ids:
            idx = self.id_to_index.get(int(fid))
            if idx is None:
                missing.append(int(fid))
            else:
                found.append(idx)
        return found, missing

    def ids_for_indices(self, indices: Sequence[int]) -> List[int]:
        import numpy as np

        if len(indices) == 0:
            return []
        return self.flywire_ids[np.asarray(indices, dtype=np.int64)].tolist()

    def downstream(self, indices: Sequence[int], min_weight: float = 0.0) -> "np.ndarray":
        """Postsynaptic partners of ``indices`` with ``|w| >= min_weight`` (sorted, unique)."""
        return self._neighbors(self.csc, indices, min_weight)

    def upstream(self, indices: Sequence[int], min_weight: float = 0.0) -> "np.ndarray":
        """Presynaptic partners of ``indices`` with ``|w| >= min_weight`` (sorted, unique)."""
        return self._neighbors(self.csr, indices, min_weight)

    @staticmethod
    def _neighbors(matrix: Any, indices: Sequence[int], min_weight: float) -> "np.ndarray":
        import numpy as np

        idx = np.unique(np.asarray(indices, dtype=np.int64))
        if idx.size == 0:
            return np.empty(0, dtype=np.int64)
        starts = matrix.indptr[idx]
        ends = matrix.indptr[idx + 1]
        offs = _ragged_ranges(starts, ends)
        if offs.size == 0:
            return np.empty(0, dtype=np.int64)
        targets = matrix.indices[offs]
        if min_weight > 0:
            keep = np.abs(matrix.data[offs]) >= min_weight
            targets = targets[keep]
        return np.unique(targets).astype(np.int64)

    # ------------------------------------------------------------------
    # Subgraph
    # ------------------------------------------------------------------

    def subgraph(
        self,
        seed_indices: Sequence[int],
        hops: int = 2,
        min_weight: float = 1.0,
        max_neurons: int = 20000,
    ) -> Tuple["sp.csc_matrix", "np.ndarray"]:
        """Induced sub-matrix around ``seed_indices``.

        Neurons within ``hops`` synaptic steps (forward and backward) of the
        seeds, traversing only synapses with ``|w| >= min_weight``. If more
        than ``max_neurons`` are found the seeds are always kept and the rest is
        ranked by total ``|w|`` (in + out) inside the candidate set. Returns
        ``(local_csc, local_to_global)`` where ``local_csc`` is the induced
        ``(post, pre)`` matrix over the kept neurons (all synapses between kept
        neurons are retained) and ``local_to_global[k]`` is the global index of
        local neuron ``k``.
        """
        import numpy as np

        seeds = np.unique(np.asarray(seed_indices, dtype=np.int64))
        if seeds.size and (seeds.min() < 0 or seeds.max() >= self.n_neurons):
            raise ValueError("seed indices out of range")
        if max_neurons < 1:
            raise ValueError("max_neurons must be >= 1")

        keep = seeds.copy()
        frontier = seeds.copy()
        for _ in range(max(0, int(hops))):
            if frontier.size == 0:
                break
            down = self.downstream(frontier, min_weight)
            up = self.upstream(frontier, min_weight)
            neighbours = np.union1d(down, up)
            new = np.setdiff1d(neighbours, keep, assume_unique=True)
            keep = np.union1d(keep, new)
            frontier = new

        if keep.size > max_neurons:
            candidate_csc = self.csc[:, keep]
            in_mass = np.asarray(abs(candidate_csc).sum(axis=0)).ravel()  # per pre (column)
            out_mass = np.asarray(abs(self.csr[keep, :]).sum(axis=1)).ravel()  # per post (row)
            mass = in_mass + out_mass
            is_seed = np.isin(keep, seeds)
            n_free = max(0, max_neurons - int(is_seed.sum()))
            free_positions = np.flatnonzero(~is_seed)
            order = free_positions[np.argsort(-mass[free_positions], kind="stable")][:n_free]
            chosen = np.union1d(keep[is_seed], keep[order])
            keep = chosen

        local_to_global = np.sort(keep).astype(np.int64)
        local_csc = self.csc[local_to_global, :][:, local_to_global].tocsc()
        local_csc.sort_indices()
        return local_csc, local_to_global

    # ------------------------------------------------------------------
    # Manifest
    # ------------------------------------------------------------------

    def manifest(self, verify: bool = True) -> ConnectomeManifest:
        """Describe the loaded connectome; hashes on-disk files when they exist."""
        if self._manifest is not None:
            return self._manifest

        sha: Dict[str, str] = {}
        sha_ok: Optional[bool] = None
        notes: List[str] = []

        if self.origin == "disk" and verify:
            checks: List[bool] = []
            if self.completeness_path and self.completeness_path.is_file():
                digest = sha256_of_file(self.completeness_path)
                sha[self.completeness_path.name] = digest
                expected = KNOWN_SHA256.get(self.completeness_path.name)
                if expected:
                    checks.append(digest == expected)
            if self.connectivity_path and self.connectivity_path.is_file():
                digest = sha256_of_file(self.connectivity_path)
                sha[self.connectivity_path.name] = digest
                expected = KNOWN_SHA256.get(self.connectivity_path.name)
                if expected:
                    checks.append(digest == expected)
                elif self.connectivity_path.name == CONNECTIVITY_NPZ:
                    known_parquet = KNOWN_SHA256.get(CONNECTIVITY_PARQUET)
                    if self.source_sha256:
                        sha[f"{CONNECTIVITY_PARQUET} (npz source)"] = self.source_sha256
                        if known_parquet:
                            checks.append(self.source_sha256 == known_parquet)
                    else:
                        notes.append("npz carries no source_sha256; parquet provenance unverified")
            sha_ok = all(checks) if checks else None
            if sha_ok is False:
                notes.append("SHA-256 mismatch against KNOWN_SHA256 (config.py)")
        elif self.origin != "disk":
            notes.append(f"in-memory connectome ({self.origin}); no files to verify")

        self._manifest = ConnectomeManifest(
            loaded=True,
            data_dir=str(self.data_dir) if self.data_dir else None,
            completeness_path=str(self.completeness_path) if self.completeness_path else None,
            connectivity_path=str(self.connectivity_path) if self.connectivity_path else None,
            n_neurons=self.n_neurons,
            n_synapses=self.n_synapses,
            sha256_ok=sha_ok,
            sha256=sha,
            reason="; ".join(notes),
        )
        return self._manifest

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return (
            f"Connectome(n_neurons={self.n_neurons}, n_synapses={self.n_synapses}, "
            f"origin={self.origin!r})"
        )


def unavailable_manifest(reason: str, data_dir: Optional[Path] = None) -> ConnectomeManifest:
    """Manifest for the 'nothing on disk' case (health endpoints)."""
    return ConnectomeManifest(
        loaded=False, data_dir=str(data_dir) if data_dir else None, reason=reason
    )


# ----------------------------------------------------------------------
# Process-wide cache
# ----------------------------------------------------------------------

_CACHE_LOCK = threading.Lock()
_CACHED: Optional[Connectome] = None
_CACHED_DIR: Optional[Path] = None
_PINNED = False  # True when installed explicitly via set_cached_connectome()


def get_connectome(settings: Optional[FlyBrainSettings] = None) -> Connectome:
    """Return the process-wide cached :class:`Connectome`, loading it once.

    Failures are not cached, so a connectome fetched after start-up is picked up
    on the next call. Raises :class:`ConnectomeUnavailable` when missing. A
    connectome installed with :func:`set_cached_connectome` is returned as-is.
    """
    global _CACHED, _CACHED_DIR
    settings = settings or get_settings()
    data_dir = Path(settings.data_dir)
    with _CACHE_LOCK:
        if _CACHED is not None and (_PINNED or _CACHED_DIR == data_dir):
            return _CACHED
        connectome = Connectome.load(settings)
        _CACHED = connectome
        _CACHED_DIR = data_dir
        return connectome


def set_cached_connectome(connectome: Optional[Connectome]) -> None:
    """Install (or clear) the cached connectome. Tests use this with a synthetic fixture."""
    global _CACHED, _CACHED_DIR, _PINNED
    with _CACHE_LOCK:
        _CACHED = connectome
        _CACHED_DIR = connectome.data_dir if connectome is not None else None
        _PINNED = connectome is not None


def reset_connectome_cache() -> None:
    set_cached_connectome(None)


def connectome_available(settings: Optional[FlyBrainSettings] = None) -> Tuple[bool, str]:
    """Cheap on-disk check (no loading) for health endpoints."""
    settings = settings or get_settings()
    data_dir = Path(settings.data_dir)
    completeness = data_dir / COMPLETENESS_FILE
    if not completeness.is_file():
        return False, f"{COMPLETENESS_FILE} missing from {data_dir}; run {FETCH_SCRIPT}"
    if (data_dir / CONNECTIVITY_NPZ).is_file() or (data_dir / CONNECTIVITY_PARQUET).is_file():
        return True, ""
    return False, f"no {CONNECTIVITY_NPZ}/{CONNECTIVITY_PARQUET} in {data_dir}; run {FETCH_SCRIPT}"


__all__ = [
    "Connectome",
    "ConnectomeUnavailable",
    "FETCH_SCRIPT",
    "connectome_available",
    "get_connectome",
    "reset_connectome_cache",
    "set_cached_connectome",
    "sha256_of_file",
    "unavailable_manifest",
]
