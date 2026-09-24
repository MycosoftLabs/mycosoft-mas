"""In-house SAHI-style slicing (spec §9.2 fallback when the ``sahi`` library is absent).

Pure numpy. ``slice_boxes`` tiles a frame, ``sliced_predict`` runs a caller
supplied ``predict_fn`` on every tile plus one full-frame pass (SAHI's default),
offsets tile boxes back into full-frame pixel coordinates and merges them with
class-aware non-maximum suppression at IoU 0.5.

Detections are plain tuples ``(x1, y1, x2, y2, conf, cls)`` in pixels so this
module has no dependency on the pydantic contracts and can be unit-tested with
a fake ``predict_fn``.
"""

from __future__ import annotations

from typing import Any, Callable, List, NamedTuple, Sequence, Tuple

Box = Tuple[int, int, int, int]
RawDetection = Tuple[float, float, float, float, float, str]
PredictFn = Callable[[Any], Sequence[Sequence[Any]]]

DEFAULT_IOU = 0.5


class SlicedPrediction(NamedTuple):
    detections: List[RawDetection]
    slices: int
    full_frame: bool


def slice_boxes(w: int, h: int, slice_size: int, overlap: float) -> List[Box]:
    """Tile a ``w``x``h`` frame with ``slice_size`` squares overlapping by ``overlap``.

    ``overlap`` is a fraction in [0, 1). Tiles advance by ``slice_size * (1 - overlap)``;
    the last tile along each axis is shifted back so it ends exactly at the frame edge
    (no tile ever leaves the frame, and the frame is always fully covered). A frame
    smaller than ``slice_size`` on an axis yields a single tile spanning that axis.
    """
    w = int(w)
    h = int(h)
    if w <= 0 or h <= 0:
        return []
    slice_size = max(1, int(slice_size))
    overlap = min(max(float(overlap), 0.0), 0.95)
    step = max(1, int(round(slice_size * (1.0 - overlap))))

    def _axis(length: int) -> List[Tuple[int, int]]:
        if length <= slice_size:
            return [(0, length)]
        starts: List[int] = []
        pos = 0
        while True:
            if pos + slice_size >= length:
                starts.append(length - slice_size)
                break
            starts.append(pos)
            pos += step
        # de-duplicate while preserving order (last tile may coincide with the previous)
        seen = set()
        out: List[Tuple[int, int]] = []
        for s in starts:
            if s in seen:
                continue
            seen.add(s)
            out.append((s, s + slice_size))
        return out

    boxes: List[Box] = []
    for y1, y2 in _axis(h):
        for x1, x2 in _axis(w):
            boxes.append((x1, y1, x2, y2))
    return boxes


def box_iou(a: Sequence[float], b: Sequence[float]) -> float:
    """IoU of two ``(x1, y1, x2, y2)`` boxes. Degenerate boxes give 0."""
    ax1, ay1, ax2, ay2 = float(a[0]), float(a[1]), float(a[2]), float(a[3])
    bx1, by1, bx2, by2 = float(b[0]), float(b[1]), float(b[2]), float(b[3])
    iw = min(ax2, bx2) - max(ax1, bx1)
    ih = min(ay2, by2) - max(ay1, by1)
    if iw <= 0.0 or ih <= 0.0:
        return 0.0
    inter = iw * ih
    area_a = max(0.0, ax2 - ax1) * max(0.0, ay2 - ay1)
    area_b = max(0.0, bx2 - bx1) * max(0.0, by2 - by1)
    union = area_a + area_b - inter
    if union <= 0.0:
        return 0.0
    return inter / union


