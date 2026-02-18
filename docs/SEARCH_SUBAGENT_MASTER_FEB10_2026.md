# Search Sub-Agent Master — Feb 10, 2026

Complete reference for the **search-engineer** sub-agent. Covers all work done and not done, requirements, tools, interfaces, plans, deployment, user interactions, integrations with MINDEX/MYCA/NLM, and Mycosoft apps.

---

## 1. Agent Identity

| Property | Value |
|----------|-------|
| **Agent** | `search-engineer` |
| **File** | `.cursor/agents/search-engineer.md` |
| **Status doc** | `docs/SEARCH_SYSTEM_STATUS_FEB10_2026.md` |
| **Route** | `/search` (freemium: 10/day, 20 max per `lib/access/routes.ts`) |
| **Repos** | Website (primary), MINDEX, MAS |

---

## 2. Architecture & Data Flow

```
User Query (debounced 300ms)
    → SearchContext.query
    → FluidSearchCanvas (useUnifiedSearch)
    → /api/search/unified (Website Next.js route)
        ├── MINDEX (192.168.0.189:8000) — species, compounds, genetics, research
        ├── iNaturalist — live observations, taxa, photos
        ├── NCBI — genetics sequences (EFetch)
        ├── PubChem — compound details, SMILES
        ├── CrossRef / OpenAlex — research papers
        └── Background ingest → MINDEX (fire-and-forget)
    → UnifiedSearchResponse → SearchContext.setResults
    → Widgets render (Species, Chemistry, Genetics, Location, Research, AI, etc.)
```

---

## 3. VM Layout & Services

| VM | IP | Role | Port | Used by Search |
|----|-----|------|------|----------------|
| Sandbox | 192.168.0.187 | Website Docker | 3000 | Search page, API routes |
| MAS | 192.168.0.188 | Orchestrator, MYCA | 8001 | AI chat, consciousness, intention |
| MINDEX | 192.168.0.189 | Postgres, Redis, Qdrant | 8000 | Primary data, unified-search, species/compounds/genetics |

---

## 4. Integration Matrix

### MINDEX (192.168.0.189:8000)

| Endpoint | Purpose | Called From |
|----------|---------|-------------|
| `/api/mindex/unified-search` | Primary multi-type search | unified route |
| `/api/mindex/species/detail?name=...` or `?id=inat-N` | Species taxonomy, photos | Species widget, compound detail |
| `/api/mindex/compounds/detail?name=...` | Compound properties | Chemistry widget, CompoundDetailModal |
| `/api/mindex/genetics?species=...` | Genetics (may 500 — schema) | unified route |
| `/api/mindex/research?search=...` | Research papers | unified route |
| `POST /api/mindex/species/ingest-background` | Background species ingest | unified route (fire-and-forget) |

### MYCA (MAS 192.168.0.188:8001)

| Endpoint | Purpose | Called From |
|----------|---------|-------------|
| `/api/myca/consciousness/chat` | AI chat | AIWidget, AIConversation |
| `/api/myca/nlq` | Natural language query | command-search, voice |
| `POST /api/myca/intention` | Intent events (search, click, focus) | lib/search/myca-intention.ts |
| `GET /agents/gap/scan` | Gap scan | gap-agent (not search UI) |

### NLM (Nature Learning Model)

- **Scope:** NLM is **not** used by main Fluid Search.
- **Usage:** Fungi Compute dashboard (`/api/fci/nlm/[deviceId]`) for FCI device/pattern analysis.
- **CREP marker:** "MINDEX · MYCA · NLM" is conceptual; NLM is FCI-specific.

### External APIs (from unified route)

| API | Purpose |
|-----|---------|
| iNaturalist | Observations, taxa, photos |
| NCBI EFetch | Genetics sequences |
| PubChem | Compound properties, SMILES, synonyms |
| CrossRef | Research papers |
| OpenAlex | Research papers |

---

## 5. File Inventory

### Website repo (primary)

| Purpose | Path |
|---------|------|
| Search page | `app/search/page.tsx` |
| Unified search API | `app/api/search/unified/route.ts` |
| Search API (legacy) | `app/api/search/route.ts` |
| Search suggestions | `app/api/search/suggestions/route.ts` |
| Search AI | `app/api/search/ai/route.ts`, `ai-v2/route.ts` |
| Search memory | `app/api/search/memory/route.ts` |
| Search location | `app/api/search/location/route.ts` |
| MINDEX proxy routes | `app/api/mindex/**` (species/detail, compounds/detail, genetics, etc.) |
| Search context | `components/search/SearchContextProvider.tsx` |
| Fluid canvas | `components/search/fluid/FluidSearchCanvas.tsx` |
| Unified search SDK | `lib/search/unified-search-sdk.ts` |
| useSearch hook | `components/search/use-search.ts` (legacy suggestions) |
| useUnifiedSearch hook | `hooks/use-unified-search.ts` |
| Session memory | `lib/search/session-memory.ts` |
| Live results engine | `lib/search/live-results-engine.ts` |
| Intent parser | `lib/search/intent-parser.ts` |
| MYCA intention | `lib/search/myca-intention.ts` |
| Widget physics | `lib/search/widget-physics.ts` |

