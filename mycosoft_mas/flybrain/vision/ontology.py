"""Detection ontology and geometry (spec §9 ``ontology.py``).

* ``CATEGORY_MAP`` / ``categorize``: detector class name → coarse category
  (person, vehicle, vessel, aircraft, animal, plant, fungus, food, structure, object).
  Class names always come from the model; this module only buckets them.
* ``TaxonResolver``: async MINDEX taxon lookup for animal/plant/fungus classes
  (``GET {MINDEX_API_URL}/api/mindex/taxa?scientific_name=<cls>&limit=1``), 2 s timeout,
  LRU cached. Unreachable → ``Taxon(matched=False, note=...)``, never a guess.
* Geometry: bearing from bbox centre, range from bbox height + per-category height prior
  (``range_source="estimate"``), location from bearing + range, ground-footprint perimeter,
  and ``TrackMemory`` pathways.
* ``enrich``: fills those fields on a ``DetectionFrame`` honestly — ``None`` whenever an
  input (frame size, heading, pose, prior) is missing.

Heavy/optional imports (httpx) are local to the functions that need them.
"""

from __future__ import annotations

import logging
import math
import time
from collections import OrderedDict, deque
from typing import Any, Deque, Dict, List, Mapping, Optional, Sequence, Tuple

from mycosoft_mas.flybrain.schemas import Detection, DetectionFrame, GeoPoint, Taxon

logger = logging.getLogger(__name__)

EARTH_RADIUS_M = 6_371_008.8

CATEGORIES = (
    "person",
    "vehicle",
    "vessel",
    "aircraft",
    "animal",
    "plant",
    "fungus",
    "food",
    "structure",
    "object",
)
BIOLOGICAL_CATEGORIES = ("animal", "plant", "fungus")


