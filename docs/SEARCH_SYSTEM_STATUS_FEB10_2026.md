# Search System Status — Feb 10, 2026

Status of the Mycosoft Fluid Search system: architecture, integrations, completed work, and remaining tasks. Reference for the **search-engineer** agent.

---

## Summary

- **Agent:** `.cursor/agents/search-engineer.md`
- **Route:** `/search` (freemium: 10/day, 20 max results)
- **Repos:** Website (primary), MINDEX, MAS (MYCA)

---

## Architecture

```
User → SearchContext → /api/search/unified
  → MINDEX (189:8000) + iNaturalist + NCBI + PubChem + CrossRef/OpenAlex
  → Background ingest to MINDEX
  → Widgets: Species, Chemistry, Genetics, Location, Research, AI, News, etc.
```

---

## Integrations

| System | Role | Endpoints |
|--------|------|-----------|
| **MINDEX** | Primary data (species, compounds, genetics, research) | `/api/mindex/unified-search`, `/species/detail`, `/compounds/detail`, `/genetics` |
| **MYCA (MAS)** | AI chat, intention events, consciousness | `/api/myca/consciousness/chat`, `/api/myca/nlq`, `/api/myca/intention` |
| **NLM** | Device/signal analysis (FCI dashboard) | `/api/fci/nlm/[deviceId]` — not used by main search |
| **iNaturalist** | Live observations, taxa | REST API |
| **NCBI** | Genetics sequences | EFetch |
| **PubChem** | Compound details | REST |
| **CrossRef/OpenAlex** | Research papers | REST |

---

## Completed Work

- Location Earth: camera centering, auto-select observation, all observations on map
- Species On Earth: compact, focused, pinned card; earthSpeciesName state
- Compound→species: COMPOUND_TO_FUNGI, sourceSpecies attached when compoundFungi exists
- useSpeciesObservations: genus fallback, quality_grade relaxed
- Ganodermic acid in COMPOUND_TO_FUNGI

---

## Remaining Work

1. **Compound detail API:** Add sourceSpecies from COMPOUND_TO_FUNGI when `/api/mindex/compounds/detail` returns
2. **Genetics:** MINDEX genetics 500 (schema); verify NCBI fallback for Ganoderma/Reishi
3. **Empty-widget policy:** "Fetch from source" button on Genetics/Chemistry when empty; re-trigger search or ingest
4. **Cross-widget:** When switching species from Chemistry/Genetics, ensure Chemistry/Genetics refresh
5. **MINDEX:** Create `/api/mindex/research/search` (currently uses `/api/mindex/research?search=...`)

---

## Deployment

- **Dev:** `npm run dev:next-only` on port 3010; env: MAS_API_URL, MINDEX_API_URL
- **Sandbox:** SSH 187, git pull, docker build, restart with NAS mount, Cloudflare purge
- **Skills:** deploy-website-sandbox, setup-env-vars, start-dev-website
