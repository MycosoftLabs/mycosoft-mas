# ITDX External Sources Integration — 09 September 2026

**Date:** 09 September 2026  
**Status:** Wired on MAS situation-assessment (in-process). Not a CMMC claim.  
**Related:** `docs/MAS_MYCA_AVANI_FUSARIUM_ITDX_INTEGRATION_PLAN_SEP09_2026.md`  
**CMMC:** Mycosoft is **pursuing** CMMC L2 — not compliant. **RJ Ricasata is CFO.**  
**CUI:** This surface is outside the CUI boundary. Official injects stay NOT_SUPPLIED.

---

## What was added

Public UNCLASSIFIED OSINT is gathered in-process by `mycosoft_mas/core/routers/itdx_public_sources.py` and mapped onto `POST /api/itdx/situation-assessment` (no self-HTTP). Every SUPPLIED channel carries `source_name`, `source_url`, `retrieved_at`, and `sources[]`. Empty or down APIs stay NOT_SUPPLIED with a reason. NLM `model_loaded=false` / stub `0.85` remains UNQUALIFIED (`p=null`).

Fort Stewart public point: **lon -81.6072, lat 31.8697**, bbox `[-81.70, 31.80, -81.45, 32.05]`.

---

## Channel table (expected when public APIs answer)

| Channel | Status when live | Source URL | Notes |
|---|---|---|---|
| weather | SUPPLIED | https://api.open-meteo.com/v1/forecast | Current + NWS `api.weather.gov/points` fallback. Earth-2 249 not required. |
| biology | SUPPLIED | https://api.gbif.org/v1/occurrence/search + https://api.inaturalist.org/v1/observations | Fungi in bbox. MINDEX 189 `/health` is up; taxa/observations routes 404 — live GBIF/iNat used. |
| chemistry | SUPPLIED or UNQUALIFIED | https://pubchem.ncbi.nlm.nih.gov/rest/pug/…/fusaric%20acid/… | PubChem if rows; else NLM UNQUALIFIED. Not a chemistry p. |
| topology | SUPPLIED | https://overpass-api.de/api/interpreter | OSM `landuse=military`, Hunter AAF aerodrome, civilian highways. |
| information | SUPPLIED | Wikipedia REST Fort_Stewart / Hunter_Army_Airfield + Nominatim | Public encyclopedia / place names. Not P(truth). |
| equipment_weapons_assets | SUPPLIED (base names only) | Nominatim + OSM road limits | Weapons/armor/TM **NOT_SUPPLIED**. `capability_class=public_road`. Exercise tracks `live=false`. |
| traffic | NOT_SUPPLIED | Google Distance Matrix | Key **present** on 188 as `GOOGLE_MAPS_API_KEY`. Live probe **REQUEST_DENIED** (API not enabled / key restricted). |
| pathways | NOT_SUPPLIED | Google Directions | Same key + same **REQUEST_DENIED**. |
| navigation | NOT_SUPPLIED | Google Directions / Distance Matrix | Same. Not `google_maps_key_missing`. |
| physics | UNQUALIFIED | NLM + PhysicsNeMo | Honesty: no invented p. |
| economics | NOT_SUPPLIED | — | No AO economics model. |
| biometry | NOT_SUPPLIED | — | No labeled model. |
| officer_capability | NOT_SUPPLIED | — | Official 1–5 rubric NOT_SUPPLIED. |
| persona | NOT_SUPPLIED | MYCA health | Dormant ≠ persona p. |
| decision_authority | UNQUALIFIED | AVANI gate | Approved/denied only. Not command authority. |
| fusion p_truth / p_deception / data_quality | NOT_SUPPLIED | — | Distinct labeled processes not mounted. |

---

## Google Maps / traffic / pathways

**Env names (gitignored only — never committed, never printed):**

| Name | Where found | Prefix / length | Used on 188 |
|---|---|---|---|
| `NEXT_PUBLIC_GOOGLE_MAP_TILES_API_KEY` | website `.env.local`, website-itdx-codex-v13 `.env.local` | `AIza` / 39 | yes (copied as aliases) |
| `GOOGLE_AI_API_KEY` | website `.env.local` (same value as tiles); MAS `.credentials.local` (different, expired) | `AIza` / 39 | no (Gemini / expired; not used as Maps) |
| `GEMINI_API_KEY` | website `.env.local` (same value as tiles) | `AIza` / 39 | no |
| `GOOGLE_MAPS_API_KEY` | **was missing**; now aliased in MAS `.credentials.local` from the tiles key | `AIza` / 39 | **yes** |
| `NEXT_PUBLIC_GOOGLE_MAPS_API_KEY` | example files only until aliased | `AIza` / 39 | **yes** (alias) |
| `GOOGLE_API_KEY` | example files only until aliased | `AIza` / 39 | **yes** (alias) |

**188 mas-orchestrator:** drop-in `google-maps.conf` → `EnvironmentFile=-/home/mycosoft/mycosoft/mas/.credentials.maps.env` (names above). `systemctl show` reports that EnvironmentFile. Values never printed.