def _build_category_map() -> Dict[str, str]:
    groups: Dict[str, Sequence[str]] = {
        "person": ("person", "human", "man", "woman", "boy", "girl", "child", "pedestrian"),
        # COCO vehicles + OpenImages
        "vehicle": (
            "bicycle",
            "car",
            "motorcycle",
            "motorbike",
            "bus",
            "train",
            "truck",
            "van",
            "taxi",
            "ambulance",
            "tank",
            "tractor",
            "golf cart",
            "snowmobile",
            "limousine",
            "vehicle",
            "land vehicle",
            "trailer",
            "cart",
            "scooter",
            "segway",
            "wheelchair",
            "unicycle",
            "tricycle",
            "jeep",
            "pickup truck",
        ),
        "vessel": (
            "boat",
            "ship",
            "canoe",
            "kayak",
            "jet ski",
            "submarine",
            "sailboat",
            "barge",
            "watercraft",
            "gondola",
            "yacht",
            "ferry",
            "raft",
            "vessel",
            "cargo ship",
            "fishing boat",
        ),
        "aircraft": (
            "airplane",
            "aeroplane",
            "aircraft",
            "helicopter",
            "drone",
            "unmanned aerial vehicle",
            "uav",
            "rocket",
            "missile",
            "hot air balloon",
            "glider",
            "jet",
            "quadcopter",
            "parachute",
        ),
        "animal": (
            # COCO
            "bird",
            "cat",
            "dog",
            "horse",
            "sheep",
            "cow",
            "elephant",
            "bear",
            "zebra",
            "giraffe",
            # OpenImages / common
            "animal",
            "deer",
            "fox",
            "rabbit",
            "hare",
            "squirrel",
            "raccoon",
            "insect",
            "butterfly",
            "moth",
            "bee",
            "wasp",
            "ant",
            "beetle",
            "spider",
            "snake",
            "lizard",
            "frog",
            "toad",
            "fish",
            "turtle",
            "tortoise",
            "duck",
            "goose",
            "swan",
            "owl",
            "eagle",
            "hawk",
            "falcon",
            "chicken",
            "turkey",
            "pig",
            "goat",
            "monkey",
            "rat",
            "hamster",
            "mouse (animal)",
            "otter",
            "seal",
            "sea lion",
            "whale",
            "dolphin",
            "shark",
            "crab",
            "lobster",
            "shrimp",
            "jellyfish",
            "starfish",
            "snail",
            "slug",
            "worm",
            "caterpillar",
            "dragonfly",
            "ladybug",
            "mosquito",
            "fly",
            "bat",
            "wolf",
            "coyote",
            "lion",
            "tiger",
            "leopard",
            "cheetah",
            "jaguar",
            "lynx",
            "kangaroo",
            "koala",
            "panda",
            "camel",
            "llama",
            "alpaca",
            "donkey",
            "mule",
            "bull",
            "ox",
            "bison",
            "moose",
            "elk",
            "antelope",
            "hippopotamus",
            "rhinoceros",
            "crocodile",
            "alligator",
            "penguin",
            "parrot",
            "sparrow",
            "pigeon",
            "crow",
            "raven",
            "magpie",
            "woodpecker",
            "hummingbird",
            "flamingo",
            "ostrich",
            "peacock",
            "seahorse",
            "octopus",
            "squid",
            "scorpion",
            "centipede",
            "millipede",
            "tick",
            "mite",
            "cricket",
            "grasshopper",
            "cockroach",
            "termite",
        ),
        "plant": (
            "potted plant",
            "pottedplant",
            "plant",
            "houseplant",
            "tree",
            "flower",
            "grass",
            "bush",
            "shrub",
            "leaf",
            "moss",
            "fern",
            "cactus",
            "palm tree",
            "sunflower",
            "rose",
            "lavender",
            "maple",
            "oak",
            "pine",
            "willow",
            "bamboo",
            "vine",
            "ivy",
            "seedling",
            "sapling",
            "weed",
            "algae",
            "seaweed",
            "kelp",
            "lily",
            "tulip",
            "daisy",
            "orchid",
            "hedge",
            "wheat",
            "corn plant",
            "crop",
            "flowerpot plant",
        ),
        "fungus": (
            "mushroom",
            "fungus",
            "fungi",
            "toadstool",
            "mold",
            "mould",
            "mildew",
            "lichen",
            "truffle",
            "bracket fungus",
            "shelf fungus",
            "puffball",
            "morel",
            "chanterelle",
            "amanita",
            "bolete",
            "polypore",
            "yeast",
            "mycelium",
            "fruiting body",
            "conk",
            "earthstar",
            "stinkhorn",
            "coral fungus",
            "jelly fungus",
            "cup fungus",
            "rust fungus",
            "smut",
            "oyster mushroom",
            "shiitake",
            "reishi",
            "lion's mane",
            "turkey tail",
            "fly agaric",
            "death cap",
            "psathyrella",
        ),
        "food": (
            # COCO
            "banana",
            "apple",
            "sandwich",
            "orange",
            "broccoli",
            "carrot",
            "hot dog",
            "pizza",
            "donut",
            "doughnut",
            "cake",
            # OpenImages / common
            "food",
            "bread",
            "cheese",
            "egg",
            "tomato",
            "potato",
            "onion",
            "garlic",
            "pepper",
            "bell pepper",
            "cucumber",
            "lettuce",
            "cabbage",
            "pumpkin",
            "squash",
            "zucchini",
            "mango",
            "pear",
            "peach",
            "grape",
            "grapes",
            "strawberry",
            "cherry",
            "lemon",
            "lime",
            "melon",
            "watermelon",
            "pineapple",
            "coconut",
            "pomegranate",
            "avocado",
            "nut",
            "peanut",
            "almond",
            "rice",
            "pasta",
            "noodle",
            "sushi",
            "burrito",
            "taco",
            "hamburger",
            "burger",
            "french fries",
            "fries",
            "cookie",
            "muffin",
            "croissant",
            "bagel",
            "pretzel",
            "candy",
            "chocolate",
            "ice cream",
            "pastry",
            "pie",
            "waffle",
            "pancake",
            "salad",
            "soup",
            "steak",
            "sausage",
            "bacon",
            "ham",
            "seafood",
            "honey",
            "fruit",
            "vegetable",
            "berry",
            "seed",
            "grain",
        ),
        "structure": (
            # COCO
            "traffic light",
            "fire hydrant",
            "stop sign",
            "parking meter",
            "bench",
            # OpenImages / common
            "building",
            "house",
            "tower",
            "bridge",
            "tent",
            "lighthouse",
            "skyscraper",
            "fountain",
            "street light",
            "billboard",
            "door",
            "window",
            "fence",
            "wall",
            "castle",
            "barn",
            "shed",
            "silo",
            "windmill",
            "wind turbine",
            "antenna",
            "pole",
            "pylon",
            "dam",
            "pier",
            "dock",
            "road",
            "stairs",
            "gate",
            "tunnel",
            "greenhouse",
            "cabin",
            "hut",
            "office building",
            "warehouse",
            "factory",
            "stadium",
            "church",
            "temple",
            "mosque",
            "monument",
            "statue",
            "sign",
            "solar panel",
            "water tower",
            "crane",
            "scaffolding",
        ),
        "object": (
            # COCO remainder
            "backpack",
            "umbrella",
            "handbag",
            "tie",
            "suitcase",
            "frisbee",
            "skis",
            "snowboard",
            "sports ball",
            "kite",
            "baseball bat",
            "baseball glove",
            "skateboard",
            "surfboard",
            "tennis racket",
            "bottle",
            "wine glass",
            "cup",
            "fork",
            "knife",
            "spoon",
            "bowl",
            "chair",
            "couch",
            "sofa",
            "bed",
            "dining table",
            "diningtable",
            "toilet",
            "tv",
            "tvmonitor",
            "laptop",
            "mouse",
            "remote",
            "keyboard",
            "cell phone",
            "microwave",
            "oven",
            "toaster",
            "sink",
            "refrigerator",
            "book",
            "clock",
            "vase",
            "scissors",
            "teddy bear",
            "hair drier",
            "hair dryer",
            "toothbrush",
        ),
    }
    out: Dict[str, str] = {}
    for category, names in groups.items():
        for name in names:
            out[name] = category
    return out


