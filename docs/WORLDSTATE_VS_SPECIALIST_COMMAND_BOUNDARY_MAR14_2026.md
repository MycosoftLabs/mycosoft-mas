# Worldstate vs Specialist Command Boundary — Mar 14, 2026

**Status:** Canonical  
**Related:** CREP_COMMAND_CONTRACT_MAR13_2026, GROUNDING_ARCHITECTURE_LOCKED_MAR14_2026, WORLDVIEW_SEARCH_EXPANSION_PLAN

## Purpose

This document defines the **boundary between passive worldstate awareness (read-only)** and **specialist command surfaces (action APIs)**. Search, CREP, Earth Simulator, MYCA context, and agent reasoning all consume the same worldstate read contract; commands that change state or trigger actions remain specialist.

---

## Two Layers

| Layer | Contract | Purpose |
|-------|----------|---------|
| **Passive awareness** | Worldstate read API | What the world contains — hazards, moving entities, environment, devices, biodiversity. Used for search ranking, widget selection, MYCA context, agent grounding. |
| **Specialist commands** | CREP, Earth2, other action APIs | Execute actions — fly map, show layer, run forecast, apply filter. Used by voice handlers, tools, and direct user commands. |

---

## Passive Awareness: Worldstate Read API

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/myca/world` | GET | Full worldstate snapshot |
| `/api/myca/world/summary` | GET | Source counts, overall status |
| `/api/myca/world/sources` | GET | Per-source status, freshness, errors |
| `/api/myca/world/region` | GET | Region-specific summary (lat, lon, radius_km) |
| `/api/myca/world/diff` | GET | Diff since last turn or timestamp |

**Ownership:** MAS `WorldModel` and canonical `WorldState`/`SelfState`. No mock data. Degraded or unavailable states are explicit.

**Consumers:**
- Website search (ranking, widget selection)
- CREP dashboard (optional source diagnostics)
- Earth Simulator (optional context overlay)
- MYCA and AVANI (grounding, suggestion generation)
- Future agent tools (awareness before action)

---

## Specialist Commands: Action APIs

| Surface | Contract Doc | Purpose |
|---------|--------------|---------|
| **CREP map** | CREP_COMMAND_CONTRACT_MAR13_2026 | `flyTo`, `showLayer`, `applyFilter`, `setTimeCursor`, etc. |
| **Earth2** | CREP_COMMAND_CONTRACT_MAR13_2026 (Earth2 section) | `run_forecast`, `run_nowcast`, `show_forecast`, etc. |
| **Voice** | `POST /voice/command` | PersonaPlex → MAS → `frontend_command` |
| **Future** | `POST /api/crep/command` | Autonomous MYCA, tool bus |

**Rule:** Specialist commands remain action-only. They do not expose worldstate; they act on it. Worldstate read API provides awareness; CREP/Earth2 commands provide control.

---

## Boundary Rules

1. **Worldstate API is read-only.** No mutations. No side effects.
2. **CREP and Earth2 commands stay specialist.** Do not merge into worldstate routes.
3. **Search and widgets use worldstate for awareness.** Widget selection, ranking, and empty states derive from worldstate summary and source metadata.
4. **MYCA context uses worldstate for grounding.** ExperiencePacket and live-context build on canonical WorldState and SelfState.
5. **No mock data.** Empty, degraded, or stale states must be explicit. Never substitute fake content.

---

## Implementation

- MAS router: `mycosoft_mas/core/routers/worldstate_api.py`
- Website proxy: `website/app/api/mas/world/[[...path]]/route.ts`
- Website client: `website/lib/mas/worldstate-client.ts`
- API URLs: `MYCA_ENDPOINTS.WORLD_*` in `website/lib/config/api-urls.ts`

---

## Cross-References

- CREP_COMMAND_CONTRACT_MAR13_2026 — specialist command schema
- GROUNDING_ARCHITECTURE_LOCKED_MAR14_2026 — WorldState, SelfState, ExperiencePacket
- Worldview Search Expansion Plan — full architecture