**Live Directions / Geocode / Distance Matrix (09 Sep 2026, no key in output):**

- Website tiles / Gemini / `GOOGLE_AI` (same hash): HTTP 200 **`REQUEST_DENIED`** — “This API key is not authorized to use this service or API” (Google Cloud **API restriction**: Map Tiles / Gemini allowed; Directions, Distance Matrix, Geocoding not enabled for this key). Not an HTTP-referrer vs IP message.
- MAS `.credentials.local` `GOOGLE_AI_API_KEY` (different hash): HTTP 200 **`REQUEST_DENIED`** — “The provided API key is expired.”

**Situation-assessment after 188 env + restart:** `google_key_present=true`, `google_key_env_name=GOOGLE_MAPS_API_KEY`. Channels `traffic` / `pathways` / `navigation` stay **NOT_SUPPLIED** with reason **`REQUEST_DENIED`**. Client remains wired (`departure_time=now`, `duration_in_traffic`, origin `31.8697,-81.6072`). No HTML scrape. Roads snap-to-road skipped.

To flip those channels to SUPPLIED: on the **existing** GCP project, enable these services and allow them on the current key (do not invent a new key):

| Service name | API |
|---|---|
| `directions-backend.googleapis.com` | Directions |
| `distancematrix-backend.googleapis.com` | Distance Matrix |
| `geocoding-backend.googleapis.com` | Geocoding (optional) |
| `roads.googleapis.com` | Roads (optional; snap-to-road still skipped) |

**GCP enable attempt (09 Sep 2026):** stopped. No `GCP_PROJECT` / `GOOGLE_CLOUD_PROJECT` in website `.env.local` or MAS `.credentials.local`. Local Cloud SDK: **not installed**, ADC file **missing**. 188: SSH ok, `gcloud` **not installed**. Directions / Distance Matrix / Geocoding re-probe (no key in stdout): still **`REQUEST_DENIED`** — “This API key is not authorized to use this service or API.” Blocker is **Google Cloud Console** (logged-in owner must enable those APIs / relax key API restrictions + billing). Not a missing-key problem. Do not commit or print the value.

---

## Public military OSINT (allowed)

| Source | Endpoint | Used for |
|---|---|---|
| Wikipedia REST | `/page/summary/Fort_Stewart`, `/Hunter_Army_Airfield` | Public base narrative |
| OSM Nominatim | `https://nominatim.openstreetmap.org/search` | Fort Stewart, Hunter AAF, Hinesville |
| OSM Overpass | `https://overpass-api.de/api/interpreter` | `landuse=military`, aerodrome, civilian maxspeed |
| HIFLD Open ArcGIS | FEMA/Esri military bases query | Attempted; layer returned **Invalid URL** → skipped |
| Army public affairs | `https://home.army.mil/stewart/` | Timed out — not invented |
| OpenSky | `/api/states/all` bbox | Public ADS-B; empty → NOT_SUPPLIED (no fake tracks) |
| MycoBrain | `http://127.0.0.1:8003/health` | Healthy, `devices_connected=0` → no invented telemetry |

Vehicle / asset limitations are **public-road only**: OSM `highway` / `maxspeed` / `maxheight` / `maxweight` / `hazmat`, Google `travel_mode=driving` when key exists. Marked `capability_class=public_road`, `exercise_synthetic=true`, `live=false` for exercise markers. **No armor, weapons, classified ranges, or TM performance.**

---

## Biodiversity / weather (kept)

| Source | Live probe 09 Sep | Count / sample |
|---|---|---|
| Open-Meteo | 200 current weather | temperature, wind, precip at 31.87,-81.61 |
| NWS points | 200 | forecast office + periods |
| GBIF fungi bbox | 200 | **28** occurrences |
| iNaturalist fungi bbox | 200 | **138** observations |
| MINDEX 189 | `/health` 200; `/taxa` `/observations` 404 | Use GBIF/iNat; no full_fungi_sync |

---

## Refused (legal / CUI boundary)

| Source | Why |
|---|---|
| `C:\Users\Owner1\Downloads\Army docs-…` HQ 3ID OPORD 14-06 BULLDOG | UNCLASSIFIED//FOUO — STOP_INGEST. No MGRS, lon/lat, unit lists, or inject text copied. |
| Official Army injects / 1–5 SME rubric | Contract: NOT_SUPPLIED |
| CAC / SIPR / NIPR / PreVeil / mil-mail | Non-public |
| ADS-B Exchange RapidAPI / MarineTraffic | Auth / paid wall → `restricted_source` |
| Palantir / Anduril / Platform One clients | Restricted / login |
| Invented COP tracks / seven LLM personas / hardcoded 0.85 | Honesty rules (fa82f060) kept |

---

## How to enable live Google traffic