CATEGORY_MAP: Dict[str, str] = _build_category_map()

# Substrings that decide a compound/unknown class name (checked in this order).
_KEYWORD_HINTS: Tuple[Tuple[str, str], ...] = (
    ("mushroom", "fungus"),
    ("fungus", "fungus"),
    ("fungi", "fungus"),
    ("mold", "fungus"),
    ("mould", "fungus"),
    ("lichen", "fungus"),
    ("truffle", "fungus"),
    ("mycel", "fungus"),
    ("boat", "vessel"),
    ("ship", "vessel"),
    ("plane", "aircraft"),
    ("copter", "aircraft"),
    ("drone", "aircraft"),
    ("truck", "vehicle"),
    ("car", "vehicle"),
    ("bike", "vehicle"),
    ("cycle", "vehicle"),
    ("tree", "plant"),
    ("flower", "plant"),
    ("plant", "plant"),
    ("person", "person"),
    ("bird", "animal"),
    ("fish", "animal"),
    ("dog", "animal"),
    ("cat", "animal"),
    ("building", "structure"),
    ("house", "structure"),
    ("tower", "structure"),
)


def normalize_class(cls: Any) -> str:
    text = str(cls or "").strip().lower().replace("_", " ").replace("-", " ")
    return " ".join(text.split())


def categorize(cls: Any) -> str:
    """Map a detector class name to one of ``CATEGORIES``. Unknown → ``"object"``."""
    name = normalize_class(cls)
    if not name:
        return "object"
    hit = CATEGORY_MAP.get(name)
    if hit:
        return hit
    if name.endswith("es") and name[:-2] in CATEGORY_MAP:
        return CATEGORY_MAP[name[:-2]]
    if name.endswith("s") and name[:-1] in CATEGORY_MAP:
        return CATEGORY_MAP[name[:-1]]
    for keyword, category in _KEYWORD_HINTS:
        if keyword in name:
            return category
    return "object"


