# NatureOS App — Compound Analyser — May 1, 2026

## What it is

The **Compound Analyser** is the chemistry-forward NatureOS workspace for compound exploration, structures, and links into retrosynthesis/alchemy tools—positioned as the on-ramp to a future **chemputer** agent.

## Why it's in NatureOS

Chemistry sits beside biology and earth apps in the console mental model; separating it from generic “tools” clarifies product boundaries.

## Current capabilities (shipped)

- Route: `/natureos/compound-analyser` (from `/natureos/tools/compound-sim`).
- Existing embed/page behavior preserved.

## Data sources

- **MINDEX:** compounds router via website proxies.
- **External chemistry APIs** only when configured through env (never hardcoded keys).

## Roadmap

1. **`COMPOUND_ANALYSER_CHEMPUTER_AGENT_PLAN_MAY01_2026.md`** — agentic reaction workspace.
2. Reaction visualization with RDKit or equivalent when service exists.

## Related apps

- **Biology Simulator**, **Tools hub → Chemistry**, **Fungi Compute**.

## File locations

- `WEBSITE/website/app/natureos/compound-analyser/page.tsx`

## Replaces / supersedes

- **`/natureos/tools/compound-sim`** (301 redirect).
