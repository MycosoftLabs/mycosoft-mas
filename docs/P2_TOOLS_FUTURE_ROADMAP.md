# P2 Tools - Future Integration Roadmap

**Date**: January 25, 2026  
**Status**: Planned  
**Priority**: Future sprints

---

## Overview

This document outlines P2 (future priority) tools identified for potential integration into the Mycosoft platform. These tools enhance visualization, ML/AI transparency, and biological data analysis capabilities but are not immediately critical for current operations.

---

## P2 Tools Summary

| Tool | Category | Use Case | Estimated Effort |
|------|----------|----------|------------------|
| BByCroft LLM Viz | ML/AI | LLM architecture education | 2-3 days |
| IGV.js | Genomics | Alternative genome browser | 3-4 days |
| Cytoscape.js | Network | Biological network visualization | 2-3 days |
| HiGlass | Genomics | 3D genome/Hi-C visualization | 4-5 days |

---

## Tool Details

### 1. BByCroft LLM Visualization

**Source**: [bbycroft.net/llm](https://bbycroft.net/llm)

**Description**: Beautiful 3D visualization of large language model architectures. Shows token flow through transformer layers with interactive exploration.

**Use Cases**:
- MYCA AI education page for users
- Marketing content showing AI capabilities
- Developer training on transformer architecture
- Public demonstrations

**Technical Notes**:
- Runs entirely in browser (WebGL)
- No backend required
- Can be embedded via iframe
- May have performance impact on lower-end devices

**Integration Path**:
```tsx
// Simple iframe embed
<iframe 
  src="https://bbycroft.net/llm" 
  className="w-full h-[600px]"
  title="LLM Visualization"
/>
```

**Considerations**:
- Check licensing for commercial use
- May want to self-host for reliability
- Consider creating MYCA-branded version

---

### 2. IGV.js - Integrative Genomics Viewer

**Source**: [github.com/igvteam/igv.js](https://github.com/igvteam/igv.js)  
**From**: [awesome-genome-visualization](https://cmdcolin.github.io/awesome-genome-visualization)

**Description**: JavaScript-based genome browser developed by the Broad Institute. Industry-standard tool used in research institutions worldwide.

**Use Cases**:
- Alternative to JBrowse2 if performance issues arise
- Viewing MINDEX genomic data
- Research-grade genome analysis
- Integration with external genomics databases

**Technical Notes**:
- Pure JavaScript, no backend required for basic usage
- Supports BAM, VCF, BED, GFF3, bigWig formats
- Well-documented API
- Active development and community

**Integration Path**:
```typescript
import igv from "igv"

// Initialize browser
const browser = await igv.createBrowser(container, {
  genome: "psilocybe_cubensis",
  tracks: [
    { type: "annotation", url: "genes.gff3" },
    { type: "variant", url: "variants.vcf" }
  ]
})
```

**Considerations**:
- Evaluate against JBrowse2 for performance
- May be better for simpler use cases
- Consider for backup/fallback option

---

### 3. Cytoscape.js - Network Visualization

**Source**: [js.cytoscape.org](https://js.cytoscape.org/)  
**From**: [awesome-biological-visualizations](https://github.com/keller-mark/awesome-biological-visualizations)

**Description**: Graph theory library for visualizing and analyzing biological networks, pathways, and relationships.

**Use Cases**:
- Symbiosis Mapper enhancement
- Metabolic pathway visualization
- Gene regulatory networks
- Mycorrhizal network visualization
- Species relationship graphs
- Agent topology visualization (MAS)

**Technical Notes**:
- Already partially installed (see package.json)
- Cytoscape-cola extension for force-directed layouts
- Supports large graphs (10,000+ nodes)
- Extensive styling options

**Current Status**:
```json
// Already in package.json
"cytoscape": "^3.33.1",
"cytoscape-cola": "^2.5.1",
```

**Integration Path**:
```typescript
import cytoscape from "cytoscape"
import cola from "cytoscape-cola"

cytoscape.use(cola)

const cy = cytoscape({
  container: document.getElementById("cy"),
  elements: [
    { data: { id: "psilocybe" } },
    { data: { id: "mycelium" } },
    { data: { source: "psilocybe", target: "mycelium" } }
  ],
  layout: { name: "cola" }
})
```

**Enhancement Ideas**:
- Replace current mycorrhizal-network-viz with Cytoscape version
- Add to Symbiosis Mapper page
- Create agent relationship graphs

---

### 4. HiGlass - Hi-C Data Visualization

**Source**: [higlass.io](https://higlass.io/)  
**From**: [awesome-biological-visualizations](https://github.com/keller-mark/awesome-biological-visualizations)

**Description**: Web-based viewer for 3D genome organization data (Hi-C, ChIP-seq, etc.). Shows chromosome conformation and 3D genome structure.

**Use Cases**:
- 3D genome structure visualization
- Chromatin interaction analysis
- Comparative genomics
- Advanced research applications

**Technical Notes**:
- Requires server component for large datasets
- Complex setup compared to other tools
- Best for advanced genomics research
- May be overkill for current needs

**Integration Path**:
1. Install HiGlass server (Docker)
2. Load fungal genome data
3. Create React wrapper component
4. Integrate with MINDEX data

**Considerations**:
- High complexity, high reward
- Defer until genomics data pipeline is mature
- Consider for Phase 2 of MINDEX development

---

## Integration Timeline

### Q2 2026 (Evaluate)
- [ ] BByCroft LLM Viz - Simple iframe integration
- [ ] Cytoscape.js - Enhance existing components

### Q3 2026 (Develop)
- [ ] IGV.js - Evaluate vs JBrowse2 performance
- [ ] Create Cytoscape-based network visualizations

### Q4 2026 (Advanced)
- [ ] HiGlass - Full 3D genome visualization
- [ ] Self-hosted LLM visualization

---

## UI Integration Strategy (Added Jan 2026)

Each P2 tool has a defined placement in the Mycosoft UI:

| Tool | Primary Location | Secondary Location | Navigation Link |
|------|-----------------|-------------------|-----------------|
| BByCroft LLM Viz | `/natureos/ai-studio/llm-viz` | AI Explainer page | NatureOS > AI Studio |
| IGV.js | `/ancestry/tools#igv` | MINDEX Genomics tab | Apps > Genomics Tools |
| Cytoscape.js | `/apps/symbiosis` | MINDEX Network tab | Apps > Symbiosis |
| HiGlass | `/natureos/mindex#3d-genome` | Ancestry 3D view | NatureOS > MINDEX |

### Component Structure

```
components/
├── mindex/
│   ├── igv-viewer.tsx          # P2 - IGV.js alternative browser
│   ├── higlass-viewer.tsx      # P2 - 3D genome visualization
│   └── cytoscape-network.tsx   # P2 - Biological network graphs
├── ai-studio/
│   └── llm-viz-embed.tsx       # P2 - BByCroft LLM viz embed
```

### API Routes Required

| Tool | API Route | Purpose |
|------|-----------|---------|
| IGV.js | `/api/natureos/mindex/igv-tracks` | Track configurations |
| Cytoscape.js | `/api/natureos/mindex/networks` | Graph data |
| HiGlass | `/api/natureos/mindex/hic-data` | Hi-C contact matrices |

### Agent Requirements

| Tool | Agent Name | Capabilities |
|------|------------|--------------|
| IGV.js | `IGVBrowserAgent` | Track management, zoom sync |
| Cytoscape.js | `NetworkGraphAgent` | Layout optimization, clustering |
| HiGlass | `HiCVisualizationAgent` | Resolution switching, 3D rendering |

---

## Resource Requirements

| Tool | Frontend | Backend | Storage | Expertise |
|------|----------|---------|---------|-----------|
| BByCroft | iframe/port | None | None | Low |
| IGV.js | React comp | Optional | Genome files | Medium |
| Cytoscape.js | React comp | None | Graph data | Medium |
| HiGlass | React comp | Docker server | Hi-C data | High |

---

## Dependencies to Add (When Implementing)

```json
// package.json additions
{
  "igv": "^2.15.0",
  "higlass": "^1.13.0"
}
```

```bash
# Backend additions
pip install cooler  # For HiGlass data processing
```

---

## Success Metrics

| Tool | Success Criteria |
|------|------------------|
| BByCroft | Embedded on education page, 1000+ views |
| IGV.js | Performance benchmark vs JBrowse2 |
| Cytoscape.js | Symbiosis Mapper uses Cytoscape graphs |
| HiGlass | 3D genome view for top 5 species |

---

## Related Documentation

- [Tool Integration Priority Plan](../../../.cursor/plans/tool_integration_priority_plan_*.plan.md)
- [MINDEX Architecture](./MINDEX_INTEGRATION_PLAN.md)
- [INNOVATION_APPS_USER_GUIDE.md](./INNOVATION_APPS_USER_GUIDE.md)

---

*Document created by MAS v2 Infrastructure Agent - January 25, 2026*
