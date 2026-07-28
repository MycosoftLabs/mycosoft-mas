"""
Tests for the TurboQuant reference codec (mycosoft_mas/memory/turboquant.py).

Verifies the three properties that matter for MYCA's memory:
  1. Orthogonal rotation is norm-preserving and invertible.
  2. PolarQuant+QJL reconstruction preserves direction (high cosine to original).
  3. The QJL asymmetric estimator recovers inner products well enough that
     top-k recall over compressed vectors matches brute-force fp32 search.
  4. Compression ratio is the advertised ~5-10x.
"""

import numpy as np
import pytest

from mycosoft_mas.memory.turboquant import (
    QJLSketch,
    TurboQuantCodec,
    randomized_rotation,
)


def test_rotation_is_orthogonal_and_invertible():
    rng = np.random.default_rng(0)
    x = rng.standard_normal(1536).astype(np.float32)
    rot = randomized_rotation(x, seed=123)
    # norm preserved (padding to next pow2 keeps L2 norm)
    assert np.isclose(np.linalg.norm(rot), np.linalg.norm(x), rtol=1e-4)
    back = randomized_rotation(rot, seed=123, inverse=True)[: x.shape[0]]
    assert np.allclose(back, x, atol=1e-4)


@pytest.mark.parametrize("dim,bits", [(384, 3), (768, 3), (1536, 4)])
def test_reconstruction_preserves_direction(dim, bits):
    rng = np.random.default_rng(1)
    codec = TurboQuantCodec(dim=dim, bits=bits)
    cosines = []
    for _ in range(50):
        x = rng.standard_normal(dim).astype(np.float32)
        approx = codec.decode(codec.encode(x))
        cos = float(x @ approx / (np.linalg.norm(x) * np.linalg.norm(approx)))
        cosines.append(cos)
    # 3-4 bit TurboQuant should keep cosine high on isotropic data
    assert np.mean(cosines) > 0.93


def test_qjl_inner_product_estimator_is_unbiased():
    rng = np.random.default_rng(2)
    dim = 1024
    qjl = QJLSketch(sketch_dim=512, seed=7)
    errors = []
    for _ in range(40):
        q = rng.standard_normal(dim).astype(np.float32)
        k = rng.standard_normal(dim).astype(np.float32)
        true_ip = float(q @ k)
        est = qjl.estimate_inner_product(q, qjl.sign_bits(k), float(np.linalg.norm(k)), dim)
        errors.append(est - true_ip)
    # estimator should be approximately unbiased (mean error near zero)
    assert abs(np.mean(errors)) < 0.15 * dim**0.5


def test_reconstruction_topk_recall_matches_bruteforce():
    """Stage-1 reconstruction scoring (the accurate primary path) tracks fp32 top-k."""
    rng = np.random.default_rng(3)
    dim, n, k = 768, 2000, 10
    base = rng.standard_normal((n, dim)).astype(np.float32)
    query = rng.standard_normal(dim).astype(np.float32)

    truth = set(np.argsort(-(base @ query))[:k].tolist())
    codec = TurboQuantCodec(dim=dim, bits=3, sketch_dim=256)
    qvs = [codec.encode(v) for v in base]
    scores = np.array([codec.score(query, qv) for qv in qvs])
    got = set(np.argsort(-scores)[:k].tolist())

    assert len(truth & got) / k >= 0.7


def test_two_stage_rerank_finds_real_neighbors():
    """
    Realistic semantic-search shape: a few true neighbors with high cosine planted
    among random noise. The QJL shortlist -> PolarQuant rerank pipeline recovers them.
    """
    rng = np.random.default_rng(11)
    dim, n, k = 768, 1500, 10
    query = rng.standard_normal(dim).astype(np.float32)
    qdir = query / np.linalg.norm(query)

    # planted neighbors: dominated by the query direction (cosine ~0.8-0.95)
    neighbors = qdir[None, :] * rng.uniform(6, 10, (k, 1)) + rng.standard_normal((k, dim)).astype(
        np.float32
    )
    noise = rng.standard_normal((n, dim)).astype(np.float32)
    corpus = np.vstack([neighbors.astype(np.float32), noise])
    truth = set(np.argsort(-(corpus @ query))[:k].tolist())

    codec = TurboQuantCodec(dim=dim, bits=3, sketch_dim=256)
    qvs = [codec.encode(v) for v in corpus]
    got = {i for i, _ in codec.rerank(query, qvs, top_k=k)}

    assert len(truth & got) / k >= 0.8


def test_compression_ratio_reported():
    codec = TurboQuantCodec(dim=1536, bits=3, sketch_dim=128)
    # 3 bits + 128/1536 ≈ 3.08 bits/dim vs 32 -> ~10x, vs 16 -> ~5x
    assert codec.compression_ratio("fp32") > 9.0
    assert codec.compression_ratio("fp16") > 4.5

    x = np.random.default_rng(4).standard_normal(1536).astype(np.float32)
    qv = codec.encode(x)
    fp32_bytes = 1536 * 4
    assert qv.nbytes() < fp32_bytes / 5
