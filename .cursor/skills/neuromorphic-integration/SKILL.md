---
name: neuromorphic-integration
description: Integrate neuromorphic UI into a page. Use when converting Shadcn pages to neuromorphic design or adding neuromorphic styling.
---

# Neuromorphic Integration

## Steps

1. **Import NeuromorphicProvider and components**
   ```tsx
   import { NeuromorphicProvider, NeuButton, NeuCard, NeuBadge, NeuTabs } from "@/components/ui/neuromorphic"
   ```

2. **Wrap page content in NeuromorphicProvider**
   ```tsx
   <NeuromorphicProvider>
     <div className="min-h-screen">
       {/* page content */}
     </div>
   </NeuromorphicProvider>
   ```

3. **Replace Shadcn components**
   - `Button` → `NeuButton` (use `variant="primary"` for primary actions)
   - `Card`, `CardContent`, `CardHeader` → `NeuCard`, `NeuCardContent`, `NeuCardHeader`
   - `Badge` → `NeuBadge` (use `variant` for semantic colors)
   - `Tabs` → `NeuTabs` with `tabs`, `activeIndex`, `onTabChange`

4. **Import neuromorphic styles** (or rely on NeuromorphicProvider which imports them)

5. **Test light and dark mode** – use theme toggle; text and icons must be readable in both

6. **Verify mobile responsiveness** – use breakpoints `md:`, `lg:` as needed

## Component Mapping

| Shadcn | Neuromorphic | Notes |
|--------|--------------|-------|
| Button | NeuButton | variant: default, primary, success, etc. |
| Card | NeuCard | Use NeuCardHeader, NeuCardContent |
| Badge | NeuBadge | variant: default, primary, success, etc. |
| Tabs | NeuTabs | Use tabs array + activeIndex state |
| Input | NeuInput | Includes label, error support |
| Select | NeuSelect | Searchable dropdown |

## Tabs Conversion

Shadcn:
```tsx
<Tabs defaultValue="tab1">
  <TabsList><TabsTrigger value="tab1">Tab 1</TabsTrigger></TabsList>
  <TabsContent value="tab1">...</TabsContent>
</Tabs>
```

Neuromorphic:
```tsx
const [activeTab, setActiveTab] = useState(0)
const TABS = [{ id: "tab1", label: "Tab 1" }, ...]
<NeuTabs tabs={TABS} activeIndex={activeTab} onTabChange={setActiveTab}>
  <NeuTabsContent id="panel-tab1" tabId="tab1" isActive={activeTab===0}>...</NeuTabsContent>
</NeuTabs>
```