def is_biological(category: str) -> bool:
    return category in BIOLOGICAL_CATEGORIES


# ---------------------------------------------------------------------------
# MINDEX taxon lookup
# ---------------------------------------------------------------------------


def _normalize_items(payload: Any) -> List[Dict[str, Any]]:
    if payload is None:
        return []
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    if not isinstance(payload, dict):
        return []
    for key in ("items", "taxa", "data", "results", "rows", "species"):
        value = payload.get(key)
        if isinstance(value, list):
            return [row for row in value if isinstance(row, dict)]
    return []


def _mindex_headers() -> Dict[str, str]:
    import os

    headers = {"Accept": "application/json"}
    token = os.environ.get("MINDEX_INTERNAL_TOKEN", "").strip()
    if token:
        headers["X-Internal-Token"] = token
        return headers
    key = os.environ.get("MINDEX_API_KEY", "").strip()
    if key:
        headers["X-API-Key"] = key
    return headers


class TaxonResolver:
    """Resolve a class name to a MINDEX taxon.

    ``resolve`` is async (httpx, ``timeout_s``); ``resolve_cached`` is sync and only
    ever returns what a previous ``resolve`` already fetched. Results are LRU cached
    (``max_entries``); lookup failures are cached for ``failure_ttl_s`` seconds only.
    """

    def __init__(
        self,
        mindex_api_url: str,
        timeout_s: float = 2.0,
        *,
        max_entries: int = 256,
        failure_ttl_s: float = 30.0,
        transport: Any = None,
    ) -> None:
        self.base_url = (mindex_api_url or "").rstrip("/")
        self.timeout_s = float(timeout_s)
        self.max_entries = int(max_entries)
        self.failure_ttl_s = float(failure_ttl_s)
        self._transport = transport
        self._cache: "OrderedDict[str, Tuple[Taxon, float, bool]]" = OrderedDict()

    # -- cache helpers ------------------------------------------------------

    def _get(self, key: str) -> Optional[Taxon]:
        entry = self._cache.get(key)
        if entry is None:
            return None
        taxon, stamp, ok = entry
        if not ok and (time.monotonic() - stamp) > self.failure_ttl_s:
            self._cache.pop(key, None)
            return None
        self._cache.move_to_end(key)
        return taxon

    def _put(self, key: str, taxon: Taxon, ok: bool) -> None:
        self._cache[key] = (taxon, time.monotonic(), ok)
        self._cache.move_to_end(key)
        while len(self._cache) > self.max_entries:
            self._cache.popitem(last=False)

    def resolve_cached(self, cls: Any) -> Optional[Taxon]:
        """Sync: return the cached taxon for ``cls`` or ``None`` (never touches the network)."""
        key = normalize_class(cls)
        if not key:
            return None
        return self._get(key)

    # -- network ------------------------------------------------------------

    async def resolve(self, cls: Any) -> Optional[Taxon]:
        key = normalize_class(cls)
        if not key:
            return None
        cached = self._get(key)
        if cached is not None:
            return cached
        if not self.base_url:
            taxon = Taxon(matched=False, note="MINDEX_API_URL not configured")
            self._put(key, taxon, ok=False)
            return taxon
        try:
            import httpx
        except ImportError:
            taxon = Taxon(matched=False, note="httpx not installed")
            self._put(key, taxon, ok=False)
            return taxon

        url = f"{self.base_url}/api/mindex/taxa"
        params = {"scientific_name": key, "limit": 1}
        try:
            client_kwargs: Dict[str, Any] = {"timeout": self.timeout_s}
            if self._transport is not None:
                client_kwargs["transport"] = self._transport
            async with httpx.AsyncClient(**client_kwargs) as client:
                response = await client.get(url, params=params, headers=_mindex_headers())
            if response.status_code >= 400:
                taxon = Taxon(matched=False, note=f"MINDEX taxa lookup HTTP {response.status_code}")
                self._put(key, taxon, ok=False)
                return taxon
            payload = response.json() if response.content else {}
        except Exception as exc:  # noqa: BLE001 - any transport failure is "unreachable"
            taxon = Taxon(
                matched=False, note=f"MINDEX unreachable: {type(exc).__name__}: {str(exc)[:120]}"
            )
            self._put(key, taxon, ok=False)
            return taxon

        rows = _normalize_items(payload)
        if not rows:
            taxon = Taxon(matched=False, note=f"no MINDEX taxon named '{key}'")
            self._put(key, taxon, ok=True)
            return taxon
        row = rows[0]
        taxon_id = row.get("taxon_id") or row.get("id") or row.get("mindex_id")
        sci = row.get("scientific_name") or row.get("name") or row.get("canonical_name")
        taxon = Taxon(
            taxon_id=str(taxon_id) if taxon_id is not None else None,
            scientific_name=str(sci) if sci else None,
            rank=(str(row.get("rank")) if row.get("rank") else None),
            source="mindex",
            matched=True,
            note="",
        )
        self._put(key, taxon, ok=True)
        return taxon


