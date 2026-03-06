# GitHub Issue #10 Fix: NatureOS Chat/Voice Bubble Layering - Mar 2, 2026

**Status:** Complete  
**Issue:** [MycosoftLabs/website#10](https://github.com/MycosoftLabs/website/issues/10) — NatureOS Chat/Voice bubble button layering conflict (CSS)

## Summary

Fixed the CSS layering conflict for the Chat and Voice floating buttons in the bottom-right corner across the site. Implemented a unified FAB container that stacks both buttons vertically with consistent z-index.

## Changes

### 1. `UnifiedMYCAFAB` component (new)

- **Path:** `WEBSITE/website/components/myca/UnifiedMYCAFAB.tsx`
- Single fixed container at `bottom-4 right-4 z-[9998]`
- Stacks Chat and Voice buttons vertically (`flex-col-reverse gap-2`)
- Voice button hidden on `/search` and `/test-voice` (pages with own mic UI)

### 2. `MYCAFloatingButton` updates

- Added `embedded?: boolean` — when true, omits fixed positioning for use inside the unified container
- Fixed modal overlay z-index: `z-[80]` → `z-[9999]` so overlay appears above the button when open
- Standalone mode: `fixed bottom-4 right-4 z-[9998]`

### 3. `PersonaPlexWidget` updates

- Added `embedded?: boolean` — when true, renders inline (no fixed) for use in `UnifiedMYCAFAB`
- Collapsed embedded: `relative z-0`
- Expanded embedded: `fixed bottom-24 right-4 z-[9999]` so panel appears above the FAB stack
- Button size aligned: `h-12 w-12` (matches Chat button)

### 4. `PersonaPlexProvider` updates

- Added `renderFloatingWidget?: boolean` (default `true`)
- When `false`, does not render its own `PersonaPlexWidget` (UnifiedMYCAFAB renders it instead)

### 5. `AppShellProviders` updates

- When `showFloating && enableVoice`: renders `UnifiedMYCAFAB` (Chat + Voice stacked)
- When `showFloating && !enableVoice`: renders `MYCAFloatingButton` only
- Passes `renderFloatingWidget={!showFloating}` to `PersonaPlexProvider` when FAB is shown

### 6. NatureOS layout

- **Removed** duplicate `MYCAFloatingButton` — was causing two overlapping buttons on NatureOS pages
- Chat/Voice FAB is now provided only by `AppShellProviders`

## Z-Index Hierarchy

| Element                | Z-Index |
|------------------------|---------|
| FAB container          | 9998    |
| Chat button            | 9998 (or relative when embedded) |
| Voice button           | 9998 (or relative when embedded) |
| Chat modal overlay     | 9999    |
| Voice expanded panel   | 9999    |

## Verification

- Build: `npm run build` completes successfully
- No linter errors
- Chat and Voice buttons stack vertically in bottom-right
- No overlapping or layering conflicts
