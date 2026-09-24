"""FlyBrain vision stack: YOLO26 + SAHI detector, remote Jetson client, ontology.

Light imports only — every heavy dependency (numpy, PIL, httpx, ultralytics, sahi)
is imported lazily inside the functions that need it. The BlueSight adapters live
in ``bluesight_provider`` and are imported explicitly by callers that need them.
"""

from mycosoft_mas.flybrain.vision.detector import (
    DetectorUnavailable,
    FlyBrainDetector,
    RemoteDetector,
    get_detector,
    set_detector_for_tests,
)
from mycosoft_mas.flybrain.vision.ontology import (
    CATEGORY_MAP,
    TaxonResolver,
    TrackMemory,
    aenrich,
    bearing_from_bbox,
    categorize,
    enrich,
    estimate_range,
    footprint_perimeter,
    locate,
)
from mycosoft_mas.flybrain.vision.slicing import merge_detections, slice_boxes, sliced_predict

__all__ = [
    "CATEGORY_MAP",
    "DetectorUnavailable",
    "FlyBrainDetector",
    "RemoteDetector",
    "TaxonResolver",
    "TrackMemory",
    "aenrich",
    "bearing_from_bbox",
    "categorize",
    "enrich",
    "estimate_range",
    "footprint_perimeter",
    "get_detector",
    "locate",
    "merge_detections",
    "set_detector_for_tests",
    "slice_boxes",
    "sliced_predict",
]