# ---------------------------------------------------------------------------
# Geometry
# ---------------------------------------------------------------------------

# Typical real-world heights (metres) used ONLY for range *estimates*
# (``range_source="estimate"``). Keys are class names first, then categories.
# Categories with no sensible prior (vessel, aircraft, structure, plant, food,
# object) deliberately have none → ``range_m=None``.
HEIGHT_PRIORS_M: Dict[str, float] = {
    # categories
    "person": 1.7,
    "animal": 0.6,
    "vehicle": 1.5,
    # classes (override the category)
    "bicycle": 1.0,
    "motorcycle": 1.1,
    "car": 1.5,
    "truck": 3.0,
    "bus": 3.2,
    "train": 4.0,
    "dog": 0.5,
    "cat": 0.25,
    "horse": 1.6,
    "cow": 1.4,
    "sheep": 0.8,
    "bird": 0.2,
    "deer": 1.0,
    "bear": 1.0,
    "elephant": 3.0,
    "giraffe": 5.0,
    "zebra": 1.4,
    "mushroom": 0.08,
}


def wrap360(angle_deg: float) -> float:
    return float(angle_deg) % 360.0


def bearing_from_bbox(
    bbox_xyxy: Sequence[float],
    frame_w: Optional[float],
    heading_deg: Optional[float],
    hfov_deg: float,
) -> Optional[float]:
    """``heading + (cx - 0.5) * hfov`` in [0, 360). ``None`` when frame_w/heading are unknown."""
    if frame_w is None or frame_w <= 0 or heading_deg is None:
        return None
    cx = (float(bbox_xyxy[0]) + float(bbox_xyxy[2])) / 2.0 / float(frame_w)
    return wrap360(float(heading_deg) + (cx - 0.5) * float(hfov_deg))


def vertical_fov_deg(hfov_deg: float, frame_w: float, frame_h: float) -> Optional[float]:
    """Vertical FOV for a rectilinear camera from its horizontal FOV and aspect ratio."""
    if not frame_w or not frame_h or frame_w <= 0 or frame_h <= 0 or hfov_deg <= 0:
        return None
    half = math.tan(math.radians(float(hfov_deg)) / 2.0) * (float(frame_h) / float(frame_w))
    return math.degrees(2.0 * math.atan(half))


