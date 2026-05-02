# NatureOS App — Tools Hub — May 1, 2026

## What it is

The **Tools** App is the `/natureos/tools` **hub index** cataloging seven categories (Lab Equipment, AI Analysis, Chemistry, Biology, Genetics & Genomics, Physics & Math, Sampling & Lab Ops). Existing simulators remain at **`/natureos/tools/<tool>`** and are linked from the hub—no duplicate implementations.

## Why it's in NatureOS

A cloud console needs a **discoverable service catalog**; flattening everything into the sidebar was unmaintainable. The hub centralizes discovery while keeping deep routes stable.

## Current capabilities (shipped)

- Hub page: `/natureos/tools` (`ToolsHubIndex`).
- Sidebar **Tools** section defers detail to hub + App-order link.

## Data sources

- **Routes only**—each card links to real pages. Pending items use `pending_data_source` status without fake metrics.
- **Lab tools:** NatureOS .NET flows via `/natureos/lab-tools/*` where applicable.

## Roadmap

1. **`NATUREOS_TOOLS_HUB_DEEP_INTEGRATION_PLAN_MAY01_2026.md`** — Tecan, AlphaFold/NIM, genome tooling health probes.
2. Optional JSON catalog generated from route manifest (no hand-maintained mock arrays).

## Related apps

- All other NatureOS Apps (deep links), **Devices**, **MINDEX**.

## File locations

- `WEBSITE/website/app/natureos/tools/page.tsx` (index; coexists with `app/natureos/tools/*/page.tsx`)
- `WEBSITE/website/components/natureos/apps/tools-hub/tools-hub-index.tsx`
- `WEBSITE/website/components/dashboard/nav.tsx`

## Replaces / supersedes

- Ad-hoc Tools sidebar-only discovery (hub is canonical).
