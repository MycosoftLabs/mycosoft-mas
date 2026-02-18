# Mobile Engineer Agent & Mobile-First Standards — Feb 17, 2026

## Summary

Created the `mobile-engineer` sub-agent, `mobile-first-standards` rule, and `mobile-audit` skill to enforce complete mobile responsiveness across all Mycosoft website pages, apps, tools, and dashboards for iOS and Android.

---

## Files Created

| File | Location | Purpose |
|------|----------|---------|
| `mobile-engineer.md` | `.cursor/agents/` (MAS, WEBSITE, global) | Sub-agent for mobile work |
| `mobile-first-standards.mdc` | `.cursor/rules/` (MAS, WEBSITE, global) | Always-applied mobile standards rule |
| `mobile-audit/SKILL.md` | `.cursor/skills/` (MAS, global) | Skill for systematic mobile audits |

All synced to `C:\Users\admin2\.cursor\` (global Cursor user directory).

---

## Agent: mobile-engineer

**Trigger:** Use proactively whenever creating pages, components, dashboards, tools, or apps.

### Scope
All pages in `app/` (50+ routes including dashboard, search, devices, natureos, myca, scientific, defense, etc.) and all components in `components/`.

### Key Responsibilities
- Mobile navigation (hamburger menus, bottom nav, collapsible sidebars)
- Touch target enforcement (≥ 44px per Apple HIG / 48dp per Android Material)
- Typography scaling (mobile-first responsive text)
- Layout responsiveness (flex-col mobile → flex-row desktop)
- Form field mobile optimization (height, font-size, stacking)
- Table and data grid mobile handling (overflow-x-auto or card layout)
- Dashboard and complex UI mobile adaptation (sidebars, charts, maps)
- iOS-specific fixes (safe area insets, 300ms tap delay, input zoom, fixed+scroll bug)
- Android-specific fixes (dvh height, theme color, Material touch)
- Chart responsiveness (ResponsiveContainer)
- Image optimization (next/image with sizes)

---

## Rule: mobile-first-standards.mdc

**Always applied** — enforced on every website file created or modified.

### Core Standards
- Tailwind mobile-first breakpoints: default (0px), sm (640px), md (768px), lg (1024px), xl (1280px)
- Minimum touch targets: 44×44px
- Minimum input font: 16px (prevents iOS zoom)
- All layouts: flex-col mobile → flex-row desktop
- Tables: always wrapped in overflow-x-auto
- Forms: stack vertically on mobile
- Modals: full-width on mobile (max-w-full sm:max-w-md)
- Images: next/image with sizes prop
- Safe areas: env(safe-area-inset-*) for iOS notch/Dynamic Island

### Required viewport meta
```tsx
export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  viewportFit: 'cover',
  themeColor: '#0a0a0a',
}
```

---

## Skill: mobile-audit

Step-by-step audit workflow:
1. Check layout.tsx for required viewport meta
2. Run 17-point checklist on each file
3. Apply fixes using standard patterns (hamburger nav, responsive containers, table wrappers, etc.)
4. Verify desktop layout unchanged at 1280px+
5. Test at 375px, 390px, 360px, 768px viewports
6. Report results

---

## Integration

- `mobile-engineer` agent added to the Development Agents table in `mycosoft-full-context-and-registries.mdc`
- `mobile-first-standards.mdc` set as always-apply rule (appears in every Cursor session)
- `mobile-audit` skill available globally via `C:\Users\admin2\.cursor\skills\mobile-audit\`

---

## Usage

```
# In any Cursor chat:
@mobile-engineer audit the /dashboard page for mobile issues
@mobile-engineer fix mobile navigation on the natureos app
@mobile-engineer make the /scientific/lab page work on iPhone

# The rule fires automatically when creating any page/component
# The skill can be invoked: "use the mobile-audit skill on components/crep/"
```

---

## Tested Viewport Sizes (always verify after changes)

| Device | Width | Notes |
|--------|-------|-------|
| iPhone SE (3rd gen) | 375px | Smallest modern iPhone |
| iPhone 14 Pro | 390px | Standard iPhone reference |
| Android generic | 360px | Most common Android width |
| iPad | 768px | Tablet breakpoint |
| Desktop | 1280px | Desktop reference (must not break) |

---

## DO NOT Rules

- NEVER break desktop layouts when fixing mobile
- NEVER remove desktop-specific Tailwind classes
- NEVER use font-size < 16px on form inputs
- NEVER leave tables without horizontal scroll wrappers
- NEVER use hover-only interactions for primary actions
- NEVER use `min-h-screen` for full-height layouts (use `min-h-dvh`)