def estimate_range(
    bbox_xyxy: Sequence[float],
    frame_h: Optional[float],
    category: str,
    vfov_deg: Optional[float] = None,
    height_priors: Optional[Mapping[str, float]] = None,
    *,
    cls: Optional[str] = None,
) -> Tuple[Optional[float], str]:
    """Pinhole range estimate from bbox pixel height and a height prior.

    Returns ``(range_m, "estimate")``; ``range_m`` is ``None`` when there is no prior
    for ``cls``/``category``, no vertical FOV, or a degenerate box.
    """
    priors = height_priors if height_priors is not None else HEIGHT_PRIORS_M
    prior: Optional[float] = None
    if cls:
        prior = priors.get(normalize_class(cls))
    if prior is None:
        prior = priors.get(str(category or "").lower())
    if prior is None or prior <= 0:
        return None, "estimate"
    if frame_h is None or frame_h <= 0 or vfov_deg is None or vfov_deg <= 0:
        return None, "estimate"
    box_h = abs(float(bbox_xyxy[3]) - float(bbox_xyxy[1]))
    if box_h <= 0:
        return None, "estimate"
    angular = math.radians(float(vfov_deg)) * (box_h / float(frame_h))
    if angular <= 0 or angular >= math.pi:
        return None, "estimate"
    rng = prior / (2.0 * math.tan(angular / 2.0))
    if not math.isfinite(rng) or rng <= 0:
        return None, "estimate"
    return float(rng), "estimate"


def locate(lat: float, lon: float, bearing_deg: float, range_m: float) -> GeoPoint:
    """Equirectangular offset of ``range_m`` along ``bearing_deg`` (fine at <= 5 km)."""
    b = math.radians(float(bearing_deg))
    d_north = float(range_m) * math.cos(b)
    d_east = float(range_m) * math.sin(b)
    dlat = math.degrees(d_north / EARTH_RADIUS_M)
    cos_lat = math.cos(math.radians(float(lat)))
    if abs(cos_lat) < 1e-9:
        cos_lat = 1e-9
    dlon = math.degrees(d_east / (EARTH_RADIUS_M * cos_lat))
    return GeoPoint(lat=float(lat) + dlat, lon=float(lon) + dlon)


def footprint_perimeter(
    location: GeoPoint, bearing_deg: float, width_m: float, depth_m: float
) -> List[List[float]]:
    """Ground-footprint rectangle centred on ``location``, its depth axis along
    ``bearing_deg``. Returns a closed ``[[lon, lat], ...]`` ring of 5 points."""
    half_w = max(float(width_m), 0.0) / 2.0
    half_d = max(float(depth_m), 0.0) / 2.0
    b = math.radians(float(bearing_deg))
    # unit vectors: along = bearing direction, across = bearing + 90°
    along_n, along_e = math.cos(b), math.sin(b)
    across_n, across_e = -math.sin(b), math.cos(b)
    cos_lat = math.cos(math.radians(location.lat))
    if abs(cos_lat) < 1e-9:
        cos_lat = 1e-9
    corners: List[List[float]] = []
    for sa, sw in ((1, 1), (1, -1), (-1, -1), (-1, 1)):
        d_n = sa * half_d * along_n + sw * half_w * across_n
        d_e = sa * half_d * along_e + sw * half_w * across_e
        lat = location.lat + math.degrees(d_n / EARTH_RADIUS_M)
        lon = location.lon + math.degrees(d_e / (EARTH_RADIUS_M * cos_lat))
        corners.append([lon, lat])
    corners.append(list(corners[0]))
    return corners


class TrackMemory:
    """Per-track location history → ``pathway`` rings (``[[lon, lat], ...]``)."""

    def __init__(self, max_points: int = 50) -> None:
        self.max_points = max(2, int(max_points))
        self._tracks: Dict[str, Deque[Tuple[float, float, Optional[float]]]] = {}

    def update(
        self, track_id: str, point: GeoPoint, t_ms: Optional[float] = None
    ) -> List[List[float]]:
        key = str(track_id)
        history = self._tracks.get(key)
        if history is None:
            history = deque(maxlen=self.max_points)
            self._tracks[key] = history
        history.append((float(point.lon), float(point.lat), t_ms))
        return self.pathway(key)

    def pathway(self, track_id: str) -> List[List[float]]:
        history = self._tracks.get(str(track_id))
        if not history:
            return []
        return [[lon, lat] for lon, lat, _ in history]

    def last_seen_ms(self, track_id: str) -> Optional[float]:
        history = self._tracks.get(str(track_id))
        if not history:
            return None
        return history[-1][2]

    def forget(self, track_id: str) -> None:
        self._tracks.pop(str(track_id), None)

    def prune(self, now_ms: float, max_age_ms: float) -> int:
        """Drop tracks whose last timestamped point is older than ``max_age_ms``."""
        stale = [
            tid
            for tid, hist in self._tracks.items()
            if hist and hist[-1][2] is not None and (now_ms - hist[-1][2]) > max_age_ms
        ]
        for tid in stale:
            self._tracks.pop(tid, None)
        return len(stale)

    def __len__(self) -> int:
        return len(self._tracks)