### Widgets

| Widget | File |
|--------|------|
| Species | `components/search/fluid/widgets/SpeciesWidget.tsx` |
| Chemistry | `components/search/fluid/widgets/ChemistryWidget.tsx` |
| Genetics | `components/search/fluid/widgets/GeneticsWidget.tsx` |
| Location | `components/search/fluid/widgets/LocationWidget.tsx` |
| Research | `components/search/fluid/widgets/ResearchWidget.tsx` |
| AI | `components/search/fluid/widgets/AIWidget.tsx` |
| News | `components/search/fluid/widgets/NewsWidget.tsx` |
| Map | `components/search/fluid/widgets/MapWidget.tsx` |
| Media | `components/search/fluid/widgets/MediaWidget.tsx` |
| CREP | `components/search/fluid/widgets/CrepWidget.tsx` |
| Earth2 | `components/search/fluid/widgets/Earth2Widget.tsx` |
| MycaSuggestions | `components/search/fluid/widgets/MycaSuggestionsWidget.tsx` |
| ObservationEarthPortal | `components/search/fluid/widgets/ObservationEarthPortal.tsx` |

---

## 6. Interfaces & Types

### UnifiedSearchResponse (`lib/search/unified-search-sdk.ts`)

```ts
{
  query: string
  results: {
    species: SpeciesResult[]
    compounds: CompoundResult[]
    genetics: GeneticsResult[]
    research: ResearchResult[]
  }
  totalCount: number
  timing: { total, mindex, ai? }
  source: "live" | "cache" | "fallback"
  aiAnswer?: { text, confidence, sources }
  live_results?: LiveResult[]
}
```

### CompoundResult

```ts
{ id, name, formula, molecularWeight, chemicalClass, sourceSpecies: string[], biologicalActivity, structure }
```

### GeneticsResult

```ts
{ id, accession, speciesName, geneRegion, sequenceLength, gcContent?, source }
```

### SpeciesResult

```ts
{ id, scientificName, commonName, taxonomy, description, photos, observationCount, rank }
```

---

## 7. User Interactions

| Action | Flow |
|--------|------|
| Type query | Debounced → `/api/search/unified` → setResults |
| Click species "On Earth" | SpeciesEarthPortalLoader → useSpeciesObservations(speciesName) → iNaturalist → ObservationEarthPortal (Cesium) |
| Click compound "Found In" species | onFocusWidget({ type: "species", id }) → Species widget pinnedSpeciesName → fetch detail |
| Click genetics organism | setEarthSpecies → GeneticsEarthPortalLoader → ObservationEarthPortal |
| Click location observation | ObservationEarthPortal, flyToBoundingSphere, selectedEntity = clicked |
| Ask MYCA | AIWidget → `/api/search/ai` or `/api/myca/consciousness/chat` |
| Voice command | VoiceCommandPanel → MAS/MYCA |
| Save to notepad | addNotepadItem (localStorage) |
| MYCA chat | addChatMessage (sessionStorage) |

---

## 8. Mycosoft Apps Integration

| App | Integration with Search |
|-----|-------------------------|
| **NatureOS** | Uses MINDEX for species/genetics; `/app/natureos/` |
| **Fungi Compute** | FCI dashboard, NLM for device signals; not main search |
| **MINDEX search UI** | `/mindex` — separate MINDEX search interface |
| **Species page** | `/species` — species database |
| **Compounds** | `/compounds` — compound catalog |
| **CREP** | CREP widget in search; aviation/maritime |
| **Earth2** | Earth2 widget; weather simulation |

---

## 9. Work DONE (as of Feb 10, 2026)

### Location widget & ObservationEarthPortal

- **Centering:** `flyToBoundingSphere` so pin is centered (not offset north)
- **Auto-select:** After fly, first/clicked observation set as `viewer.selectedEntity`
- **Multiple observations:** Location passes `observations={[earthObs, ...others]}` with clicked one first

### Species widget

- **On Earth (compact):** Button on non-focused pill
- **On Earth (pinned):** Button on pinned species card when from Chemistry/Genetics
- **On Earth (focused):** Button in main dashboard
- **earthSpeciesName state:** Ensures pinned species name used when opening Earth from pinned card

