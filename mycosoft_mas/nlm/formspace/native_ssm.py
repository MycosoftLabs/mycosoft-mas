"""Native tied-A rank-1 SSM arithmetic from the SEP10 packet blueprint.

These functions are the archived FormSpace family, not Mamba-1 and not Ollama.
They do not emit Fusarium ecology p.
"""

from __future__ import annotations

import math
from typing import Iterable, List, Sequence, Tuple


def softplus(x: float) -> float:
    return max(x, 0.0) + math.log1p(math.exp(-abs(x)))


def inverse_softplus(y: float) -> float:
    if y <= 0:
        raise ValueError("Positive target required")
    return y + math.log(-math.expm1(-y))


def native_scan(
    inputs: Sequence[float],
    dt: float,
    a: float,
    b: float,
    h: float = 0.0,
) -> Tuple[List[float], float]:
    output: List[float] = []
    state = h
    for x in inputs:
        state = math.exp(dt * a) * state + dt * b * x
        output.append(state)
    return output, state


def count_native(d: int, inner: int, state: int, conv: int) -> int:
    return 3 * d * inner + inner * conv + 5 * inner + 2 * state * inner + state + 2 * d


def count_mamba1(d: int, inner: int, state: int, rank: int, conv: int) -> int:
    return (
        3 * d * inner
        + inner * conv
        + 3 * inner
        + inner * (2 * state + rank)
        + rank * inner
        + inner * state
    )


def inverse_variance_fusion(
    means: Sequence[float],
    variances: Sequence[float],
) -> Tuple[float, float]:
    if len(means) != len(variances) or not means:
        raise ValueError("means and variances must be nonempty and aligned")
    weights = [1.0 / v for v in variances]
    denom = sum(weights)
    fused_mean = sum(m * w for m, w in zip(means, weights)) / denom
    fused_var = 1.0 / denom
    return fused_mean, fused_var


def hazard_cumulative(hazards: Iterable[float]) -> float:
    survive = 1.0
    for h in hazards:
        survive *= 1.0 - h
    return 1.0 - survive
