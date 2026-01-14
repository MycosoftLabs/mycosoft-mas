import { NextRequest, NextResponse } from "next/server";

export const dynamic = "force-dynamic";

// MINDEX API URL
const MINDEX_API_URL = process.env.MINDEX_API_URL || "http://localhost:8000";

interface GraphNode {
  id: string;
  label: string;
  type: "taxon" | "specimen" | "sequencing_run" | "assembly" | "variant_set";
  rank?: string;
  data?: Record<string, unknown>;
}

interface GraphEdge {
  source: string;
  target: string;
  relationship: "parent_of" | "assigned_to" | "sequenced_by" | "assembled_into" | "has_variants";
}

interface MINDEXTaxon {
  id: string;
  scientific_name: string;
  common_name?: string;
  rank?: string;
  parent_id?: string;
  gbif_id?: string;
  children_count?: number;
  observations_count?: number;
}

/**
 * GET /api/ancestry/graph
 * Fetches taxonomy graph data from MINDEX and formats for Cytoscape.js
 * 
 * Query params:
 * - root: Root taxon ID (default: "fungi")
 * - depth: How many levels to fetch (default: 3)
 */
export async function GET(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams;
  const rootId = searchParams.get("root") || "fungi";
  const depth = parseInt(searchParams.get("depth") || "3", 10);

  try {
    // Try to fetch from MINDEX API
    const response = await fetch(
      `${MINDEX_API_URL}/api/mindex/taxa?parent=${rootId}&limit=100`,
      {
        signal: AbortSignal.timeout(5000),
        headers: {
          Accept: "application/json",
        },
      }
    );

    if (response.ok) {
      const data = await response.json();
      const taxa: MINDEXTaxon[] = data.taxa || data.results || data || [];

      // Build graph from MINDEX data
      const { nodes, edges } = buildGraphFromTaxa(taxa, rootId, depth);

      return NextResponse.json({
        nodes,
        edges,
        source: "mindex",
        rootId,
        depth,
      });
    }
  } catch (error) {
    console.log("MINDEX not available, using mock data:", error);
  }

  // Fallback to mock data
  const { nodes, edges } = getMockGraph(rootId, depth);

  return NextResponse.json({
    nodes,
    edges,
    source: "mock",
    rootId,
    depth,
  });
}

/**
 * Build graph structure from MINDEX taxa data
 */
function buildGraphFromTaxa(
  taxa: MINDEXTaxon[],
  rootId: string,
  maxDepth: number
): { nodes: GraphNode[]; edges: GraphEdge[] } {
  const nodes: GraphNode[] = [];
  const edges: GraphEdge[] = [];
  const visited = new Set<string>();

  // Add root node
  const rootTaxon = taxa.find((t) => t.id === rootId);
  if (rootTaxon) {
    nodes.push({
      id: rootTaxon.id,
      label: rootTaxon.scientific_name,
      type: "taxon",
      rank: rootTaxon.rank,
      data: {
        common_name: rootTaxon.common_name,
        gbif_id: rootTaxon.gbif_id,
        children_count: rootTaxon.children_count,
        observations_count: rootTaxon.observations_count,
      },
    });
    visited.add(rootTaxon.id);
  }

  // Build tree from taxa
  function addChildren(parentId: string, currentDepth: number) {
    if (currentDepth >= maxDepth) return;

    const children = taxa.filter((t) => t.parent_id === parentId);
    for (const child of children) {
      if (visited.has(child.id)) continue;
      visited.add(child.id);

      nodes.push({
        id: child.id,
        label: child.scientific_name,
        type: "taxon",
        rank: child.rank,
        data: {
          common_name: child.common_name,
          gbif_id: child.gbif_id,
          children_count: child.children_count,
          observations_count: child.observations_count,
        },
      });

      edges.push({
        source: parentId,
        target: child.id,
        relationship: "parent_of",
      });

      addChildren(child.id, currentDepth + 1);
    }
  }

  addChildren(rootId, 0);

  return { nodes, edges };
}

