"""Fusion and reconciliation helpers for BlueSight."""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

from mycosoft_mas.schemas.bluesight import (
    BlueSightDetection,
    BlueSightReconciliation,
    BlueSightTrack,
)


def _centroid(det: BlueSightDetection) -> Tuple[float, float]:
    if det.centroid_xy is not None:
        return float(det.centroid_xy[0]), float(det.centroid_xy[1])
    if det.bbox_xyxy is not None:
        x1, y1, x2, y2 = det.bbox_xyxy
        return (x1 + x2) / 2.0, (y1 + y2) / 2.0
    return (0.0, 0.0)


def fuse_sensor_detections(detections: List[BlueSightDetection]) -> List[BlueSightDetection]:
    """Deduplicate by class + nearest centroid to avoid duplicate multi-sensor entities."""
    fused: List[BlueSightDetection] = []
    for det in detections:
        cx, cy = _centroid(det)
        duplicate = None
        for existing in fused:
            if existing.class_name != det.class_name:
                continue
            ex, ey = _centroid(existing)
            if ((ex - cx) ** 2 + (ey - cy) ** 2) ** 0.5 <= 4.0:
                duplicate = existing
                break
        if duplicate is None:
            fused.append(det)
            continue
        if det.confidence > duplicate.confidence:
            fused.remove(duplicate)
            fused.append(det)
    return fused


def build_tracks(detections: List[BlueSightDetection], timestamp: str) -> List[BlueSightTrack]:
    tracks: List[BlueSightTrack] = []
    for det in detections:
        cx, cy = _centroid(det)
        track_id = det.track_id or det.detection_id
        tracks.append(
            BlueSightTrack(
                track_id=track_id,
                class_name=det.class_name,
                status="updated",
                confidence=det.confidence,
                centroid_xy=(cx, cy),
                last_seen_ts=timestamp,
            )
        )
    return tracks


def reconcile_truth(
    detections: List[BlueSightDetection],
    truth_entities: List[Dict[str, Any]],
    max_distance_px: float = 10.0,
) -> BlueSightReconciliation:
    matched_truth_ids = set()
    matched_detections = 0
    for det in detections:
        dcx, dcy = _centroid(det)
        best_truth_id = None
        best_distance = max_distance_px
        for entity in truth_entities:
            tx = float(entity.get("x", 0.0))
            ty = float(entity.get("y", 0.0))
            distance = ((dcx - tx) ** 2 + (dcy - ty) ** 2) ** 0.5
            if distance <= best_distance:
                best_distance = distance
                best_truth_id = str(entity.get("id", ""))
        if best_truth_id is not None:
            matched_detections += 1
            matched_truth_ids.add(best_truth_id)
    unmatched_visual = max(0, len(detections) - matched_detections)
    unmatched_truth = max(0, len(truth_entities) - len(matched_truth_ids))
    denominator = max(1, len(detections) + len(truth_entities))
    disagreement = float(unmatched_visual + unmatched_truth) / float(denominator)
    return BlueSightReconciliation(
        matched_sim_entities=matched_detections,
        unmatched_visual_entities=unmatched_visual,
        visual_truth_disagreement_score=disagreement,
        sensor_disagreement_score=0.0,
    )

