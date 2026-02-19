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

## Protocol

- Follow `.cursor/rules/neuromorphic-ui-standards.mdc`
- Use the `neuromorphic-integration` skill when converting pages
- Test in both light and dark mode
- Verify mobile responsiveness