def merge_detections(
    detections: Sequence[Sequence[Any]], iou_threshold: float = DEFAULT_IOU
) -> List[RawDetection]:
    """Class-aware NMS. Suppresses lower-confidence boxes of the *same class* that
    overlap a kept box with IoU >= ``iou_threshold``. Boxes of different classes
    never suppress each other. Output is sorted by confidence descending.
    """
    import numpy as np

    normalised: List[RawDetection] = []
    for det in detections:
        if len(det) < 6:
            continue
        x1, y1, x2, y2 = float(det[0]), float(det[1]), float(det[2]), float(det[3])
        normalised.append(
            (min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2), float(det[4]), str(det[5]))
        )
    if not normalised:
        return []

    kept: List[RawDetection] = []
    classes = sorted({d[5] for d in normalised})
    for cls in classes:
        group = [d for d in normalised if d[5] == cls]
        boxes = np.asarray([d[:4] for d in group], dtype=np.float64)
        confs = np.asarray([d[4] for d in group], dtype=np.float64)
        order = np.argsort(-confs, kind="stable")
        areas = np.clip(boxes[:, 2] - boxes[:, 0], 0, None) * np.clip(
            boxes[:, 3] - boxes[:, 1], 0, None
        )
        suppressed = np.zeros(len(group), dtype=bool)
        for pos, i in enumerate(order):
            if suppressed[i]:
                continue
            kept.append(group[int(i)])
            rest = order[pos + 1 :]
            if rest.size == 0:
                continue
            rest = rest[~suppressed[rest]]
            if rest.size == 0:
                continue
            iw = np.minimum(boxes[i, 2], boxes[rest, 2]) - np.maximum(boxes[i, 0], boxes[rest, 0])
            ih = np.minimum(boxes[i, 3], boxes[rest, 3]) - np.maximum(boxes[i, 1], boxes[rest, 1])
            inter = np.clip(iw, 0, None) * np.clip(ih, 0, None)
            union = areas[i] + areas[rest] - inter
            iou = np.where(union > 0, inter / np.where(union > 0, union, 1.0), 0.0)
            suppressed[rest[iou >= iou_threshold]] = True
    kept.sort(key=lambda d: -d[4])
    return kept


def sliced_predict(
    predict_fn: PredictFn,
    image_hwc: Any,
    slice_size: int,
    overlap: float,
    conf: float | None = None,
    *,
    full_frame: bool = True,
    iou_threshold: float = DEFAULT_IOU,
) -> SlicedPrediction:
    """Run ``predict_fn`` on each tile of ``image_hwc`` (H x W x C numpy array), offset
    the tile boxes back to full-frame pixels, optionally add one full-frame pass, and
    merge everything with class-aware NMS.

    ``predict_fn(tile_array) -> iterable of (x1, y1, x2, y2, conf, cls_name)`` in tile
    pixel coordinates. ``conf`` (when given) drops detections below the threshold.
    Returns ``SlicedPrediction(detections, slices, full_frame)``; ``slices`` counts
    only the tiles, not the full-frame pass.
    """
    import numpy as np

    image = np.asarray(image_hwc)
    if image.ndim < 2:
        raise ValueError("image_hwc must be at least 2-D (H x W[ x C])")
    h, w = int(image.shape[0]), int(image.shape[1])
    tiles = slice_boxes(w, h, slice_size, overlap)
    raw: List[RawDetection] = []
    min_conf = float(conf) if conf is not None else None

    def _collect(results: Sequence[Sequence[Any]], dx: float, dy: float) -> None:
        for det in results or []:
            if len(det) < 6:
                continue
            c = float(det[4])
            if min_conf is not None and c < min_conf:
                continue
            raw.append(
                (
                    float(det[0]) + dx,
                    float(det[1]) + dy,
                    float(det[2]) + dx,
                    float(det[3]) + dy,
                    c,
                    str(det[5]),
                )
            )

    n_slices = 0
    single_tile_is_frame = len(tiles) == 1 and tiles[0] == (0, 0, w, h)
    if not single_tile_is_frame:
        for x1, y1, x2, y2 in tiles:
            _collect(predict_fn(image[y1:y2, x1:x2]), float(x1), float(y1))
            n_slices += 1
    if full_frame or single_tile_is_frame:
        _collect(predict_fn(image), 0.0, 0.0)
    # clamp to frame bounds
    clamped: List[RawDetection] = []
    for x1, y1, x2, y2, c, cls in raw:
        clamped.append(
            (
                min(max(x1, 0.0), float(w)),
                min(max(y1, 0.0), float(h)),
                min(max(x2, 0.0), float(w)),
                min(max(y2, 0.0), float(h)),
                c,
                cls,
            )
        )
    merged = merge_detections(clamped, iou_threshold=iou_threshold)
    return SlicedPrediction(
        detections=merged, slices=n_slices, full_frame=bool(full_frame or single_tile_is_frame)
    )


__all__ = [
    "Box",
    "DEFAULT_IOU",
    "RawDetection",
    "SlicedPrediction",
    "box_iou",
    "merge_detections",
    "slice_boxes",
    "sliced_predict",
]
