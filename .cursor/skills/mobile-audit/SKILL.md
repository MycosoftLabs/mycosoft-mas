# Skill: Mobile Audit & Fix

**Trigger:** Use when auditing pages/components for mobile readiness, fixing mobile layout issues, or when the user says "make mobile-ready", "fix mobile", "audit for mobile", or "mobile overhaul".

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
// Must have viewport config:
export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  viewportFit: 'cover',
  themeColor: '#0a0a0a',
}
```

If missing, add it. Import `Viewport` from `next/server` or `next`.

### STEP 3: Run Audit on Each File

For each file, check:

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

For each issue found, apply the fix directly to the file. Common fix patterns:

```tsx
// FIX: Add mobile navigation
import { Sheet, SheetContent, SheetTrigger } from "@/components/ui/sheet"
import { Menu } from "lucide-react"

// In header/nav component:
<nav className="flex items-center justify-between p-4">
  {/* Desktop nav */}
  <div className="hidden md:flex gap-6">
    {navItems.map(item => <NavLink key={item.href} {...item} />)}
  </div>
  
  {/* Mobile nav */}
  <Sheet>
    <SheetTrigger asChild>
      <button className="md:hidden min-h-[44px] min-w-[44px] flex items-center justify-center">
        <Menu className="h-6 w-6" />
      </button>
    </SheetTrigger>
    <SheetContent side="left" className="w-72 pt-8">
      <nav className="flex flex-col gap-2">
        {navItems.map(item => <MobileNavLink key={item.href} {...item} />)}
      </nav>
    </SheetContent>
  </Sheet>
</nav>

// FIX: Make layout responsive
<div className="flex flex-col md:flex-row gap-4 md:gap-8">
  <aside className="w-full md:w-64 lg:w-72">...</aside>
  <main className="flex-1 min-w-0">...</main>
</div>

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

// FIX: Modal responsive
<DialogContent className="w-full max-w-full sm:max-w-md mx-4 sm:mx-auto rounded-t-xl sm:rounded-xl">
```

### STEP 5: Verify Changes Don't Break Desktop

After each fix:
1. Confirm desktop classes (`md:`, `lg:`, `xl:`) remain intact
2. Verify the fix is additive (mobile-first base + desktop override)
3. No desktop-specific styles removed

### STEP 6: Test Sizes to Verify

Using browser DevTools (or note for manual testing):
- 375px (iPhone SE)
- 390px (iPhone 14 Pro)
- 360px (Android)
- 768px (iPad)
- 1280px (desktop — must be unchanged)

### STEP 7: Report Results

After completing audit/fix, report:
- Pages/components audited: N
- Issues found: N
- Issues fixed: N
- Files modified: list them
- Remaining issues (if any requiring design decisions): list them

## Common Patterns Reference

### Mobile-First Responsive Container
```tsx
<div className="w-full max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
```

### Dashboard Sidebar (collapsible)
```tsx
<div className="flex flex-col lg:flex-row gap-0">
  {/* Mobile: Sheet drawer */}
  <MobileSidebar className="lg:hidden" />
  {/* Desktop: fixed sidebar */}
  <aside className="hidden lg:flex w-64 flex-shrink-0 flex-col border-r">
    ...
  </aside>
  <main className="flex-1 min-w-0 p-4 md:p-6">...</main>
</div>
```

### Bottom Navigation (mobile apps)
```tsx
<nav className="fixed bottom-0 left-0 right-0 z-50 bg-background border-t
                flex md:hidden items-center justify-around
                pb-[env(safe-area-inset-bottom)]">
  {tabs.map(tab => (
    <Link key={tab.href} href={tab.href}
      className="flex flex-col items-center gap-1 py-2 min-w-[44px] min-h-[44px]">
      <tab.icon className="h-5 w-5" />
      <span className="text-xs">{tab.label}</span>
    </Link>
  ))}
</nav>
```

### Card Layout for Mobile Tables
```tsx
// Mobile cards (< md)
<div className="space-y-3 md:hidden">
  {rows.map(row => (
    <div key={row.id} className="rounded-lg border p-4 space-y-2">
      <div className="flex justify-between">
        <span className="font-medium">{row.name}</span>
        <Badge>{row.status}</Badge>
      </div>
      <p className="text-sm text-muted-foreground">{row.description}</p>
    </div>
  ))}
</div>

// Desktop table (>= md)
<div className="hidden md:block overflow-x-auto">
  <table className="w-full">...</table>
</div>
```

## Notes

- NEVER use `@media` queries in inline styles or JS — use Tailwind classes only
- NEVER remove desktop styles when adding mobile styles
- ALWAYS test that desktop 1280px+ is visually unchanged after fixes
- The `mobile-engineer` agent handles complex decisions; this skill handles systematic fixes
