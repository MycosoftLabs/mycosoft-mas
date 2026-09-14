# FlyBrain Module — FlyWire whole-brain LIF as a pluggable MYCA module

**Date:** 14 September 2026
**Status:** DESIGN + IMPLEMENTATION (this document is the contract every file in the module follows)
**Authority:** Morgan, 14 Sep 2026 — "make an application that allows us to plug this fly brain into any one of our systems".
**Upstream:** https://github.com/eonsystemspbc/fly-brain (Shiu et al. 2024 whole-brain LIF on FlyWire v783).
**Protected files:** untouched (`orchestrator.py`, `orchestrator_service.py`, `safety/`, `security/`, `constitution/`, `myca_soul.yaml`, `identity.py`).

---

## 1. What the upstream repo actually is

`eonsystemspbc/fly-brain` is a benchmark harness around one scientific model:

| Piece | Fact |
|---|---|
| Model | Leaky integrate-and-fire (LIF) neurons with alpha-function synapses, 1.8 ms delay, 2.2 ms refractory, Poisson optogenetic-style drive. Parameters in `code/paper-phil-drosophila/model.py` (MIT) and `code/run_pytorch.py` (GPL-2.0-or-later). |
| Data | FlyWire v783 public release: `data/2025_Completeness_783.csv` (138,639 neuron ids, 3.3 MB) and `data/2025_Connectivity_783.parquet` (15,091,983 synapse rows pre→post with signed weights `Excitatory x Connectivity`, 97 MB). |
| Experiments shipped | `sugar` (21 sugar GRNs @ 200 Hz → feeding circuit) and `p9` (P9 left/right descending neurons @ 100 Hz → forward walking). `data/sez_neurons.pickle` names 106 SEZ cell types (369 neurons). |
| Backends | Brian2 CPU (ground truth), Brian2CUDA, PyTorch, NEST GPU, GeNN, Brian2GeNN. All produce the same per-spike parquet schema. |
| Output | Spike times per neuron. Nothing else — no vision, no navigation, no classifier. |

Measured on this build host (CPU, numpy/scipy): loading the two files takes ~3 s; a dense sparse-matvec over the full 15M-synapse matrix is ~14 ms; an **event-driven** column gather over only the neurons that spiked in a step (typically 100–1,000 of 138k) is **0.3–0.8 ms**. That is what makes a real-time closed loop possible on the MAS VM without a GPU.

**Licenses (must be respected):** repo code is GPL-2.0-or-later except `code/paper-phil-drosophila/` (MIT). The MAS engine is written from the MIT model equations and the published parameters — it does **not** copy GPL source. FlyWire v783 data carries FlyWire's own data terms (the public release is CC BY-NC 4.0 at the time of writing; commercial use needs FlyWire's permission). The data is therefore **never committed** to a Mycosoft repo; it is fetched onto the NAS by `scripts/flybrain_fetch_connectome.py` and its SHA-256 is verified at load.

## 2. What the module does

```
Mycosoft system ──observe()──▶ Encoder ──rates──▶ FlyBrainEngine (138k LIF, event-driven) ──spikes──▶ Decoder ──MotorAction/NavPath──▶ Plug.act()
                                                          │
                                YOLO26 + SAHI vision ─────┘ (detections are one Observation kind)
```

One runtime, many plugs. A **plug** is the adapter for one Mycosoft system:

