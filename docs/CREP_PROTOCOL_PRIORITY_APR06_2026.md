# CREP + Protocol Stack Priority — April 6, 2026

**Date:** April 6, 2026  
**Status:** Prioritized backlog  
**Sources:** `WEBSITE/website/docs/CREP_INTEGRATION_TEST_PLAN_MAR10_2026.md`, `docs/MYCA_PROTOCOL_STACK_INTEGRATION_PLAN_FEB17_2026.md`

---

## CREP (dashboard `/dashboard/crep`)

| Priority | Work item | Notes |
|----------|-----------|--------|
| **P0** | Biodiversity/wildlife bubbles | **Done** per Mar 10 doc. |
| **P1** | Satellite imagery + Live Data | MODIS, VIIRS, AIRS, Landsat, EONET toggles; port GIBS `DeckGibsDemo` / `SatelliteTilesDemo` patterns into `CREPDashboardClient` / deck layers. |
| **P2** | Basemap switcher | Carto dark vs satellite (MapLibre style or raster). |
| **P3** | Shadowbroker + deck.gl | Usability pass on filters and layer UX per test plan §4–5. |
| **P4** | Military filter updates | Per test plan work order §6. |
| **P5** | Full integration test + doc push | Close loop on `CREP_INTEGRATION_TEST_PLAN_MAR10_2026.md`. |

**Suggested order:** P1 → P2 → P3 → P4 → P5.

---

## Protocol stack (A2A / WebMCP / UCP)

| Priority | Work item | Notes |
|----------|-----------|--------|
| **P1** | **UCP commerce routing** | Complete “UCP-first” paths where vendors expose UCP; avoid scrape when UCP exists (`MYCA_PROTOCOL_STACK_INTEGRATION_PLAN_FEB17_2026.md`). |
| **P2** | **WebMCP coverage** | Expand `navigator.modelContext` tools on high-traffic Mycosoft pages (search, notepad) per plan. |
| **P3** | **TLS + auth on A2A** | Production Agent Card `securitySchemes`, HTTPS requirement. |

**Suggested order:** P1 → P2 → P3 (security hardening last mile after features stabilize).

---

## Cross-links

- `docs/SUBAGENT_ROLES_AND_COMMANDS_FEB12_2026.md` — @crep-agent, @website-dev for CREP implementation.
