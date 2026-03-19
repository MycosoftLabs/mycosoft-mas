# MYCA Export — Skill: Mobile Audit & Fix

**Export Date:** MAR16_2026  
**Skill Name:** mobile-audit  
**Purpose:** Audits pages/components for mobile readiness, fixes mobile layout issues. Use when "make mobile-ready", "fix mobile", "audit for mobile", or "mobile overhaul".  
**External Systems:** Base44, Claude, Perplexity, OpenAI, Grok — load when user requests mobile responsiveness work.

---

## What This Skill Does

Audits one or more Mycosoft website pages/components for mobile responsiveness and fixes all issues found without breaking desktop layouts.

## Steps

### STEP 1: Identify Target
Determine what to audit:
- Single page: `app/[route]/page.tsx`
- Single component: `components/[name]/index.tsx`
- Full section: all pages in a directory
- Full site: all pages in `app/`

### STEP 2: Check layout.tsx for Required Mobile Meta
Read `app/layout.tsx` and verify:

```tsx
export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  viewportFit: 'cover',
  themeColor: '#0a0a0a',
}
```

If missing, add it. Import `Viewport` from `next/server` or `next`.

### STEP 3: Run Audit on Each File

**Navigation Check**
- [ ] Desktop nav has `hidden md:flex` (or similar)
- [ ] Mobile nav exists with `md:hidden` hamburger using Shadcn `Sheet`
- [ ] Sub-pages have mobile back button

**Touch Target Check**
- [ ] All `<button>`, `<a>`, `<Link>` elements have ≥ 44px clickable area
- [ ] Fix with `min-h-[44px] px-4` or `p-3`

**Typography Check**
- [ ] All `<input>`, `<textarea>`, `<select>` have `text-base` (16px+)
- [ ] Body text uses responsive sizing (`text-sm sm:text-base`)
- [ ] Headings scale: `text-xl sm:text-2xl md:text-3xl`

**Layout Check**
- [ ] No `flex-row` or `grid-cols-N` without mobile fallback
- [ ] No fixed pixel widths that could overflow (`w-[800px]` → `w-full max-w-[800px]`)
- [ ] Padding uses responsive classes: `p-4 md:p-6 lg:p-8`

**Table Check**
- [ ] All `<table>` wrapped in `<div className="overflow-x-auto">`
- [ ] OR has `hidden md:table` with mobile card alternative

**Form Check**
- [ ] Fields stack vertically on mobile
- [ ] Inputs height ≥ `h-12` or `py-3`
- [ ] Submit button `w-full md:w-auto`

**Image Check**
- [ ] Uses `next/image` with `sizes` prop

**Chart/Dashboard Check**
- [ ] Recharts/charts use `<ResponsiveContainer width="100%" height={...}>`
- [ ] Complex charts have mobile scroll wrapper or simplified view

**iOS Safe Area Check**
- [ ] Full-height layouts use `min-h-dvh`
- [ ] Bottom navigation/fixed bars use `pb-[env(safe-area-inset-bottom)]`

### STEP 4: Apply Fixes

Common fix patterns:

```tsx
// FIX: Add mobile navigation
import { Sheet, SheetContent, SheetTrigger } from "@/components/ui/sheet"
import { Menu } from "lucide-react"

<nav className="flex items-center justify-between p-4">
  <div className="hidden md:flex gap-6">...</div>
  <Sheet>
    <SheetTrigger asChild>
      <button className="md:hidden min-h-[44px] min-w-[44px] flex items-center justify-center">
        <Menu className="h-6 w-6" />
      </button>
    </SheetTrigger>
    <SheetContent side="left" className="w-72 pt-8">
      <nav className="flex flex-col gap-2">...</nav>
    </SheetContent>
  </Sheet>
</nav>

// FIX: Make layout responsive
<div className="flex flex-col md:flex-row gap-4 md:gap-8">...</div>

// FIX: Wrap table
<div className="overflow-x-auto rounded-lg border">
  <table className="w-full min-w-[640px]">...</table>
</div>

// FIX: Input height and font size
<input className="h-12 px-4 text-base rounded-md border w-full" />

// FIX: Responsive chart
<ResponsiveContainer width="100%" height={300}>
  <LineChart data={data}>...</LineChart>
</ResponsiveContainer>

// FIX: Full-height mobile safe
<div className="min-h-dvh flex flex-col">
```

### STEP 5: Verify Changes Don't Break Desktop

- Confirm desktop classes (`md:`, `lg:`, `xl:`) remain intact
- Verify fix is additive (mobile-first base + desktop override)

### STEP 6: Test Sizes

- 375px (iPhone SE)
- 390px (iPhone 14 Pro)
- 360px (Android)
- 768px (iPad)
- 1280px (desktop — must be unchanged)

### STEP 7: Report Results

- Pages/components audited: N
- Issues found: N
- Issues fixed: N
- Files modified: list them

## Notes

- NEVER use `@media` queries in inline styles or JS — use Tailwind classes only
- NEVER remove desktop styles when adding mobile styles
- ALWAYS test that desktop 1280px+ is visually unchanged after fixes