| Plug | observe() | act() | Actuation |
|---|---|---|---|
| `standalone` | API-supplied observations only | returns action | none |
| `droid` (Psathyrella / MycaControl) | in-process device telemetry (`device_registry_api.get_device_telemetry`), camera detections (remote Jetson `/detect` or local YOLO26+SAHI) | guidance payload; waypoints + camera point-at **only** when `dry_run=False` **and** `FLYBRAIN_DROID_ACTUATE=1` **and** AVANI approves | gated |
| `earthsim` (Earth Simulator operator) | ITDX map slice (`ao` bbox/center), device registry snapshot, Earth-2 status | nav path across the AO + operator narration | none |
| `nlm` (Nature Learning Model / FormSpace) | NLM probe status, optional NLM predict text | emits `formspace.observation/v1` envelopes of population rates into `CausalObservationPipeline`; anomaly score on rate vectors | none |
| `itdx` (FUSARIUM ITDX demonstration) | map slice + detections | `pathways`, `navigation`, `biology`, `information` channel rows in the exact `itdx_api._channel` shape | none |

Everything the module reports is **SIMULATED** (`origin`) and the API says so on every payload.

## 3. Package layout (MAS repo)

```
mycosoft_mas/flybrain/
  __init__.py            light imports only
  config.py              FlyBrainSettings (env: FLYBRAIN_*), known SHA-256, upstream raw URLs
  schemas.py             ALL pydantic contracts (already written — do not fork them)
  connectome.py          load CSV + (parquet|npz) → CSC/CSR float32; id<->index; sha256; subgraph; cache
  atlas.py               NeuronGroups from config/flybrain_atlas.yaml (+ derived downstream groups)
  model.py               FlyBrainEngine (numpy event-driven; optional torch); step/run/stimulate/silence/rates
  encoders.py            Observation → {group: rate_hz}
  decoders.py            group rates → MotorAction; population-code classifier (nearest centroid, session-learned)
  navigation.py          OccupancyGrid (local ENU), A*, NavPath, turn-bias
  runtime.py             FlyBrainRuntime: sessions, tick, autopilot loop, JSONL recorder, plug registry
  plugs/base.py          FlyBrainPlug protocol + PlugContext
  plugs/droid.py         psathyrella adapter (AVANI-gated)
  plugs/earthsim.py      Earth Simulator / AO operator
  plugs/nlm.py           FormSpace coupling
  plugs/itdx.py          ITDX channel provider
  vision/detector.py     YOLO26 (ultralytics) + SAHI (sahi lib or in-house slicing) + RemoteDetector; honest unavailability
  vision/slicing.py      in-house SAHI-style tiling + merge (class-aware NMS)
  vision/ontology.py     class → category; MINDEX taxon lookup; bearing/range/location/perimeter/pathway geometry
  vision/bluesight_provider.py  BlueSight DetectionProvider adapters: "yolo26_sahi", "flybrain_vision"
mycosoft_mas/core/routers/flybrain_api.py   /api/flybrain/*
mycosoft_mas/agents/flybrain_agent.py       FlyBrainAgent(BaseAgent)
config/flybrain_atlas.yaml                  (already written)
scripts/flybrain_fetch_connectome.py        fetch + verify + parquet→npz
tests/test_flybrain_*.py
docs/FLYBRAIN_MODULE_SEP14_2026.md          this file
```

Website (Next.js):

```
lib/flybrain/contract.ts                       TS mirror of schemas.py
lib/flybrain/client.ts                         server-side MAS client (timeouts, no secrets)
app/api/fusarium/flybrain/[...path]/route.ts   owner-gated allow-listed BFF proxy → MAS /api/flybrain/*
components/itdx/ITDXFlyBrainPanel.tsx          panel inside the ITDX application (session, activity, detections, nav)
hooks/use-flybrain-session.ts
__tests__/lib/flybrain/*.test.ts
```

## 4. Engine semantics (port of the Shiu et al. LIF, MIT model.py)

Per time step `dt = 0.1 ms` (state arrays are float32 of length N):

