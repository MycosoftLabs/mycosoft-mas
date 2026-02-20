# Neuromorphic UI Sub-Agent

**Role:** Neuromorphic UI specialist for the Mycosoft website

**When to Invoke:**
- Creating UI with neuromorphic styling
- Converting pages to neuromorphic design
- Debugging neuromorphic theming or dark/light mode
- Adding new neuromorphic components or patterns

---

## Architecture

- **Component library:** `WEBSITE/website/components/ui/neuromorphic/`
- **CSS variables:** `neuromorphic-styles.css` (`--neu-bg-primary`, `--neu-shadow-dark`, etc.)
- **Dark/light mode:** `next-themes` + `.neuromorphic-dark` class

---

## Key Commands

1. **Wrap page in NeuromorphicProvider**
   ```tsx
   import { NeuromorphicProvider } from "@/components/ui/neuromorphic"
   <NeuromorphicProvider>
     {pageContent}
   </NeuromorphicProvider>
   ```

2. **Use neuromorphic components instead of Shadcn**
   - `Button` → `NeuButton`
   - `Card` → `NeuCard`
   - `Badge` → `NeuBadge`
   - `Tabs` → `NeuTabs`
   - `Input` → `NeuInput`

3. **Apply container class**
   - Use `.neuromorphic-page` on the root container
   - Use `.neuromorphic-dark` when dark mode is active (provider handles this)

4. **Import styles**
   - `import "./neuromorphic-styles.css"` or use `NeuromorphicProvider` (it imports CSS)

---

## Component Mapping

| Shadcn | Neuromorphic |
|--------|--------------|
| Button | NeuButton |
| Card, CardContent, CardHeader | NeuCard, NeuCardHeader, NeuCardContent |
| Badge | NeuBadge |
| Tabs, TabsContent, TabsList, TabsTrigger | NeuTabs, NeuTabsContent, etc. |
| Input | NeuInput |
| Select | NeuSelect |

---

## Over-Video / Dark-Background Logic

When building neuromorphic pages with video or dark hero backgrounds:

1. Add `data-over-video` to the section containing dark video/gradient.
2. Apply override classes so text stays white: `.portal-hero-badge`, `.portal-hero-title`, `.device-hero-title`, etc.
3. Green accents: always `text-green-400`.
4. CTA buttons: light mode = dark text on light button; dark mode = white text (use `device-cta-over-video` or `portal-cta-over-video` class).
5. Light mode widgets over video get sharp outline via CSS in `neuromorphic-styles.css`.

## Device Pages

- Mushroom1, SporeBase, Hyphae1, MycoNode, Alarm — all wrapped in `NeuromorphicProvider` with `data-over-video` on video/dark hero sections.
- Paths: `components/devices/mushroom1-details.tsx`, `sporebase-details.tsx`, `hyphae1-details.tsx`, `myconode-details.tsx`, `alarm-details.tsx`.

---

## Protocol

- Follow `.cursor/rules/neuromorphic-ui-standards.mdc`
- Use the `neuromorphic-integration` skill when converting pages
- Test in both light and dark mode
- Verify mobile responsiveness
