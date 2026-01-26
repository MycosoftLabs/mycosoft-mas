# P2 Tools Testing Report

**Date**: January 26, 2026  
**Status**: Tested and Integration Locations Identified  
**Tester**: Claude AI Assistant

---

## Executive Summary

All 4 P2 tools have been tested and verified to be working. This report documents the test results and provides specific recommendations for where each tool should be integrated in the Mycosoft website.

---

## Test Results

| Tool | URL Tested | Status | Load Time | Notes |
|------|------------|--------|-----------|-------|
| BByCroft LLM Viz | https://bbycroft.net/llm | **WORKING** | ~2s | Beautiful 3D visualization, GPT-2/3 models available |
| IGV.js | https://igv.org/app/ | **WORKING** | ~1.5s | Full genome browser with tracks, Broad Institute tool |
| Cytoscape.js | https://js.cytoscape.org/ | **WORKING** | ~1s | Extensive docs, already in package.json |
| HiGlass | http://higlass.io/ | **WORKING** | ~2s | Note: HTTPS has cert issues, use HTTP |

---

## Detailed Integration Recommendations

### 1. BByCroft LLM Visualization

**Why**: Provides stunning 3D visualization of transformer architecture that helps users understand how MYCA AI works.

**Where to Integrate**:

| Location | Path | Integration Type | Priority |
|----------|------|-----------------|----------|
| **Primary** | `/natureos/ai-studio/explainer` | Full page embed | HIGH |
| **Secondary** | `/myca-ai` | Iframe widget | MEDIUM |
| **Marketing** | `/capabilities/ai` | Screenshot with link | LOW |

**How to Integrate**:
```tsx
// components/ai-studio/llm-visualizer.tsx
"use client"

import { LazyLoader } from "@/components/performance"

export function LLMVisualizer() {
  return (
    <LazyLoader skeleton={<LLMSkeleton />} minHeight={600}>
      <iframe
        src="https://bbycroft.net/llm"
        className="w-full h-[600px] rounded-lg border"
        title="LLM Architecture Visualization"
        allow="accelerometer; gyroscope"
      />
    </LazyLoader>
  )
}
```

**Benefits**:
- Zero backend required
- Highly educational for users
- Marketing value for AI capabilities
- Interactive exploration of GPT-2, GPT-3 architectures

---

### 2. IGV.js - Integrative Genomics Viewer

**Why**: Industry-standard genome browser from Broad Institute. Simpler alternative to JBrowse2 for certain use cases.

**Where to Integrate**:

| Location | Path | Integration Type | Priority |
|----------|------|-----------------|----------|
| **Primary** | `/ancestry/tools#igv` | Embedded viewer | MEDIUM |
| **Secondary** | `/natureos/mindex` | Tab option | MEDIUM |
| **Fallback** | JBrowse2 alternative | Config option | LOW |

**How to Integrate**:
```tsx
// components/mindex/igv-viewer.tsx
"use client"

import { useEffect, useRef } from "react"
import { LazyLoader } from "@/components/performance"

export function IGVViewer({ genome, tracks }: IGVViewerProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  
  useEffect(() => {
    if (!containerRef.current) return
    
    // Dynamic import to avoid SSR issues
    import("igv").then(igv => {
      igv.createBrowser(containerRef.current, {
        genome: genome || "hg38",
        tracks: tracks || []
      })
    })
  }, [genome, tracks])
  
  return <div ref={containerRef} className="w-full h-[400px]" />
}
```

**Benefits**:
- Lighter weight than JBrowse2
- Better for simple genome browsing
- Well-documented API
- Supports standard genomics formats (BAM, VCF, BED, GFF3)

---

### 3. Cytoscape.js - Network Visualization

**Why**: Perfect for visualizing biological networks, symbiosis relationships, and agent topologies.

**Current Status**: Already installed in package.json:
```json
"cytoscape": "^3.33.1",
"cytoscape-cola": "^2.5.1"
```

**Where to Integrate**:

| Location | Path | Integration Type | Priority |
|----------|------|-----------------|----------|
| **Primary** | `/apps/symbiosis` | Main visualization | HIGH |
| **Secondary** | `/ancestry/phylogeny` | Relationship graphs | MEDIUM |
| **MINDEX** | `/natureos/mindex#networks` | Network tab | MEDIUM |
| **MAS Admin** | `/admin/agents` | Agent topology | LOW |

**How to Integrate**:
```tsx
// components/mindex/cytoscape-network.tsx
"use client"

import { useEffect, useRef } from "react"
import cytoscape from "cytoscape"
import cola from "cytoscape-cola"
import { LazyLoader } from "@/components/performance"

cytoscape.use(cola)

interface NetworkNode {
  id: string
  label: string
  type: "species" | "compound" | "gene"
}

interface NetworkEdge {
  source: string
  target: string
  type: "symbiosis" | "produces" | "inhibits"
}

export function CytoscapeNetwork({ nodes, edges }: { nodes: NetworkNode[], edges: NetworkEdge[] }) {
  const containerRef = useRef<HTMLDivElement>(null)
  const cyRef = useRef<cytoscape.Core | null>(null)
  
  useEffect(() => {
    if (!containerRef.current) return
    
    cyRef.current = cytoscape({
      container: containerRef.current,
      elements: [
        ...nodes.map(n => ({ data: { id: n.id, label: n.label }, classes: n.type })),
        ...edges.map(e => ({ data: { source: e.source, target: e.target }, classes: e.type }))
      ],
      layout: { name: "cola", animate: true },
      style: [
        { selector: "node", style: { "label": "data(label)", "background-color": "#10b981" }},
        { selector: "node.compound", style: { "background-color": "#8b5cf6" }},
        { selector: "node.gene", style: { "background-color": "#f59e0b" }},
        { selector: "edge", style: { "line-color": "#6b7280", "width": 2 }},
        { selector: "edge.symbiosis", style: { "line-color": "#10b981" }},
        { selector: "edge.inhibits", style: { "line-color": "#ef4444" }}
      ]
    })
    
    return () => { cyRef.current?.destroy() }
  }, [nodes, edges])
  
  return <div ref={containerRef} className="w-full h-[500px]" />
}
```