```
refrac    = where(spikes_prev > 0, 0, refrac + 1)
gate      = (refrac >= refrac_steps)              # refrac_steps = round(2.2/dt) = 22, but 0 for externally driven neurons
g_new     = g * (1 - dt/tauSyn) + delayed_input * gate
delayed_input buffer: circular, steps_delay = int(1.8/dt) = 18; push this step's recurrent_input, pop the one from 18 steps ago
v         = v + w_scale * poisson_spikes * scale_poisson      # voltage_stim, only for driven neurons
v         = v + (dt/tauMem) * (g_old - (v - vRest))           # NOTE: uses g BEFORE this step's synaptic update
spike     = v > vThreshold
v         = where(spike, vReset, v)
g_new     = where(spike, 0, g_new)
recurrent_input[post] = w_scale * Σ_{pre spiked} W[post, pre]   # event-driven: gather CSC columns of the spiking pre neurons; skip silenced
```

Parameters: `tauSyn=5 ms, tDelay=1.8 ms, v0=vReset=vRest=-52 mV, vThreshold=-45 mV, tauMem=20 ms, tRefrac=2.2 ms, scalePoisson=250, wScale=0.275`. Poisson drive: `bernoulli(rate_hz * dt / 1000)`.

`FlyBrainEngine` API (numpy backend is mandatory; torch backend optional and interface-identical):

```python
engine = FlyBrainEngine(connectome, params=LIFParams(), dt_ms=0.1, seed=None, backend="auto", subgraph=None)
engine.n_neurons; engine.t_ms; engine.step_count; engine.backend  # "numpy" | "torch:cpu" | "torch:cuda"
engine.set_rates(indices, rate_hz)        # persistent Poisson drive (indices in engine-local index space)
engine.clear_rates(indices=None)
engine.silence(indices); engine.unsilence(indices)
engine.step() -> np.ndarray[int]          # local indices that spiked this step
engine.run(duration_ms, record=True) -> (times_ms: np.ndarray, indices: np.ndarray)   # concatenated
engine.mean_rates(indices, window_ms) -> float  # Hz per neuron averaged over the last window (uses the ring spike history)
engine.recent_spikes(limit) -> (times_ms, indices)
engine.snapshot() -> dict                 # counts, t_ms, backend, active neurons in window
engine.reset()
engine.to_global(indices) / engine.to_local(global_indices)   # subgraph mapping (identity when no subgraph)
```

Subgraph mode (`SubgraphSpec`): induced sub-matrix on neurons within `hops` (forward and backward) of the seed groups with `|w| >= min_weight`, capped at `max_neurons` (highest total |w| kept). Local/global index maps are exposed. Default sessions run the **full** brain.

## 5. Atlas

`config/flybrain_atlas.yaml`: `groups` (name → role, description, flywire_ids) plus `derived` groups computed against the loaded connectome (`downstream_of`, `hops`, `min_weight`, `exclude`, `intersection`) and a `sensorimotor` mapping (`inputs`: forward/left/right/attract → groups; `readouts`: forward/turn_left/turn_right/feeding → groups). Missing ids (not in the completeness file) are listed in `missing_ids`, never silently dropped.

## 6. Encoders (Observation → drive)

All encoders return `Dict[group_name, rate_hz]` and never invent detections.

| kind | payload | mapping |
|---|---|---|
| `detections` | `DetectionFrame` dict | For each detection: horizontal position `cx = (x1+x2)/2 / frame_w` (or `bearing_deg` if present, relative to heading). Left half → `inputs.left` (`p9_left`) rate += k·conf·area, right half → `inputs.right`. Categories in `attract_categories` (default: food, fungus, plant) → `inputs.attract` (`sugar_grn`). Rates clipped to `max_rate_hz` (default 200). No detections → all zero (no drive). |
| `telemetry` | `{heading_deg, target_bearing_deg?, speed_kn?, distance_to_goal_m?}` | heading error → left/right drive proportional to |error| (≤ 100 Hz), forward drive from distance_to_goal (0 when arrived). |
| `earthsim` | ITDX slice `{ao:{bbox,center}, assets:[...], devices:[...]}` + `focus` point | asset/device bearings relative to AO center, same left/right rule; density → forward. |
| `nlm` | `{model_loaded: bool, confidence?: float, prediction?: str}` | `model_loaded=false` → no drive and note `UNQUALIFIED`; loaded → `attract` drive scaled by usable confidence (`is_usable_nlm_confidence`), never the 0.85 stub. |
| `itdx_slice` | same as earthsim | same encoder |
| `raw_rates` | `{group: hz}` | pass-through (validated against atlas) |

