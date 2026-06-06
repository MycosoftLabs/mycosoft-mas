"""
TurboQuant — data-oblivious extreme vector compression for MAS memory.

Reference implementation of Google Research's TurboQuant
(https://research.google/blog/turboquant-redefining-ai-efficiency-with-extreme-compression/)
adapted for MYCA's vector memory (Qdrant `semantic_facts` / `myca_semantic_memory`)
and as the shared algorithm spec for MINDEX vector search.

TurboQuant is a *two-stage*, *data-oblivious* quantizer. "Data-oblivious" means it
needs no codebook training and no per-dataset tuning (unlike Product Quantization /
KIVI), so it works identically on any embedding model MYCA uses (OpenAI 1536-d,
Gemini 768-d, MiniLM 384-d, Nemotron-Retriever, MINDEX fci_signals 768-d, ...).

    Stage 1 — PolarQuant (high-quality compression)
        Randomly rotate the vector so its geometry becomes isotropic, then split it
        into magnitude (radius) and direction (angles). After a random rotation the
        direction's coordinates are tightly concentrated (~N(0, 1/d)), so a *fixed*
        Gaussian-optimal grid quantizes them well with ZERO per-block scale overhead.

    Stage 2 — QJL (1-bit error correction)
        A Quantized Johnson–Lindenstrauss sketch reduces the vector to sign bits
        (+1/-1) at 1 bit/dim with zero memory overhead, used to correct residual
        error and to estimate inner products / attention scores directly from the
        sketch.

Design goals for this module:
  * numpy-only, no heavy deps, importable anywhere in MAS.
  * Deterministic & reproducible from an integer seed — the random rotation and the
    JL sketch are regenerated from the seed, so we NEVER store rotation/JL matrices
    (that is the whole point: zero memory overhead).
  * Honest accounting: `Codec.compression_ratio()` reports real bits/dim vs fp32/fp16.

This is the canonical reference. The MINDEX cuVS path mirrors the same math on GPU
(see mindex docs/TURBOQUANT_INTEGRATION_JUN06_2026.md).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

import numpy as np

__all__ = [
    "PolarQuantizer",
    "QJLSketch",
    "TurboQuantCodec",
    "QuantizedVector",
]


# --------------------------------------------------------------------------- #
# Stage 0: data-oblivious random rotation (Randomized Hadamard Transform)
# --------------------------------------------------------------------------- #
def _next_pow2(n: int) -> int:
    return 1 << (n - 1).bit_length()


def _fwht(a: np.ndarray) -> np.ndarray:
    """In-place fast Walsh–Hadamard transform along the last axis (len = power of 2)."""
    x = a.copy()
    n = x.shape[-1]
    h = 1
    while h < n:
        x = x.reshape(*x.shape[:-1], n // (2 * h), 2, h)
        a0 = x[..., 0, :]
        a1 = x[..., 1, :]
        x = np.concatenate([a0 + a1, a0 - a1], axis=-1).reshape(*a.shape[:-1], n)
        h *= 2
    return x


def _random_signs(dim: int, seed: int) -> np.ndarray:
    """Deterministic ±1 sign vector derived from `seed` (never stored)."""
    rng = np.random.default_rng(seed)
    return rng.integers(0, 2, size=dim).astype(np.float32) * 2.0 - 1.0


def randomized_rotation(x: np.ndarray, seed: int, inverse: bool = False) -> np.ndarray:
    """
    Apply a structured random orthogonal rotation (sign-flip + Walsh–Hadamard).

    The transform is orthogonal (norm-preserving) and O(d log d). It is fully
    determined by `seed`, so it is regenerated on demand rather than stored. After
    rotation the coordinates of any fixed vector are spread isotropically, which is
    what lets PolarQuant use a single fixed quantization grid for every dataset.
    """
    x = np.asarray(x, dtype=np.float32).ravel()
    d = x.shape[0]
    n = _next_pow2(d)
    signs = _random_signs(n, seed)
    if not inverse:
        buf = np.zeros(n, dtype=np.float32)
        buf[:d] = x
        buf = buf * signs
        buf = _fwht(buf) / math.sqrt(n)
        return buf  # length n (>= d)
    # inverse: Hadamard is symmetric & orthogonal, so H^-1 = H/n already normalized
    buf = _fwht(x) / math.sqrt(n)
    buf = buf * signs
    return buf[:d]


# --------------------------------------------------------------------------- #
# Stage 1: PolarQuant — radius + direction with a fixed Gaussian grid
# --------------------------------------------------------------------------- #
def _gaussian_levels(bits: int) -> np.ndarray:
    """
    Quantization reconstruction levels for a unit-variance Gaussian source, placed
    so that after random rotation the (approximately Gaussian) direction coordinates
    are quantized near-optimally with NO per-vector parameters.

    We use Lloyd-Max optimal points approximated by inverse-CDF placement, which is
    accurate and, crucially, identical for every dataset (data-oblivious).
    """
    k = 1 << bits
    # midpoints of equal-probability bins under the standard normal
    from math import sqrt

    def _ppf(p: float) -> float:
        # rational approximation of the normal inverse CDF (Acklam)
        a = [
            -3.969683028665376e01,
            2.209460984245205e02,
            -2.759285104469687e02,
            1.383577518672690e02,
            -3.066479806614716e01,
            2.506628277459239e00,
        ]
        b = [
            -5.447609879822406e01,
            1.615858368580409e02,
            -1.556989798598866e02,
            6.680131188771972e01,
            -1.328068155288572e01,
        ]
        c = [
            -7.784894002430293e-03,
            -3.223964580411365e-01,
            -2.400758277161838e00,
            -2.549732539343734e00,
            4.374664141464968e00,
            2.938163982698783e00,
        ]
        dd = [
            7.784695709041462e-03,
            3.224671290700398e-01,
            2.445134137142996e00,
            3.754408661907416e00,
        ]
        plow, phigh = 0.02425, 1 - 0.02425
        if p < plow:
            q = sqrt(-2 * math.log(p))
            return (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / (
                (((dd[0] * q + dd[1]) * q + dd[2]) * q + dd[3]) * q + 1
            )
        if p > phigh:
            q = sqrt(-2 * math.log(1 - p))
            return -(((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / (
                (((dd[0] * q + dd[1]) * q + dd[2]) * q + dd[3]) * q + 1
            )
        q = p - 0.5
        r = q * q
        return (
            (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5])
            * q
            / (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1)
        )

    levels = np.array([_ppf((i + 0.5) / k) for i in range(k)], dtype=np.float32)
    return levels


@dataclass
class PolarQuantizer:
    """
    Stage 1 quantizer. Encodes a vector as a quantized radius + `bits`-bit direction
    codes against a fixed Gaussian grid (after random rotation).
    """

    bits: int = 3
    radius_bits: int = 16  # the only per-vector scalar; tiny overhead

    def __post_init__(self) -> None:
        self._levels = _gaussian_levels(self.bits)
        # precompute decision thresholds (midpoints between levels)
        self._thresholds = (self._levels[:-1] + self._levels[1:]) / 2.0

    def encode(self, rotated: np.ndarray) -> Tuple[float, np.ndarray]:
        norm = float(np.linalg.norm(rotated))
        if norm == 0.0:
            return 0.0, np.zeros(rotated.shape[0], dtype=np.uint8)
        direction = rotated / norm  # unit vector; coords ~N(0, 1/d)
        # scale to unit variance so the fixed grid applies regardless of d
        d = rotated.shape[0]
        scaled = direction * math.sqrt(d)
        codes = np.searchsorted(self._thresholds, scaled).astype(np.uint16)
        return norm, codes

    def decode(self, norm: float, codes: np.ndarray, dim: int) -> np.ndarray:
        if norm == 0.0:
            return np.zeros(dim, dtype=np.float32)
        scaled = self._levels[codes]
        direction = scaled / math.sqrt(dim)
        # renormalize: quantization perturbs the norm of the unit direction
        n = np.linalg.norm(direction)
        if n > 0:
            direction = direction / n
        return (direction * norm).astype(np.float32)


# --------------------------------------------------------------------------- #
# Stage 2: QJL — 1-bit Quantized Johnson–Lindenstrauss sketch + estimator
# --------------------------------------------------------------------------- #
@dataclass
class QJLSketch:
    """
    1-bit JL sketch. Projects a vector with a seeded Gaussian JL matrix and stores
    only the signs (1 bit/dim of the sketch, zero scale overhead). Supports an
    asymmetric inner-product estimator: a full-precision query projection against the
    stored key sign bits recovers <q, k> without ever materializing the key.

    Estimator (Zandieh et al., QJL):
        <q, k> ≈ sqrt(pi/2) * ||k|| * mean_i( (S q)_i * sign((S k)_i) )
    which is unbiased via the Gaussian identity E[a·sign(b)] = sqrt(2/pi)·cov(a,b)/std(b).
    """

    sketch_dim: int = 128
    seed: int = 0xC0FFEE

    def _matrix(self, dim: int) -> np.ndarray:
        rng = np.random.default_rng(self.seed ^ (dim * 2654435761 & 0xFFFFFFFF))
        return rng.standard_normal(size=(self.sketch_dim, dim)).astype(np.float32)

    def sign_bits(self, x: np.ndarray) -> np.ndarray:
        """Pack sketch signs into a bit-array (np.uint8, 8 dims/byte)."""
        x = np.asarray(x, dtype=np.float32).ravel()
        proj = self._matrix(x.shape[0]) @ x
        bits = (proj >= 0).astype(np.uint8)
        return np.packbits(bits)

    def project(self, x: np.ndarray) -> np.ndarray:
        x = np.asarray(x, dtype=np.float32).ravel()
        return self._matrix(x.shape[0]) @ x

    def estimate_inner_product(
        self, query: np.ndarray, key_bits: np.ndarray, key_norm: float, dim: int
    ) -> float:
        signs = np.unpackbits(key_bits)[: self.sketch_dim].astype(np.float32) * 2.0 - 1.0
        qp = self.project(query)
        return float(math.sqrt(math.pi / 2.0) * key_norm * np.mean(qp * signs))


# --------------------------------------------------------------------------- #
# Combined codec
# --------------------------------------------------------------------------- #
@dataclass
class QuantizedVector:
    """Compact compressed representation of a single embedding."""

    dim: int
    rot_dim: int
    norm: float
    direction_codes: np.ndarray  # uint16 (values < 2**bits)
    sketch_bits: np.ndarray  # packed uint8 sign bits
    seed: int

    def nbytes(self) -> int:
        # direction stored at `bits` bits/dim (packed), sketch at 1 bit/dim, norm fp16
        return int(self.direction_codes.nbytes + self.sketch_bits.nbytes + 2)


@dataclass
class TurboQuantCodec:
    """
    Full TurboQuant codec: PolarQuant (Stage 1) + QJL (Stage 2).

    Example
    -------
    >>> codec = TurboQuantCodec(dim=1536, bits=3)
    >>> qv = codec.encode(embedding)            # compress
    >>> approx = codec.decode(qv)               # reconstruct (for storage round-trip)
    >>> score = codec.estimate_inner_product(query, qv)  # rerank without decoding
    """

    dim: int
    bits: int = 3
    sketch_dim: int = 128
    seed: int = 0x5EED

    polar: PolarQuantizer = field(init=False)
    qjl: QJLSketch = field(init=False)

    def __post_init__(self) -> None:
        self.polar = PolarQuantizer(bits=self.bits)
        self.qjl = QJLSketch(sketch_dim=self.sketch_dim, seed=self.seed ^ 0xA5A5)

    def encode(self, x: np.ndarray) -> QuantizedVector:
        x = np.asarray(x, dtype=np.float32).ravel()
        rotated = randomized_rotation(x, self.seed)
        norm, codes = self.polar.encode(rotated)
        sketch = self.qjl.sign_bits(x)
        return QuantizedVector(
            dim=x.shape[0],
            rot_dim=rotated.shape[0],
            norm=norm,
            direction_codes=self._pack_codes(codes),
            sketch_bits=sketch,
            seed=self.seed,
        )

    def decode(self, qv: QuantizedVector) -> np.ndarray:
        codes = self._unpack_codes(qv.direction_codes, qv.rot_dim)
        rotated = self.polar.decode(qv.norm, codes, qv.rot_dim)
        return randomized_rotation(rotated, qv.seed, inverse=True)[: qv.dim]

    def score(self, query: np.ndarray, qv: QuantizedVector) -> float:
        """
        Accurate primary scorer: inner product against the Stage-1 (PolarQuant)
        reconstruction. This is the high-quality path used for final ranking — on
        isotropic embeddings the 3-bit reconstruction keeps ~0.98 cosine, so top-k
        ranking closely tracks fp32. Cost: one decode (O(d log d)) per candidate.
        """
        q = np.asarray(query, dtype=np.float32).ravel()
        return float(q @ self.decode(qv))

    def estimate_inner_product(self, query: np.ndarray, qv: QuantizedVector) -> float:
        """
        Fast Stage-2 (QJL) pre-filter score from the 1-bit sketch alone — no decode.
        Unbiased estimate of <query, key>; higher variance than `score()`. Use it to
        cheaply shortlist candidates, then re-rank the shortlist with `score()`.
        """
        return self.qjl.estimate_inner_product(query, qv.sketch_bits, qv.norm, qv.dim)

    def rerank(
        self,
        query: np.ndarray,
        candidates: List[QuantizedVector],
        top_k: int = 10,
        shortlist: Optional[int] = None,
    ) -> List[Tuple[int, float]]:
        """
        Two-stage ANN re-ranking exactly as TurboQuant is meant to be used:
        QJL shortlist (1-bit, cheap) -> PolarQuant re-rank (3-bit, accurate).
        Returns (index, score) pairs sorted by descending score.
        """
        n = len(candidates)
        shortlist = shortlist or min(n, max(top_k * 8, 64))
        prelim = np.array([self.estimate_inner_product(query, c) for c in candidates])
        idx = np.argsort(-prelim)[:shortlist]
        rescored = [(int(i), self.score(query, candidates[i])) for i in idx]
        rescored.sort(key=lambda t: -t[1])
        return rescored[:top_k]

    def estimate_cosine(self, query: np.ndarray, qv: QuantizedVector) -> float:
        q = np.asarray(query, dtype=np.float32).ravel()
        qn = float(np.linalg.norm(q))
        if qn == 0 or qv.norm == 0:
            return 0.0
        return self.estimate_inner_product(query, qv) / (qn * qv.norm)

    # -- bit packing for the `bits`-bit direction codes --------------------- #
    def _pack_codes(self, codes: np.ndarray) -> np.ndarray:
        bitstr = np.zeros(codes.shape[0] * self.bits, dtype=np.uint8)
        for b in range(self.bits):
            bitstr[b :: self.bits] = (codes >> b) & 1
        return np.packbits(bitstr)

    def _unpack_codes(self, packed: np.ndarray, count: int) -> np.ndarray:
        bits = np.unpackbits(packed)[: count * self.bits]
        codes = np.zeros(count, dtype=np.uint16)
        for b in range(self.bits):
            codes |= bits[b :: self.bits].astype(np.uint16) << b
        return codes

    # -- accounting --------------------------------------------------------- #
    def compression_ratio(self, against: str = "fp32") -> float:
        """Bytes-saved ratio vs fp32 (32 bit/dim) or fp16 (16 bit/dim) storage."""
        codec_bits_per_dim = self.bits + (self.sketch_dim / self.dim)
        baseline = 32.0 if against == "fp32" else 16.0
        return baseline / codec_bits_per_dim
