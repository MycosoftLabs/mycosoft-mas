# NatureOS App — Ancestry Database — May 1, 2026

## What it is

The **Ancestry Database** hosts taxonomy exploration, species detail, database views, and genomics tool links—scoped today primarily around fungal datasets with an explicit roadmap to all kingdoms.

## Why it's in NatureOS

Taxonomic navigation is a **platform primitive**; nesting under `/natureos/ancestry` keeps NatureOS coherent while redirects preserve `/ancestry` bookmarks.

## Current capabilities (shipped)

- Base route: `/natureos/ancestry` with explorer, database, species pages, etc.
- Redirects: `/ancestry` → `/natureos/ancestry` (and nested paths).

## Data sources

- **MINDEX:** taxon, genetics, observations as used by ancestry pages.
- **Website BFF:** `/api/ancestry/*` routes remain API paths (unchanged).

## Roadmap

1. **`ANCESTRY_ALL_SPECIES_EXPANSION_PLAN_MAY01_2026.md`** — kingdom-wide ETL + UX.
2. Cross-links from **Nature Statistics** KPIs.

## Related apps

- **Nature Statistics**, **Genetics tools**, **Growth Analytics**.

## File locations

- `WEBSITE/website/app/natureos/ancestry/**`
- Internal links updated to `/natureos/ancestry/*`

## Replaces / supersedes

- Top-level **`/ancestry/*`** public navigation (301 to `/natureos/ancestry/*`).