## 7. Decoders (rates → action)

`LocomotionDecoder(readouts)`:
```
fwd  = mean rate of readouts.forward
left = mean rate of readouts.turn_left, right = mean rate of readouts.turn_right
turn = (right - left) / (right + left + eps)        # in [-1, 1], negative = left
forward = clip(fwd / fwd_ref, 0, 1)                 # fwd_ref = 50 Hz default
heading_delta_deg = turn * max_turn_deg (default 30)
throttle_pct = forward * 100
confidence = 1 - exp(-(spike_count_window) / 200)   # 0 when the brain is silent
kind = "locomotion" if forward > 0.05 or |turn| > 0.05 else "none"
```
`PopulationClassifier`: nearest-centroid over rate vectors of atlas groups; centroids are learned only from labelled ticks in this session (`label` in Observation payload) — with no labels it returns `None`, never a guess.

## 8. Navigation

`OccupancyGrid(center: GeoPoint, size_m, cell_m)` in a local ENU frame (equirectangular, fine at ≤ 5 km). `add_perimeter(polygon lon/lat)`, `add_point(lat, lon, radius_m)`, `plan(start, goal, turn_bias) -> NavPath` using A* (8-neighbour, diagonal cost √2); `turn_bias ∈ [-1,1]` adds `bias_weight·|Δheading|` on moves that turn against the brain's preferred side. Output waypoints are decimated (Douglas–Peucker, ≤ 12 points) and include a GeoJSON LineString. Infeasible (goal blocked / unreachable) → `feasible=False`, `waypoints=[]`, honest `note`.

## 9. Vision (YOLO26 + SAHI)

`FlyBrainDetector`:
1. Try `from ultralytics import YOLO`; weights `FLYBRAIN_YOLO_WEIGHTS` (default `yolo26n.pt`; ultralytics downloads it on first use when the host has internet — an air-gapped VM reports `available=False` with the reason).
2. SAHI: try `sahi` (`AutoDetectionModel.from_pretrained(model_type="ultralytics", ...)` + `get_sliced_prediction`); if `sahi` is absent, use `vision/slicing.py` (tiles of `slice`×`slice` with `overlap`, per-tile YOLO, merge with class-aware NMS at IoU 0.5). `DetectionFrame.sahi=True`, `slices=n`, `sahi_impl` recorded in health.
3. `RemoteDetector(url)`: GET snapshot (Jetson `:8792/detect` shape: `{ok, ts, engine, device, detections:[{source, class, confidence, bbox:[x1,y1,x2,y2]}], frames:{source:{frameW,frameH}}}`) and POST image if the remote accepts it.
4. Missing everything → `DetectionFrame(available=False, detections=[], note=reason)`; the API returns **503** with the same reason. **No synthetic boxes, ever.**

`ontology.py`: COCO/OpenImages-style class → `category` (person, vehicle, vessel, aircraft, animal, plant, fungus, food, structure, object). Animal/plant/fungus classes get an async MINDEX taxon lookup (`GET {MINDEX_API_URL}/api/mindex/taxa?scientific_name=<cls>&limit=1`, 2 s timeout, LRU cached); unreachable → `taxon=None` with `note`. Geometry: `bearing_deg = heading + (cx - 0.5) * hfov`; `range_m` only if measured (payload) or estimated from bbox height and a per-category height prior (`range_source="estimate"`); `location` from bearing+range; `perimeter` = ground footprint polygon (4 corners) only when range is known; `pathway` = the track's location history (`TrackMemory`, keyed by `track_id`).