/**
 * Mock taxonomy graph data for when MINDEX is unavailable
 */
function getMockGraph(
  rootId: string,
  depth: number
): { nodes: GraphNode[]; edges: GraphEdge[] } {
  const nodes: GraphNode[] = [
    {
      id: "fungi",
      label: "Fungi",
      type: "taxon",
      rank: "Kingdom",
      data: { common_name: "Fungi", children_count: 144000 },
    },
    {
      id: "ascomycota",
      label: "Ascomycota",
      type: "taxon",
      rank: "Phylum",
      data: { common_name: "Sac Fungi", children_count: 64000 },
    },
    {
      id: "basidiomycota",
      label: "Basidiomycota",
      type: "taxon",
      rank: "Phylum",
      data: { common_name: "Club Fungi", children_count: 31500 },
    },
    {
      id: "agaricales",
      label: "Agaricales",
      type: "taxon",
      rank: "Order",
      data: { common_name: "Gilled Mushrooms", children_count: 13000 },
    },
    {
      id: "boletales",
      label: "Boletales",
      type: "taxon",
      rank: "Order",
      data: { common_name: "Boletes", children_count: 1300 },
    },
    {
      id: "amanitaceae",
      label: "Amanitaceae",
      type: "taxon",
      rank: "Family",
      data: { common_name: "Amanita Family", children_count: 600 },
    },
    {
      id: "agaricaceae",
      label: "Agaricaceae",
      type: "taxon",
      rank: "Family",
      data: { common_name: "Agaric Family", children_count: 1400 },
    },
    {
      id: "boletaceae",
      label: "Boletaceae",
      type: "taxon",
      rank: "Family",
      data: { common_name: "Bolete Family", children_count: 500 },
    },
    {
      id: "pezizomycotina",
      label: "Pezizomycotina",
      type: "taxon",
      rank: "Subphylum",
      data: { common_name: "Filamentous Ascomycetes", children_count: 35000 },
    },
    {
      id: "pezizales",
      label: "Pezizales",
      type: "taxon",
      rank: "Order",
      data: { common_name: "Cup Fungi", children_count: 1600 },
    },
    // Add some specimens for variety
    {
      id: "specimen-001",
      label: "MYCO-001",
      type: "specimen",
      data: { collection_date: "2026-01-05", location: "San Diego, CA" },
    },
    {
      id: "specimen-002",
      label: "MYCO-002",
      type: "specimen",
      data: { collection_date: "2026-01-08", location: "Los Angeles, CA" },
    },
  ];

  const edges: GraphEdge[] = [
    { source: "fungi", target: "ascomycota", relationship: "parent_of" },
    { source: "fungi", target: "basidiomycota", relationship: "parent_of" },
    { source: "basidiomycota", target: "agaricales", relationship: "parent_of" },
    { source: "basidiomycota", target: "boletales", relationship: "parent_of" },
    { source: "agaricales", target: "amanitaceae", relationship: "parent_of" },
    { source: "agaricales", target: "agaricaceae", relationship: "parent_of" },
    { source: "boletales", target: "boletaceae", relationship: "parent_of" },
    { source: "ascomycota", target: "pezizomycotina", relationship: "parent_of" },
    { source: "pezizomycotina", target: "pezizales", relationship: "parent_of" },
    { source: "amanitaceae", target: "specimen-001", relationship: "assigned_to" },
    { source: "boletaceae", target: "specimen-002", relationship: "assigned_to" },
  ];

  // Filter by depth if needed
  if (depth < 5) {
    const filteredNodes = nodes.filter((n) => {
      const ranks = ["Kingdom", "Phylum", "Subphylum", "Order", "Family"];
      const rankIndex = ranks.indexOf(n.rank || "");
      return rankIndex < depth || n.type !== "taxon";
    });
    const nodeIds = new Set(filteredNodes.map((n) => n.id));
    const filteredEdges = edges.filter(
      (e) => nodeIds.has(e.source) && nodeIds.has(e.target)
    );
    return { nodes: filteredNodes, edges: filteredEdges };
  }

  return { nodes, edges };
}