# ---------------------------------------------------------------------------
# Frame enrichment
# ---------------------------------------------------------------------------


def _as_float(value: Any) -> Optional[float]:
    try:
        if value is None or isinstance(value, bool):
            return None
        out = float(value)
    except (TypeError, ValueError):
        return None
    return out if math.isfinite(out) else None


def _pose_fields(
    pose: Optional[Mapping[str, Any]],
) -> Tuple[Optional[float], Optional[float], Optional[float]]:
    if not pose:
        return None, None, None
    lat = _as_float(pose.get("lat", pose.get("latitude")))
    lon = _as_float(pose.get("lon", pose.get("lng", pose.get("longitude"))))
    heading = _as_float(pose.get("heading_deg", pose.get("heading", pose.get("yaw_deg"))))
    return lat, lon, heading


def enrich(
    frame: DetectionFrame,
    pose: Optional[Mapping[str, Any]],
    settings: Any = None,
    *,
    track_memory: Optional[TrackMemory] = None,
    resolver: Optional[TaxonResolver] = None,
) -> DetectionFrame:
    """Fill ``category``, ``bbox_norm``, ``bearing_deg``, ``range_m``/``range_source``,
    ``location``, ``perimeter`` and ``pathway`` on every detection of ``frame``.

    Every field stays ``None`` when its inputs are missing: no frame size → no bearing;
    no heading → no bearing; no bearing or range → no location; no location → no
    perimeter/pathway; no height prior for the class/category → no range estimate.
    A ``range_m`` already on the detection is treated as measured and kept.
    Taxa are attached only from ``resolver``'s cache (sync); use ``aenrich`` for lookups.
    """
    if settings is None:
        from mycosoft_mas.flybrain.config import get_settings

        settings = get_settings()
    hfov = float(getattr(settings, "camera_hfov_deg", 90.0) or 90.0)
    lat, lon, heading = _pose_fields(pose)
    frame_w = _as_float(frame.frame_w)
    frame_h = _as_float(frame.frame_h)
    vfov_frame = vertical_fov_deg(hfov, frame_w or 0.0, frame_h or 0.0)
    pose_vfov = _as_float(pose.get("vfov_deg")) if pose else None
    pose_hfov = _as_float(pose.get("hfov_deg")) if pose else None
    if pose_hfov:
        hfov = pose_hfov
        vfov_frame = vertical_fov_deg(hfov, frame_w or 0.0, frame_h or 0.0)

    enriched: List[Detection] = []
    for det in frame.detections:
        updates: Dict[str, Any] = {}
        category = (
            det.category if det.category and det.category != "unknown" else categorize(det.cls)
        )
        updates["category"] = category

        # Per-detection frame dims (multi-source remote payloads) override the frame's.
        det_w = _as_float(det.attributes.get("frame_w")) or frame_w
        det_h = _as_float(det.attributes.get("frame_h")) or frame_h
        det_vfov = pose_vfov or (
            vertical_fov_deg(hfov, det_w or 0.0, det_h or 0.0) if det_w and det_h else vfov_frame
        )

        x1, y1, x2, y2 = det.bbox_xyxy
        if det.bbox_norm is None and det_w and det_h and det_w > 0 and det_h > 0:
            updates["bbox_norm"] = (
                min(max(x1 / det_w, 0.0), 1.0),
                min(max(y1 / det_h, 0.0), 1.0),
                min(max(x2 / det_w, 0.0), 1.0),
                min(max(y2 / det_h, 0.0), 1.0),
            )

        bearing = det.bearing_deg
        if bearing is None:
            bearing = bearing_from_bbox(det.bbox_xyxy, det_w, heading, hfov)
        updates["bearing_deg"] = bearing

        range_m = det.range_m
        range_source = det.range_source
        if range_m is not None:
            range_source = range_source or "measured"
        else:
            range_m, est_source = estimate_range(
                det.bbox_xyxy, det_h, category, det_vfov, cls=det.cls
            )
            range_source = est_source if range_m is not None else None
        updates["range_m"] = range_m
        updates["range_source"] = range_source

        location = det.location
        if (
            location is None
            and bearing is not None
            and range_m is not None
            and lat is not None
            and lon is not None
        ):
            location = locate(lat, lon, bearing, range_m)
        updates["location"] = location

        perimeter = det.perimeter
        if (
            perimeter is None
            and location is not None
            and bearing is not None
            and range_m is not None
        ):
            width_m: Optional[float] = None
            if det_w and det_w > 0:
                ang_w = math.radians(hfov) * (abs(x2 - x1) / det_w)
                if 0 < ang_w < math.pi:
                    width_m = 2.0 * range_m * math.tan(ang_w / 2.0)
            if width_m is not None and width_m > 0:
                perimeter = footprint_perimeter(location, bearing, width_m, width_m)
                updates.setdefault("attributes", dict(det.attributes))
                updates["attributes"]["footprint_source"] = "estimate"
                updates["attributes"]["footprint_width_m"] = round(width_m, 3)
        updates["perimeter"] = perimeter

        pathway = det.pathway
        if location is not None and det.track_id and track_memory is not None:
            pathway = track_memory.update(det.track_id, location, frame.t_ms)
        updates["pathway"] = pathway

        if det.taxon is None and resolver is not None and is_biological(category):
            cached = resolver.resolve_cached(det.cls)
            if cached is not None:
                updates["taxon"] = cached

        enriched.append(det.model_copy(update=updates))

    notes: List[str] = []
    if frame.note:
        notes.append(frame.note)
    if enriched and heading is None:
        notes.append("no heading in pose: bearings not computed")
    if enriched and (lat is None or lon is None):
        notes.append("no lat/lon in pose: locations not computed")
    return frame.model_copy(update={"detections": enriched, "note": "; ".join(notes)})