`bluesight_provider.py`: `Yolo26SahiProvider` and `FlyBrainVisionProvider` implementing `mycosoft_mas.bluesight.providers.DetectionProvider` (`detect(packet) -> List[BlueSightDetection]`) using `packet.frame_ref` (path or URL) — registered into `ProviderRegistry` under `"yolo26_sahi"` and `"flybrain_vision"` **only via** `register_flybrain_providers(registry)` (no edits to bluesight files).

## 10. Runtime and API

`FlyBrainRuntime` (module singleton, `get_runtime()`): loads the connectome lazily once (`Connectome` cached), keeps one `FlyBrainEngine` per session, runs `engine.run()` in `asyncio.to_thread`, guards with a per-session lock, records ticks as JSONL under `FLYBRAIN_RECORD_DIR/<session_id>/ticks.jsonl` when `record=True`, and owns autopilot tasks (`asyncio.create_task`, period ≥ 0.2 s, stops on session delete / error).

`/api/flybrain` (router prefix, tag `flybrain`):

| Endpoint | Method | Returns |
|---|---|---|
| `/health` | GET | `FlyBrainHealth` — connectome loaded?, vision available?, backend, sessions |
| `/connectome/manifest` | GET | `ConnectomeManifest` |
| `/atlas` | GET | `AtlasSummary` (group sizes, missing ids, sensorimotor map) |
| `/sessions` | GET / POST(`SessionConfig`) | list / `SessionInfo` (503 when connectome missing, with fetch instructions) |
| `/sessions/{id}` | GET / DELETE | `SessionInfo` |
| `/sessions/{id}/tick` | POST(`TickRequest`) | `TickResult` |
| `/sessions/{id}/stimulate` | POST(`List[StimulusCommand]`) | `BrainState` |
| `/sessions/{id}/state` | GET | `BrainState` |
| `/sessions/{id}/spikes?limit=` | GET | `SpikeRecord` |
| `/sessions/{id}/reset` | POST | `SessionInfo` |
| `/sessions/{id}/autopilot` | POST `{enabled, period_s}` | `SessionInfo` |
| `/vision/health` | GET | `VisionHealth` |
| `/vision/detect` | POST multipart `image` **or** JSON `{image_b64 \| image_url, sahi?, conf?, pose?:{lat,lon,heading_deg}}` | `DetectionFrame` (503 when unavailable) |
| `/itdx/channels` | POST `{map_slice, session_id?, detections?}` | `{schema_version, channels:{pathways,navigation,biology,information}, nav, session_id}` |
| `/nlm/observation` | POST `{session_id, cutoff?}` | `CausalObservationPipeline.process` result + envelope |
| `/droid/{device_id}/guidance` | GET `?session_id=` | guidance payload (dry-run, never actuates) |

Mounted from `myca_main.py` inside `try/except ImportError` exactly like ITDX. `FlyBrainAgent` (agent_id `flybrain`) exposes `process_task` types `status | create_session | tick | detect | navigate | assess_situation | couple_nlm | stop_session` and is `_safe_import`ed in `agents/__init__.py`.

## 11. Honesty / safety rules for this module

