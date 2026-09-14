"""FlyBrain atlas (spec §5): named neuron groups from ``config/flybrain_atlas.yaml``.

* ``groups``: name → role / description / flywire_ids, resolved to connectome
  indices. Ids absent from the completeness file are recorded in
  ``missing_ids`` — never silently dropped, never an exception.
* ``derived``: groups computed against the loaded connectome
  (``downstream_of`` seed groups, ``hops``, ``min_weight``, ``exclude``,
  ``intersection``).
* ``sensorimotor``: ``inputs`` (forward/left/right/attract → groups) and
  ``readouts`` (forward/turn_left/turn_right/feeding → groups).

The atlas also works without a connectome (indices empty,
``connectome_loaded=False``) so health/atlas endpoints can describe the
configuration honestly before the FlyWire files are fetched.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, Iterable, List, Optional, Sequence, Set, Union

from mycosoft_mas.flybrain.config import get_settings
from mycosoft_mas.flybrain.schemas import AtlasSummary, NeuronGroup

if TYPE_CHECKING:  # pragma: no cover - typing only
    from mycosoft_mas.flybrain.connectome import Connectome

logger = logging.getLogger(__name__)

VALID_ROLES = {"sensory", "motor", "interneuron", "custom"}
SENSORIMOTOR_INPUT_KEYS = ("forward", "left", "right", "attract")
SENSORIMOTOR_READOUT_KEYS = ("forward", "turn_left", "turn_right", "feeding")


class AtlasError(ValueError):
    """Malformed atlas YAML."""


def _as_role(value: Any) -> str:
    role = str(value or "custom").strip().lower()
    return role if role in VALID_ROLES else "custom"


def _as_int_list(values: Any, context: str) -> List[int]:
    if values is None:
        return []
    if not isinstance(values, (list, tuple)):
        raise AtlasError(f"{context}: flywire_ids must be a list")
    out: List[int] = []
    for v in values:
        try:
            out.append(int(v))
        except (TypeError, ValueError) as exc:
            raise AtlasError(f"{context}: non-integer flywire id {v!r}") from exc
    return out


def _as_name_list(values: Any, context: str) -> List[str]:
    if values is None:
        return []
    if isinstance(values, str):
        return [values]
    if not isinstance(values, (list, tuple)):
        raise AtlasError(f"{context}: expected a list of group names")
    return [str(v) for v in values]


def load_atlas_yaml(path: Union[str, Path, None] = None) -> Dict[str, Any]:
    """Read the atlas YAML into a plain dict (PyYAML, safe_load)."""
    import yaml

    atlas_path = Path(path) if path else get_settings().atlas_path
    with open(atlas_path, "r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle) or {}
    if not isinstance(raw, dict):
        raise AtlasError(f"{atlas_path}: top level must be a mapping")
    raw.setdefault("_path", str(atlas_path))
    return raw


class Atlas:
    """Resolved neuron groups plus the sensorimotor mapping."""

    def __init__(
        self,
        groups: Dict[str, NeuronGroup],
        sensorimotor: Dict[str, Any],
        source: Optional[Dict[str, Any]] = None,
        schema_version: str = "flybrain.atlas/v1",
        path: Optional[str] = None,
        connectome: Optional["Connectome"] = None,
        derived_specs: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> None:
        self.groups: Dict[str, NeuronGroup] = groups
        self.sensorimotor: Dict[str, Any] = sensorimotor
        self.source: Dict[str, Any] = dict(source or {})
        self.schema_version = schema_version
        self.path = path
        self.connectome = connectome
        self.derived_specs: Dict[str, Dict[str, Any]] = dict(derived_specs or {})

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    @classmethod
    def load(
        cls,
        path: Union[str, Path, None] = None,
        connectome: Optional["Connectome"] = None,
    ) -> "Atlas":
        raw = load_atlas_yaml(path)
        return cls.from_dict(raw, connectome=connectome)

    @classmethod
    def from_dict(cls, raw: Dict[str, Any], connectome: Optional["Connectome"] = None) -> "Atlas":
        groups_raw = raw.get("groups") or {}
        derived_raw = raw.get("derived") or {}
        sensorimotor_raw = raw.get("sensorimotor") or {}
        if not isinstance(groups_raw, dict) or not isinstance(derived_raw, dict):
            raise AtlasError("atlas 'groups' and 'derived' must be mappings")

        groups: Dict[str, NeuronGroup] = {}
        for name, spec in groups_raw.items():
            spec = spec or {}
            if not isinstance(spec, dict):
                raise AtlasError(f"group {name}: expected a mapping")
            ids = _as_int_list(spec.get("flywire_ids"), f"group {name}")
            indices: List[int] = []
            missing: List[int] = []
            if connectome is not None:
                found, missing = connectome.indices_for_ids(ids)
                # unique, sorted, stable for downstream consumers
                indices = sorted(set(found))
            groups[str(name)] = NeuronGroup(
                name=str(name),
                role=_as_role(spec.get("role")),
                description=str(spec.get("description") or ""),
                flywire_ids=ids,
                indices=indices,
                derived=False,
                missing_ids=missing,
            )

        derived_specs: Dict[str, Dict[str, Any]] = {}
        for name, spec in derived_raw.items():
            spec = spec or {}
            if not isinstance(spec, dict):
                raise AtlasError(f"derived group {name}: expected a mapping")
            derived_specs[str(name)] = dict(spec)

        atlas = cls(
            groups=groups,
            sensorimotor=cls._normalise_sensorimotor(sensorimotor_raw),
            source=raw.get("source") or {},
            schema_version=str(raw.get("schema_version") or "flybrain.atlas/v1"),
            path=raw.get("_path"),
            connectome=connectome,
            derived_specs=derived_specs,
        )
        atlas._compute_derived()
        return atlas

    @staticmethod
    def _normalise_sensorimotor(raw: Any) -> Dict[str, Any]:
        raw = raw if isinstance(raw, dict) else {}
        inputs_raw = raw.get("inputs") or {}
        readouts_raw = raw.get("readouts") or {}
        inputs = {
            str(k): _as_name_list(v, f"sensorimotor.inputs.{k}")
            for k, v in (inputs_raw.items() if isinstance(inputs_raw, dict) else [])
        }
        readouts = {
            str(k): _as_name_list(v, f"sensorimotor.readouts.{k}")
            for k, v in (readouts_raw.items() if isinstance(readouts_raw, dict) else [])
        }
        return {
            "note": str(raw.get("note") or ""),
            "inputs": inputs,
            "readouts": readouts,
        }

    # ------------------------------------------------------------------
    # Derived groups
    # ------------------------------------------------------------------

    def _compute_derived(self) -> None:
        """Compute ``derived`` groups in declaration order (later may reference earlier)."""
        for name, spec in self.derived_specs.items():
            try:
                group = self._derive_group(name, spec)
            except AtlasError:
                raise
            except Exception as exc:  # pragma: no cover - defensive
                logger.warning("FlyBrain atlas: derived group %s failed: %s", name, exc)
                group = NeuronGroup(
                    name=name,
                    role=_as_role(spec.get("role")),
                    description=str(spec.get("description") or ""),
                    derived=True,
                )
            self.groups[name] = group

    def _derive_group(self, name: str, spec: Dict[str, Any]) -> NeuronGroup:
        seeds = _as_name_list(spec.get("downstream_of"), f"derived {name}.downstream_of")
        hops = int(spec.get("hops", 1) or 0)
        min_weight = float(spec.get("min_weight", 0.0) or 0.0)
        exclude = _as_name_list(spec.get("exclude"), f"derived {name}.exclude")
        intersection = bool(spec.get("intersection", False))
        role = _as_role(spec.get("role"))
        description = str(spec.get("description") or "")

        for ref in list(seeds) + list(exclude):
            if ref not in self.groups:
                raise AtlasError(f"derived group {name} references unknown group {ref!r}")

        indices: List[int] = []
        flywire_ids: List[int] = []
        if self.connectome is not None and hops >= 0:
            import numpy as np

            per_seed: List[Set[int]] = []
            for seed_name in seeds:
                seed_idx = self.groups[seed_name].indices
                reach = self._downstream_hops(seed_idx, hops, min_weight)
                per_seed.append(set(int(i) for i in reach))
            if per_seed:
                if intersection:
                    result = set.intersection(*per_seed)
                else:
                    result = set.union(*per_seed)
            else:
                result = set()
            for ex_name in exclude:
                result.difference_update(self.groups[ex_name].indices)
            indices = sorted(result)
            if indices:
                flywire_ids = self.connectome.flywire_ids[
                    np.asarray(indices, dtype=np.int64)
                ].tolist()

        return NeuronGroup(
            name=name,
            role=role,
            description=description,
            flywire_ids=flywire_ids,
            indices=indices,
            derived=True,
            missing_ids=[],
        )

    def _downstream_hops(
        self, seed_idx: Sequence[int], hops: int, min_weight: float
    ) -> "np.ndarray":
        """Neurons reachable in exactly 1..hops forward steps (excluding the seeds
        themselves unless they are reached through a synapse)."""
        import numpy as np

        assert self.connectome is not None
        if hops <= 0 or len(seed_idx) == 0:
            return np.empty(0, dtype=np.int64)
        reached = np.empty(0, dtype=np.int64)
        frontier = np.asarray(seed_idx, dtype=np.int64)
        for _ in range(hops):
            nxt = self.connectome.downstream(frontier, min_weight)
            new = np.setdiff1d(nxt, reached, assume_unique=True)
            reached = np.union1d(reached, new)
            frontier = new
            if frontier.size == 0:
                break
        return reached

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    @property
    def connectome_loaded(self) -> bool:
        return self.connectome is not None

    def group(self, name: str) -> NeuronGroup:
        try:
            return self.groups[name]
        except KeyError as exc:
            raise KeyError(f"unknown atlas group {name!r}") from exc

    def has_group(self, name: str) -> bool:
        return name in self.groups

    def names(self) -> List[str]:
        return list(self.groups.keys())

    def indices(self, names: Union[str, Iterable[str]]) -> List[int]:
        """Union of connectome indices for the named groups (sorted, unique)."""
        if isinstance(names, str):
            names = [names]
        out: Set[int] = set()
        for n in names:
            out.update(self.group(n).indices)
        return sorted(out)

    def missing_ids(self, names: Union[str, Iterable[str], None] = None) -> Dict[str, List[int]]:
        if names is None:
            names = self.groups.keys()
        elif isinstance(names, str):
            names = [names]
        return {n: list(self.group(n).missing_ids) for n in names if self.group(n).missing_ids}

    def input_groups(self, key: str) -> List[str]:
        return list(self.sensorimotor.get("inputs", {}).get(key, []))

    def readout_groups(self, key: str) -> List[str]:
        return list(self.sensorimotor.get("readouts", {}).get(key, []))

    def input_indices(self, key: str) -> List[int]:
        return self.indices(self.input_groups(key))

    def readout_indices(self, key: str) -> List[int]:
        return self.indices(self.readout_groups(key))

    def group_of_index(self, index: int) -> List[str]:
        """Names of every group that contains a connectome index."""
        return [name for name, g in self.groups.items() if index in g.indices]

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------

    def group_summary(self, group: NeuronGroup) -> Dict[str, Any]:
        return {
            "name": group.name,
            "role": group.role,
            "description": group.description,
            "derived": group.derived,
            "n_ids": len(group.flywire_ids),
            "size": len(group.indices),
            "n_missing": len(group.missing_ids),
            "missing_ids": list(group.missing_ids),
        }

    def summary(self) -> AtlasSummary:
        unresolved_refs: List[str] = []
        for section in ("inputs", "readouts"):
            for key, names in self.sensorimotor.get(section, {}).items():
                for n in names:
                    if n not in self.groups:
                        unresolved_refs.append(f"{section}.{key}:{n}")
        sensorimotor = {
            "note": self.sensorimotor.get("note", ""),
            "inputs": {
                k: {"groups": v, "size": len(self._safe_indices(v))}
                for k, v in self.sensorimotor.get("inputs", {}).items()
            },
            "readouts": {
                k: {"groups": v, "size": len(self._safe_indices(v))}
                for k, v in self.sensorimotor.get("readouts", {}).items()
            },
            "unresolved_group_refs": unresolved_refs,
        }
        source = dict(self.source)
        if self.path:
            source["atlas_path"] = self.path
        source["n_groups"] = len(self.groups)
        source["n_derived"] = sum(1 for g in self.groups.values() if g.derived)
        source["total_missing_ids"] = sum(len(g.missing_ids) for g in self.groups.values())
        return AtlasSummary(
            schema_version=self.schema_version,
            source=source,
            groups=[self.group_summary(g) for g in self.groups.values()],
            sensorimotor=sensorimotor,
            connectome_loaded=self.connectome is not None,
        )

    def _safe_indices(self, names: Iterable[str]) -> List[int]:
        out: Set[int] = set()
        for n in names:
            g = self.groups.get(n)
            if g is not None:
                out.update(g.indices)
        return sorted(out)

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return (
            f"Atlas(groups={len(self.groups)}, connectome_loaded={self.connectome is not None}, "
            f"path={self.path!r})"
        )


__all__ = ["Atlas", "AtlasError", "load_atlas_yaml"]
