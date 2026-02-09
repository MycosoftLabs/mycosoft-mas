"""
MyceliumSeg segmentation metrics (paper-aligned).
IoU, F1, Boundary IoU (dilation ratio 0.001), HD95, ASSD.
"""
from __future__ import annotations

import math
from typing import Tuple

import numpy as np


def _ensure_binary(mask: np.ndarray) -> np.ndarray:
    if mask.dtype != bool and mask.dtype != np.uint8:
        mask = np.asarray(mask, dtype=np.float64)
    return (mask > 0).astype(np.uint8)


def _boundary_points(mask: np.ndarray) -> np.ndarray:
    """Return (N,2) array of boundary pixel coordinates (y,x)."""
    mask = _ensure_binary(mask)
    if mask.sum() == 0:
        return np.zeros((0, 2), dtype=np.int64)
    try:
        from scipy import ndimage
        eroded = ndimage.binary_erosion(mask)
        boundary = mask & ~eroded
    except ImportError:
        # Fallback: pixel is boundary if any 4-neighbor is 0
        pad = np.pad(mask, 1, mode="constant", constant_values=0)
        boundary = mask & (
            (pad[:-2, 1:-1] == 0) | (pad[2:, 1:-1] == 0) |
            (pad[1:-1, :-2] == 0) | (pad[1:-1, 2:] == 0)
        )
    ys, xs = np.where(boundary)
    return np.column_stack((ys, xs))


def iou_f1(gt: np.ndarray, pred: np.ndarray) -> Tuple[float, float, float, float, float]:
    """
    Foreground IoU and F1 (mycelium class).
    Returns: (iou, f1, precision, recall, tp+fp+fn info).
    """
    gt = _ensure_binary(gt).ravel()
    pred = _ensure_binary(pred).ravel()
    if gt.shape != pred.shape:
        raise ValueError("gt and pred shape mismatch")
    tp = float(np.logical_and(gt == 1, pred == 1).sum())
    fp = float(np.logical_and(gt == 0, pred == 1).sum())
    fn = float(np.logical_and(gt == 1, pred == 0).sum())
    # IoU = TP / (TP+FP+FN)
    denom_iou = tp + fp + fn
    iou = tp / denom_iou if denom_iou > 0 else 0.0
    # Precision, Recall, F1
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
    return iou, f1, precision, recall, (tp, fp, fn)


def boundary_iou(
    gt: np.ndarray,
    pred: np.ndarray,
    dilation_ratio: float = 0.001,
) -> float:
    """
    Boundary IoU: IoU restricted to pixels within d of boundary.
    d = dilation_ratio * image_diagonal (paper uses 0.001).
    """
    gt = _ensure_binary(gt)
    pred = _ensure_binary(pred)
    if gt.shape != pred.shape:
        raise ValueError("gt and pred shape mismatch")
    h, w = gt.shape
    diag = math.sqrt(h * h + w * w)
    d = max(1, int(round(dilation_ratio * diag)))
    # Boundary bands: dilate boundary by d
    def mask_to_boundary_band(m: np.ndarray) -> np.ndarray:
        b = _boundary_points(m)
        if len(b) == 0:
            return np.zeros_like(m, dtype=bool)
        band = np.zeros_like(m, dtype=bool)
        for dy in range(-d, d + 1):
            for dx in range(-d, d + 1):
                if dy * dy + dx * dx <= d * d:
                    y, x = b[:, 0] + dy, b[:, 1] + dx
                    valid = (y >= 0) & (y < m.shape[0]) & (x >= 0) & (x < m.shape[1])
                    band[y[valid], x[valid]] = True
        return band & (m > 0)
    g_bound = mask_to_boundary_band(gt)
    p_bound = mask_to_boundary_band(pred)
    inter = np.logical_and(g_bound, p_bound).sum()
    union = np.logical_or(g_bound, p_bound).sum()
    return float(inter / union) if union > 0 else 0.0


def _pairwise_min_distances(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """For each row in a, min Euclidean distance to any row in b. Shape (len(a),)."""
    try:
        from scipy.spatial.distance import cdist
        return cdist(a, b, metric="euclidean").min(axis=1)
    except ImportError:
        # Fallback: brute force (slow for large boundaries)
        out = np.full(len(a), np.nan)
        for i in range(len(a)):
            out[i] = np.sqrt(((b - a[i]) ** 2).sum(axis=1)).min()
        return out


def hausdorff_95(gt: np.ndarray, pred: np.ndarray) -> float:
    """
    HD95: 95th percentile of distances between boundary points; max of two directions.
    """
    sg = _boundary_points(gt)
    sp = _boundary_points(pred)
    if len(sg) == 0 or len(sp) == 0:
        return float("inf") if len(sg) != len(sp) else 0.0
    d_gp = _pairwise_min_distances(sg, sp)
    d_pg = _pairwise_min_distances(sp, sg)
    p95_gp = np.percentile(d_gp, 95)
    p95_pg = np.percentile(d_pg, 95)
    return float(max(p95_gp, p95_pg))


def assd(gt: np.ndarray, pred: np.ndarray) -> float:
    """
    Average symmetric surface distance between boundary point sets.
    """
    sg = _boundary_points(gt)
    sp = _boundary_points(pred)
    if len(sg) == 0 or len(sp) == 0:
        return float("inf") if len(sg) != len(sp) else 0.0
    d_gp = _pairwise_min_distances(sg, sp)
    d_pg = _pairwise_min_distances(sp, sg)
    return float((d_gp.sum() + d_pg.sum()) / (len(sg) + len(sp)))


def compute_all_metrics(
    gt: np.ndarray,
    pred: np.ndarray,
    boundary_dilation_ratio: float = 0.001,
) -> dict:
    """
    Returns dict with keys: iou, f1, precision, recall, boundary_iou, hd95, assd.
    """
    iou, f1, precision, recall, _ = iou_f1(gt, pred)
    biou = boundary_iou(gt, pred, dilation_ratio=boundary_dilation_ratio)
    hd = hausdorff_95(gt, pred)
    a = assd(gt, pred)
    return {
        "iou": round(iou, 6),
        "f1": round(f1, 6),
        "precision": round(precision, 6),
        "recall": round(recall, 6),
        "boundary_iou": round(biou, 6),
        "hd95": round(hd, 4),
        "assd": round(a, 4),
    }