**Benefits**:
- Already installed, ready to use
- Perfect for Symbiosis Mapper
- Excellent for gene regulatory networks
- Can visualize MAS agent topology

---

### 4. HiGlass - Hi-C Data Visualization

**Why**: Advanced 3D genome organization visualization for research-grade analysis.

**Note**: HTTPS certificate expired, use HTTP: http://higlass.io/

**Where to Integrate**:

| Location | Path | Integration Type | Priority |
|----------|------|-----------------|----------|
| **Primary** | `/natureos/mindex#3d-genome` | Tab in MINDEX | LOW |
| **Secondary** | `/ancestry/tools#higlass` | Research section | LOW |

**Why Lower Priority**:
- Requires Docker server for custom data
- Complex setup
- Best suited for advanced research users
- Hi-C data not currently available in MINDEX

**How to Integrate (Future)**:
```tsx
// components/mindex/higlass-viewer.tsx
"use client"

import { useEffect, useRef } from "react"
import { LazyLoader } from "@/components/performance"

export function HiGlassViewer({ config }: { config: object }) {
  const containerRef = useRef<HTMLDivElement>(null)
  
  useEffect(() => {
    if (!containerRef.current) return
    
    // HiGlass requires special initialization
    import("higlass").then(hg => {
      hg.viewer(containerRef.current, config)
    })
  }, [config])
  
  return <div ref={containerRef} className="w-full h-[600px]" />
}
```

**Benefits**:
- Research-grade Hi-C visualization
- Multi-view synchronized browsing
- Harvard/MIT developed tool
- Published in Genome Biology

---

## Recommended Implementation Order

### Phase 1: Quick Wins (This Week)

1. **BByCroft LLM Viz** → `/natureos/ai-studio/explainer`
   - Effort: 2 hours
   - Impact: High (marketing + education value)
   - Method: Simple iframe embed with lazy loading

2. **Cytoscape.js** → `/apps/symbiosis`
   - Effort: 4-6 hours
   - Impact: High (enhances existing app)
   - Method: Replace current visualization with Cytoscape graph

### Phase 2: Genomics Enhancement (Next Sprint)

3. **IGV.js** → `/ancestry/tools#igv`
   - Effort: 1-2 days
   - Impact: Medium (alternative to JBrowse2)
   - Method: Add as optional genome browser

### Phase 3: Advanced Research (Q3 2026)

4. **HiGlass** → `/natureos/mindex#3d-genome`
   - Effort: 3-5 days
   - Impact: Medium (research users only)
   - Method: Docker server + React wrapper

---

## Files to Create

| File | Tool | Purpose |
|------|------|---------|
| `components/ai-studio/llm-visualizer.tsx` | BByCroft | LLM architecture embed |
| `components/mindex/cytoscape-network.tsx` | Cytoscape.js | Network visualization |
| `components/mindex/igv-viewer.tsx` | IGV.js | Alternative genome browser |
| `components/mindex/higlass-viewer.tsx` | HiGlass | 3D genome visualization |
| `app/natureos/ai-studio/llm-viz/page.tsx` | BByCroft | Dedicated LLM viz page |
| `app/apps/symbiosis/page.tsx` | Cytoscape.js | Enhanced Symbiosis Mapper |

---

## API Routes Required

| Tool | Route | Purpose |
|------|-------|---------|
| Cytoscape.js | `/api/natureos/mindex/networks` | Fetch network graph data |
| Cytoscape.js | `/api/apps/symbiosis/relationships` | Symbiosis relationship data |
| IGV.js | `/api/natureos/mindex/igv-config` | IGV track configurations |
| HiGlass | `/api/natureos/mindex/higlass-tileset` | Tileset server proxy |

---

## Dependencies to Install

```bash
# For IGV.js (when implementing)
npm install igv

# For HiGlass (when implementing)
npm install higlass

# Cytoscape.js already installed
```

---

## Conclusion

All P2 tools are functional and ready for integration. The recommended approach is:

1. Start with **BByCroft LLM Viz** (easiest, highest marketing value)
2. Enhance **Symbiosis Mapper** with Cytoscape.js (already installed)
3. Add **IGV.js** as JBrowse2 alternative later
4. Defer **HiGlass** until Hi-C data is available

The existing performance infrastructure (LazyLoader, visibility-based loading) is perfect for these integrations to ensure no background processing when tools are not in use.

---

*Report generated by MAS Infrastructure Agent - January 26, 2026*
