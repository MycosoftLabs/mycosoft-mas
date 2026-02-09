"""
Unit tests for MyceliumSeg segmentation metrics (IoU, F1, Boundary IoU, HD95, ASSD).
Plan: docs/MYCELIUMSEG_INTEGRATION_PLAN_FEB06_2026.md
"""
import numpy as np
import pytest

# Import from scripts path
import sys
from pathlib import Path
_root = Path(__file__).resolve().parents[1]
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from scripts.myceliumseg.metrics import (
    iou_f1,
    boundary_iou,
    hausdorff_95,
    assd,
    compute_all_metrics,
)


def test_iou_f1_perfect():
    gt = np.zeros((10, 10), dtype=np.uint8)
    gt[2:8, 2:8] = 1
    pred = gt.copy()
    iou, f1, p, r, _ = iou_f1(gt, pred)
    assert iou == 1.0
    assert f1 == 1.0
    assert p == 1.0
    assert r == 1.0


def test_iou_f1_no_overlap():
    gt = np.zeros((10, 10), dtype=np.uint8)
    gt[1:4, 1:4] = 1
    pred = np.zeros((10, 10), dtype=np.uint8)
    pred[6:9, 6:9] = 1
    iou, f1, p, r, _ = iou_f1(gt, pred)
    assert iou == 0.0
    assert f1 == 0.0


def test_iou_f1_partial():
    gt = np.zeros((10, 10), dtype=np.uint8)
    gt[2:6, 2:6] = 1  # 16 pixels
    pred = np.zeros((10, 10), dtype=np.uint8)
    pred[3:7, 3:7] = 1  # 16 pixels, overlap 3x3=9
    # TP=9, FP=7, FN=7 -> IoU = 9/(9+7+7)
    iou, f1, _, _, _ = iou_f1(gt, pred)
    assert 0 < iou < 1
    assert abs(iou - 9 / (9 + 7 + 7)) < 0.001


def test_boundary_iou_identical():
    gt = np.zeros((50, 50), dtype=np.uint8)
    y, x = np.ogrid[:50, :50]
    gt[(x - 25) ** 2 + (y - 25) ** 2 <= 15**2] = 1
    pred = gt.copy()
    biou = boundary_iou(gt, pred, dilation_ratio=0.01)
    assert biou >= 0.99


def test_hd95_identical():
    gt = np.zeros((30, 30), dtype=np.uint8)
    gt[5:25, 5:25] = 1
    pred = gt.copy()
    h = hausdorff_95(gt, pred)
    assert h == 0.0


def test_assd_identical():
    gt = np.zeros((30, 30), dtype=np.uint8)
    gt[5:25, 5:25] = 1
    pred = gt.copy()
    a = assd(gt, pred)
    assert a == 0.0


def test_compute_all_metrics():
    gt = np.zeros((40, 40), dtype=np.uint8)
    gt[5:35, 5:35] = 1
    pred = gt.copy()
    pred[8:32, 8:32] = 1  # slightly smaller
    out = compute_all_metrics(gt, pred, boundary_dilation_ratio=0.001)
    assert "iou" in out
    assert "f1" in out
    assert "boundary_iou" in out
    assert "hd95" in out
    assert "assd" in out
    assert 0 <= out["iou"] <= 1
    assert 0 <= out["f1"] <= 1
    assert 0 <= out["boundary_iou"] <= 1
    assert out["hd95"] >= 0
    assert out["assd"] >= 0