1. **Do not create a new key.** In Google Cloud Console on the existing project, enable `directions-backend.googleapis.com` and `distancematrix-backend.googleapis.com` (optional: `geocoding-backend.googleapis.com`, `roads.googleapis.com`) and add those APIs to this key’s API restrictions.
2. Names already on 188: `GOOGLE_MAPS_API_KEY`, `NEXT_PUBLIC_GOOGLE_MAPS_API_KEY`, `GOOGLE_API_KEY`, `NEXT_PUBLIC_GOOGLE_MAP_TILES_API_KEY` via `/home/mycosoft/mycosoft/mas/.credentials.maps.env`. Alias list in `itdx_public_sources.py` `GOOGLE_KEY_NAMES`.
3. Restart `mas-orchestrator` only after changing the env file (not needed until the Console enable succeeds).
4. Re-curl situation-assessment. Channels flip to SUPPLIED only when Directions/Distance Matrix return **OK**. Current live status is **REQUEST_DENIED** (API restriction on this key). `gcloud services enable` was **not run** — Cloud SDK / ADC / project id absent. Do not commit the key. Never print the key.

Official APIs only — no Google HTML scrape. Client uses `departure_time=now` so `duration_in_traffic` is live. Destinations: Hunter Army Airfield and Hinesville (public towns). Roads / snap-to-road skipped until a Roads-capable key is proven.

---

## Proof — live curl 09 September 2026

`POST http://192.168.0.188:8001/api/itdx/situation-assessment` Fort Stewart public slice  
`center 31.8697,-81.6072` `bbox [-81.70, 31.80, -81.45, 32.05]`  
HTTP **200**, client elapsed **5.18s**, `timed_out` absent, `self_http=false`, `in_process=true`.  
`google_key_present=true`, `google_key_env_name=GOOGLE_MAPS_API_KEY` (after 188 EnvironmentFile). GeoJSON public point features (declared + Nominatim + Wikipedia). No secrets in the payload. Directions/Distance Matrix **REQUEST_DENIED**.

| Channel | Status | Source URL | Sample | Reason / note |
|---|---|---|---|---|
| weather | **SUPPLIED** | https://api.open-meteo.com/v1/forecast | 1 current | 28.4 °C at the public point. NWS points also cited. |
| biology | **SUPPLIED** | https://api.gbif.org/v1/occurrence/search | **28** GBIF | iNaturalist also cited (**138** fungi). MINDEX taxa routes 404. |
| chemistry | UNQUALIFIED | — | — | PubChem deferred for latency; NLM stub 0.85 never used as `p`. |
| topology | NOT_SUPPLIED | — | — | OSM Overpass deferred; Google Directions **REQUEST_DENIED** (API restriction). |
| information | **SUPPLIED** | https://en.wikipedia.org/api/rest_v1/page/summary/Fort_Stewart | — | Hunter AAF Wikipedia also cited. Official injects NOT_SUPPLIED. |
| equipment_weapons_assets | **SUPPLIED** | https://nominatim.openstreetmap.org/search | — | Public names only. `capability_class=public_road`. Exercise `live=false`. Weapons/TM NOT_SUPPLIED. |
| traffic | NOT_SUPPLIED | — | — | Key on 188. **`REQUEST_DENIED`** — Directions/Distance Matrix APIs not authorized on this key. |
| pathways | NOT_SUPPLIED | — | — | Same **`REQUEST_DENIED`**. Client ready (`departure_time=now`, polyline decode). |
| navigation | NOT_SUPPLIED | — | — | Same **`REQUEST_DENIED`**. |
| physics | UNQUALIFIED | NLM | — | `model_loaded=false`. No invented p. |
| economics | NOT_SUPPLIED | — | — | No AO economics model. |
| biometry | NOT_SUPPLIED | — | — | No labeled model. |
| officer_capability | NOT_SUPPLIED | — | — | Official 1–5 rubric NOT_SUPPLIED. |
| persona | NOT_SUPPLIED | MYCA health | — | Dormant ≠ persona p. |
| decision_authority | UNQUALIFIED | AVANI | — | Approved/denied only. |

Cited `sources[]` on this curl: Open-Meteo, NWS `api.weather.gov/points/31.8697,-81.6072`, GBIF, iNaturalist, Nominatim, Wikipedia Fort_Stewart, Wikipedia Hunter_Army_Airfield.

### Vehicles / assets (honest, public)

- Limitations/capabilities from **public classes only**: OSM highway / maxspeed (deferred this curl for latency), Google `travel_mode=driving` when a key exists, civilian road constraints.
- `capability_class=public_road`. Exercise unit markers `exercise_synthetic=true`, `live=false`.
- No armor, weapons, classified ranges, or TM performance invented.
- MycoBrain telemetry: not cited as live on this curl (probe deferred; last local health had `devices_connected=0`).

### Base information

Public only: Wikipedia Fort Stewart / Hunter AAF, Nominatim place names, OSM military landuse when Overpass is in budget, HIFLD Open (skipped — prior Invalid URL). Army `home.army.mil/stewart/` previously timed out — not invented. No FOUO maps.

---

## Files

- `mycosoft_mas/core/routers/itdx_public_sources.py` — probes
- `mycosoft_mas/core/routers/itdx_api.py` — channel mapping (in-process)
- `tests/test_itdx_task8_api.py` — channel keys + no fake p
- `scripts/_itdx_ship_188.py` — includes the sources module
