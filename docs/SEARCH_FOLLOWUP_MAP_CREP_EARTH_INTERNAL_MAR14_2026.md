# Search Follow-Up: Map/CREP Full-Screen, Earth Simulator, Internal Answers (Mar 14, 2026)

**Status:** Planned (deferred from Doable Search Rollout)  
**Related:** `docs/DOABLE_SEARCH_ROLLOUT_COMPLETE_MAR14_2026.md`

## Scope

Three follow-up workstreams identified after the Doable Search Rollout. Not required for rollout completion; to be scheduled separately.

### 1. Map/CREP full-screen experience

- Provide full-screen or expanded map view for CREP/worldview results (flights, vessels, satellites).
- Ensure widget registry and canvas support a dedicated map/CREP view mode.
- Align with CREP dashboard and OEI APIs; consider route `/search?view=map` or modal full-screen.

### 2. Earth Simulator naming and UX

- Standardize naming: "Earth Simulator" vs "Earth2" vs "Earth Intelligence" across website and MAS.
- Ensure search result buckets and widget labels use one canonical name.
- Document in widget registry and UX copy.

### 3. Internal-only answers

- Option to mark answers as internal-only (e.g. for staff or authenticated users) so they are not surfaced to anonymous users.
- May require MINDEX schema extension (e.g. `visibility` or `audience` on answer_snippet/qa_pair) and website filtering by auth.

## Completion criteria (when implemented)

- Map/CREP: Full-screen or expanded map available from search results; no regressions to current widget behavior.
- Earth Simulator: Single canonical name in UI and docs; registry updated.
- Internal answers: Schema and API support; website filters by auth when configured.

## References

- Doable Search Rollout completion: `docs/DOABLE_SEARCH_ROLLOUT_COMPLETE_MAR14_2026.md`
- Widget registry: `website/lib/search/widget-registry.ts`
- CREP/OEI: CREP dashboard and worldstate docs