### Search API (unified route)

- **Ganodermic acid:** `COMPOUND_TO_FUNGI` includes `ganodermic`, `"ganodermic acid"`
- **compoundFungi → sourceSpecies:** When compound query, attach `sourceSpecies` to compounds for "Found In"
- **SPECIES_NAMES:** Reishi, lingzhi → Ganoderma lucidum
- **Background ingest:** Fire-and-forget to MINDEX for species, compounds, genetics, research

### useSpeciesObservations

- Genus fallback: if species-level returns 0, retry with genus (e.g. "Ganoderma")
- `quality_grade` relaxed for genus fallback to include `casual`

---

## 10. Work NOT DONE / Remaining

### Compound detail API

- **Gap:** `/api/mindex/compounds/detail` does not return `sourceSpecies`
- **Fix:** Add COMPOUND_TO_FUNGI lookup in compound detail route when compound name matches; return `sourceSpecies: string[]`
- **File:** `app/api/mindex/compounds/detail/route.ts`

### Genetics

- **MINDEX genetics 500:** Schema mismatch; NCBI fallback works
- **Ganoderma/Reishi:** `resolveScientificName` maps to Ganoderma lucidum; `searchNCBIGenetics(query)` runs — verify genetics returned for common names
- **Empty state:** No "Fetch from source" button

### Empty-widget policy

- **Required:** When widget empty, show "Fetch from source" that triggers re-search or background ingest
- **Genetics/Chemistry empty:** Add button that calls `refresh()` from useUnifiedSearch (or equivalent)
- **SearchContext:** Add `refreshSearch` or expose `refresh` from useUnifiedSearch to widgets

### Cross-widget behavior

- When switching species from Chemistry "Found In" or Genetics organism link, Chemistry and Genetics widgets should update
- Verify `navigate-to-species`, `onFocusWidget`, `pinnedSpeciesName` trigger correct data refresh

### MINDEX TODOs

- **TODO:** Create `/api/mindex/research/search` — currently uses `/api/mindex/research?search=...`

---

## 11. Deployment: Dev → Sandbox → Production

### Local dev

- **Command:** `npm run dev:next-only` (port 3010) — no GPU
- **Env (`.env.local`):** `MAS_API_URL=http://192.168.0.188:8001`, `MINDEX_API_URL=http://192.168.0.189:8000`
- **VMs:** MAS (188) and MINDEX (189) must be reachable

### Sandbox (VM 187)

1. Commit and push to GitHub
2. `ssh mycosoft@192.168.0.187`
3. `cd /opt/mycosoft/website && git reset --hard origin/main`
4. `docker build -t mycosoft-always-on-mycosoft-website:latest --no-cache .`
5. Restart container **with NAS mount:**
   ```bash
   docker run -d --name mycosoft-website -p 3000:3000 \
     -v /opt/mycosoft/media/website/assets:/app/public/assets:ro \
     --restart unless-stopped mycosoft-always-on-mycosoft-website:latest
   ```
6. **Purge Cloudflare cache** (Purge Everything)
7. Verify: sandbox.mycosoft.com

### Production

- Same flow; ensure `MINDEX_API_URL` and `MAS_API_URL` point to production VMs if different

---

## 12. Skills to Use

| Skill | When |
|-------|------|
| `create-api-route` | New search proxy or webhook |
| `create-nextjs-page` | New search-related page |
| `create-react-component` | New widget or search UI |
| `deploy-website-sandbox` | Deploy to VM 187 |
| `setup-env-vars` | MINDEX/MAS URLs |
| `start-dev-website` | `npm run dev:next-only` |

---

## 13. Rules to Follow

- **No mock data** — All data from real APIs; empty states when none
- **Dated docs** — Any new search doc: `docs/SEARCH_*_FEB10_2026.md` (or current date)
- **Registries** — Update API_CATALOG, SYSTEM_REGISTRY if adding endpoints
- **NAS mount** — Always include `/opt/mycosoft/media/website/assets` when restarting website container

---

## 14. Related Agents

| Agent | Use For |
|-------|---------|
| `website-dev` | Next.js, React, Tailwind for search UI |
| `gap-agent` | Missing work, connection gaps |
| `deploy-pipeline` | Sandbox/production deployment |
| `backend-dev` | MINDEX/MAS API changes |

---

## 15. When to Invoke search-engineer

- Building or fixing Fluid Search, widgets, Earth portals
- Debugging empty results, compound→species, genetics
- Adding search API routes or MINDEX proxies
- Deploying search changes to sandbox/production
- Connecting search to new data sources (MINDEX, MYCA, NLM, apps)
- Implementing empty-widget "Fetch from source" or ingest triggers