async def aenrich(
    frame: DetectionFrame,
    pose: Optional[Mapping[str, Any]],
    settings: Any = None,
    *,
    track_memory: Optional[TrackMemory] = None,
    resolver: Optional[TaxonResolver] = None,
) -> DetectionFrame:
    """``enrich`` plus async MINDEX taxon lookups for animal/plant/fungus detections."""
    out = enrich(frame, pose, settings, track_memory=track_memory, resolver=resolver)
    if resolver is None:
        return out
    updated: List[Detection] = []
    for det in out.detections:
        if det.taxon is None and is_biological(det.category):
            taxon = await resolver.resolve(det.cls)
            if taxon is not None:
                det = det.model_copy(update={"taxon": taxon})
        updated.append(det)
    return out.model_copy(update={"detections": updated})


__all__ = [
    "BIOLOGICAL_CATEGORIES",
    "CATEGORIES",
    "CATEGORY_MAP",
    "EARTH_RADIUS_M",
    "HEIGHT_PRIORS_M",
    "TaxonResolver",
    "TrackMemory",
    "aenrich",
    "bearing_from_bbox",
    "categorize",
    "enrich",
    "estimate_range",
    "footprint_perimeter",
    "is_biological",
    "locate",
    "normalize_class",
    "vertical_fov_deg",
    "wrap360",
]