1. No connectome on disk → health `unavailable`, sessions 503, agent returns `status="unavailable"`. Never a toy fallback in production paths (tests use an explicit in-memory synthetic connectome fixture only).
2. No detector → 503 / `available=False`. Never synthetic detections.
3. Droid actuation is triple-gated: session `dry_run=False` **and** env `FLYBRAIN_DROID_ACTUATE=1` **and** AVANI `approved=True` (`Proposal(source_agent="flybrain-droid", action_type="navigation", risk_tier=MEDIUM, reversibility=0.8)`). Default is dry-run; the guidance payload is still returned.
4. NLM coupling never emits a probability. Population rates go in as `formspace.observation/v1` (`origin="SYNTHETIC"` — the FormSpace contract's word for non-measured input); forecasts stay `UNSUPPORTED` unless the scientific NLM is loaded.
5. ITDX rows use `SCORED` only for quantities the module computed from real geometry this tick (path feasibility, blocked fraction, detection counts) and say what `p` means in `note`; everything else is `NOT_SUPPLIED`/`UNQUALIFIED`.
6. No HTTP self-calls to MAS from inside MAS (the ITDX deadlock lesson). Plugs call in-process functions.
7. VM addresses come only from env with the documented defaults (MINDEX 189:8000, MAS 188:8001). Nothing in this module changes any existing default.

## 12. Deployment

```
# MAS VM 188 (one time): fetch the connectome onto the NAS and convert to npz
poetry run python scripts/flybrain_fetch_connectome.py --dest /mnt/mycosoft-nas/models/flybrain
# env
FLYBRAIN_DATA_DIR=/mnt/mycosoft-nas/models/flybrain
FLYBRAIN_BACKEND=numpy            # or torch on GPU VMs
FLYBRAIN_YOLO_WEIGHTS=yolo26n.pt  # or a Mycosoft species model
FLYBRAIN_REMOTE_DETECTOR_URL=http://<jetson>:8792/detect   # optional
FLYBRAIN_DROID_ACTUATE=0          # keep 0 until pool-test sign-off
# then the standard MAS docker rebuild from CLAUDE.md
```
Website: `FLYBRAIN_ENABLED=1` is not needed — the panel renders honest status from `/api/fusarium/flybrain/health` and only owners reach it.

---

## 13. Verification record (14 Sep 2026, build host, CPU only)

Everything below was executed on this session's build container against the real FlyWire v783 files (fetched from the upstream repo, SHA-256 verified, converted to npz). Numbers are measurements, not targets.

| Check | Result |
|---|---|
| `pytest tests/test_flybrain_*.py` (no connectome on disk) | **170 passed, 6 skipped** (skips = real-data tests) |
| same with `FLYBRAIN_DATA_DIR` pointing at the v783 files | **176 passed, 0 skipped** |
| CI-equivalent full MAS suite (`poetry run pytest tests/ …` ignore list from `ci.yml`) | **1467 passed, 30 skipped** |
| `black --check`, `isort --check-only`, `flake8 --select=E9,F63,F7` on all FlyBrain files | clean |
| `import mycosoft_mas.core.routers.flybrain_api` under `MAS_LIGHT_IMPORT=1`, torch/ultralytics/sahi/PIL absent | ok, 18 routes |
| Website `npx jest --env=node __tests__/lib/flybrain` | **23 passed** (4 suites) |
| Website `npx tsc --noEmit` | 213 errors, **0** in FlyBrain files or `ITDXApplication.tsx`; the same 213 exist on pristine `main` (`64a8950`) |
| Connectome load (npz + csv) | 138,639 neurons, 15,091,983 synapses, ~3.3 s |
| Full-brain engine throughput (numpy event-driven, this CPU) | ~2,100 steps/s ⇒ one 50 ms window in 0.15–0.26 s wall (realtime ratio ≈ 0.2) |
| Sugar experiment through the router (`sugar_grn` @ 200 Hz, 3 × 50 ms) | 281–300 active neurons per window, `sugar_downstream` 70–80 Hz, SEZ types `usnea`, `tinctoria`, `roundup`, `G2N_1` active — the feeding circuit, as in Shiu et al. |
| Detection encoding (large left box conf 0.9, small right box conf 0.4) | `p9_left` driven at 41.7 Hz vs `p9_right` 0.46 Hz; decoded `turn` = 0 until readouts exceed the 5 Hz activity gate, then **−0.65 (left)** by the third window |
| `/itdx/channels` from a non-navigating session | `pathways`/`navigation` NOT_SUPPLIED, `biology` SCORED p=0/2 with explanatory note, `information` sample_count=2 |
| `/nlm/observation` | `formspace.observation/v1` envelope accepted by `CausalObservationPipeline` (`status: accepted`), duplicate `root_evidence_id` refused on replay |
| `/droid/{id}/guidance` | dry-run, `actuated=false`, `actuated_by_this_call=false`, guidance derived from the last action |
| `earthsim` plug, Fort Stewart slice | feasible A* path, 4 waypoints; autopilot at 0.5 s period ran 5 ticks in 2.5 s and stopped on disable |
| `droid` plug with no device registered and no detector | honest notes (`telemetry unavailable`, `detections unavailable … no boxes invented`), `nav_feasible=false`, nothing actuated |
| `/vision/detect` with no ultralytics and no remote URL | **503** `detector_unavailable` with the reason |

### Review loop

Five adversarial reviewers (LIF port vs. reference, honesty/no-fake-data, cross-layer contracts, security/ops, tests + end-to-end) produced 26 findings; each was voted on by two or three independent refuters (47 votes upheld, 5 refuted). All confirmed findings were fixed with regression tests, including: per-index `set_rates` ordering bug; synaptic delay ring aligned to the Brian2 reference; `health()` no longer claims YOLO availability before weights exist; `image_url` SSRF guard (public addresses only, no redirects, size cap, explicit allow-list env `FLYBRAIN_IMAGE_URL_ALLOW_HOSTS`); `dt_ms` lower bound so one tick is hard-capped at 500,000 steps; session-slot reservation under the lock; guidance endpoint no longer overwrites the last tick's actuation record; ITDX rows refuse to label a different AO than the one the session planned on; NLM envelopes are not emitted for sessions that never ticked; decoder activity gate (`min_turn_hz`) so a single stray spike cannot saturate `turn`; bearing-only detections without a measurable bbox produce no drive; agent resource usage measured with psutil or reported as not measured; BlueSight provider surfaces detector failures in packet metadata instead of a silent empty list; website hook no longer invents a `running` status; panel gates on `health.status`, not on the lazy `connectome.loaded` flag.

## 14. Known limitations and next steps

- **Torch backend untested here** (no torch in the build container). `backend="auto"` picks torch only when CUDA is present; smoke-test `FLYBRAIN_BACKEND=torch` on the GPU Legion before relying on it.
- **YOLO26 / SAHI library paths untested here** (ultralytics and sahi are not installed in the container). The in-house slicing/merge, the remote Jetson `/detect` mapping, ontology geometry and the BlueSight adapters are unit-tested; run `/api/flybrain/vision/health` and one `/vision/detect` on the Jetson or GPU VM to validate the library path. Install: `pip install ultralytics sahi pillow`.
- **Atlas coverage:** 128 SEZ ids from the paper's `sez_neurons.pickle` are not in the v783 completeness file; they are listed under `missing_ids`, not dropped. No visual-system neuron groups are shipped yet — add FlyWire cell-type ids to `config/flybrain_atlas.yaml` to give the module real visual input populations.
- **Sensorimotor mapping is a demonstration choice.** Driving P9 from detection position and reading turn from P9 downstream partners is configuration, not a biological claim (atlas `sensorimotor.note`).
- **Droid actuation stays dry-run** until the Psathyrella pool-test sign-off; then set `FLYBRAIN_DROID_ACTUATE=1` and create the session with `dry_run=false`. AVANI still has to approve every actuation.
- **FlyWire data terms** (CC BY-NC 4.0 public release at time of writing) need FlyWire's permission for commercial use; the data never enters a Mycosoft repo.
- **Website type-check baseline** is 213 pre-existing errors on `main`; none are in FlyBrain files.
- Not touched in this change: `mindex`, `mycobrain`, `AgaricFlight`, `MycaControl`, `FlySwarm` (the last is an unrelated wallet-intelligence tool that only borrows the fly-brain metaphor).
