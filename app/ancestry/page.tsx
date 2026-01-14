"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import dynamic from "next/dynamic";
import {
  Activity,
  ArrowLeft,
  Search,
  Dna,
  GitBranch,
  Book,
  Globe,
  Database,
  Microscope,
  ChevronRight,
  Network,
  RefreshCw,
  Loader2,
} from "lucide-react";
import type { GraphNode, GraphEdge } from "@/components/ancestry/GraphCanvas";

// Dynamically import GraphCanvas to avoid SSR issues with Cytoscape
const GraphCanvas = dynamic(
  () => import("@/components/ancestry/GraphCanvas"),
  { 
    ssr: false,
    loading: () => (
      <div className="flex items-center justify-center h-96 bg-gray-900 rounded-lg">
        <Loader2 className="w-8 h-8 animate-spin text-purple-400" />
      </div>
    ),
  }
);

interface TaxonInfo {
  id: string;
  scientific_name: string;
  common_name?: string;
  rank: string;
  parent?: string;
  children_count: number;
  observations_count: number;
  description?: string;
  gbif_id?: string;
}

interface Tool {
  id: string;
  name: string;
  description: string;
  icon: React.ComponentType<{ className?: string }>;
  status: "available" | "coming_soon";
}

const tools: Tool[] = [
  {
    id: "taxonomy-browser",
    name: "Taxonomy Browser",
    description: "Browse the complete fungal taxonomy tree",
    icon: GitBranch,
    status: "available",
  },
  {
    id: "graph-view",
    name: "Graph View",
    description: "Interactive network visualization",
    icon: Network,
    status: "available",
  },
  {
    id: "species-search",
    name: "Species Search",
    description: "Search and lookup any fungal species",
    icon: Search,
    status: "available",
  },
  {
    id: "dna-comparison",
    name: "DNA Comparison",
    description: "Compare genetic sequences between species",
    icon: Dna,
    status: "coming_soon",
  },
  {
    id: "distribution-map",
    name: "Distribution Map",
    description: "Global distribution of species",
    icon: Globe,
    status: "available",
  },
  {
    id: "literature-search",
    name: "Literature Search",
    description: "Search mycological publications",
    icon: Book,
    status: "coming_soon",
  },
];

export default function AncestryPage() {
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedTaxon, setSelectedTaxon] = useState<TaxonInfo | null>(null);
  const [activeTool, setActiveTool] = useState<string>("taxonomy-browser");
  const [taxa, setTaxa] = useState<Record<string, TaxonInfo>>({});
  const [graphData, setGraphData] = useState<{ nodes: GraphNode[]; edges: GraphEdge[] }>({ nodes: [], edges: [] });
  const [loading, setLoading] = useState(true);
  const [dataSource, setDataSource] = useState<"mindex" | "mock">("mock");

  // Fetch taxonomy data from MINDEX API
  const fetchTaxonomyData = useCallback(async () => {
    setLoading(true);
    try {
      // Try MINDEX API first
      const response = await fetch("/api/ancestry/graph?root=fungi&depth=4");
      if (response.ok) {
        const data = await response.json();
        setGraphData({ nodes: data.nodes, edges: data.edges });
        setDataSource(data.source);

        // Build taxa record from nodes
        const taxaRecord: Record<string, TaxonInfo> = {};
        for (const node of data.nodes) {
          if (node.type === "taxon") {
            taxaRecord[node.id] = {
              id: node.id,
              scientific_name: node.label,
              common_name: node.data?.common_name as string,
              rank: node.rank || "Unknown",
              children_count: (node.data?.children_count as number) || 0,
              observations_count: (node.data?.observations_count as number) || 0,
              gbif_id: node.data?.gbif_id as string,
            };
          }
        }
        
        // Add parent relationships
        for (const edge of data.edges) {
          if (edge.relationship === "parent_of" && taxaRecord[edge.target]) {
            taxaRecord[edge.target].parent = edge.source;
          }
        }

        setTaxa(taxaRecord);
        
        // Select root taxon
        if (taxaRecord.fungi) {
          setSelectedTaxon(taxaRecord.fungi);
        } else {
          const firstTaxon = Object.values(taxaRecord)[0];
          if (firstTaxon) setSelectedTaxon(firstTaxon);
        }
      }
    } catch (error) {
      console.error("Failed to fetch taxonomy data:", error);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchTaxonomyData();
  }, [fetchTaxonomyData]);

  const handleSearch = async () => {
    const query = searchQuery.toLowerCase();
    
    // Try MINDEX API search
    try {
      const response = await fetch(`/api/ancestry/graph?search=${encodeURIComponent(query)}`);
      if (response.ok) {
        const data = await response.json();
        if (data.nodes.length > 0) {
          setGraphData({ nodes: data.nodes, edges: data.edges });
        }
      }
    } catch {
      // Fall back to local search
    }

    // Local search
    const found = Object.values(taxa).find(
      (t) =>
        t.scientific_name.toLowerCase().includes(query) ||
        t.common_name?.toLowerCase().includes(query)
    );
    if (found) {
      setSelectedTaxon(found);
    }
  };

  const getChildren = (parentId: string): TaxonInfo[] => {
    return Object.values(taxa).filter((t) => t.parent === parentId);
  };

  const handleNodeClick = useCallback((node: GraphNode) => {
    if (node.type === "taxon" && taxa[node.id]) {
      setSelectedTaxon(taxa[node.id]);
    }
  }, [taxa]);

  const handleNodeDoubleClick = useCallback((node: GraphNode) => {
    // Expand node - fetch children from API
    console.log("Double-clicked node:", node);
  }, []);

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 text-white">
      {/* Header */}
      <header className="border-b border-gray-700/50 bg-gray-900/80 backdrop-blur-sm sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link href="/apps" className="p-2 hover:bg-gray-800 rounded-lg transition-colors">
              <ArrowLeft className="w-5 h-5" />
            </Link>
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-purple-500/20">
                <Activity className="w-6 h-6 text-purple-400" />
              </div>
              <div>
                <h1 className="text-xl font-bold">Ancestry Tools</h1>
                <p className="text-xs text-gray-400">
                  Fungal Taxonomy & Phylogeny
                  {dataSource === "mindex" && (
                    <span className="ml-2 px-1.5 py-0.5 rounded bg-green-500/20 text-green-400 text-[10px]">
                      MINDEX
                    </span>
                  )}
                </p>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={fetchTaxonomyData}
              disabled={loading}
              className="p-2 hover:bg-gray-800 rounded-lg transition-colors"
              title="Refresh data"
            >
              <RefreshCw className={`w-5 h-5 ${loading ? "animate-spin" : ""}`} />
            </button>
            <Link
              href="/ancestry/tools"
              className="flex items-center gap-2 px-4 py-2 bg-purple-600 hover:bg-purple-700 rounded-lg text-sm font-medium"
            >
              All Tools
              <ChevronRight className="w-4 h-4" />
            </Link>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 py-6">
        {/* Search Bar */}
        <div className="mb-8">
          <div className="relative max-w-2xl mx-auto">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSearch()}
              placeholder="Search for any fungal species, genus, or family..."
              className="w-full pl-12 pr-4 py-3 bg-gray-800/50 border border-gray-700/50 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-purple-500"
            />
            <button
              onClick={handleSearch}
              className="absolute right-2 top-1/2 -translate-y-1/2 px-4 py-1.5 bg-purple-600 hover:bg-purple-700 rounded-lg text-sm font-medium"
            >
              Search
            </button>
          </div>
        </div>

        {/* Quick Tools */}
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4 mb-8">
          {tools.map((tool) => (
            <button
              key={tool.id}
              onClick={() => tool.status === "available" && setActiveTool(tool.id)}
              className={`p-4 rounded-xl border text-center transition-all ${
                activeTool === tool.id
                  ? "bg-purple-500/20 border-purple-500"
                  : tool.status === "available"
                  ? "bg-gray-800/50 border-gray-700/50 hover:border-purple-500/50"
                  : "bg-gray-800/30 border-gray-700/30 opacity-50 cursor-not-allowed"
              }`}
            >
              <tool.icon className={`w-6 h-6 mx-auto mb-2 ${
                activeTool === tool.id ? "text-purple-400" : "text-gray-400"
              }`} />
              <div className="text-sm font-medium">{tool.name}</div>
            </button>
          ))}
        </div>

        {/* Graph View Mode */}
        {activeTool === "graph-view" ? (
          <div className="rounded-xl bg-gray-800/50 border border-gray-700/50 overflow-hidden">
            <div className="p-4 border-b border-gray-700/50 flex items-center justify-between">
              <h2 className="font-semibold flex items-center gap-2">
                <Network className="w-5 h-5 text-purple-400" />
                Phylogenetic Network
              </h2>
              <div className="text-sm text-gray-400">
                {graphData.nodes.length} nodes • {graphData.edges.length} edges
              </div>
            </div>
            <GraphCanvas
              nodes={graphData.nodes}
              edges={graphData.edges}
              layout="breadthfirst"
              onNodeClick={handleNodeClick}
              onNodeDoubleClick={handleNodeDoubleClick}
              selectedNodeId={selectedTaxon?.id}
              className="h-[600px]"
            />
          </div>
        ) : (
          /* Taxonomy Browser Mode */
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Taxonomy Tree */}
            <div className="lg:col-span-1">
              <div className="rounded-xl bg-gray-800/50 border border-gray-700/50 overflow-hidden">
                <div className="p-4 border-b border-gray-700/50">
                  <h2 className="font-semibold flex items-center gap-2">
                    <GitBranch className="w-5 h-5 text-purple-400" />
                    Taxonomy Tree
                  </h2>
                </div>
                <div className="p-4 max-h-[600px] overflow-y-auto">
                  {loading ? (
                    <div className="flex items-center justify-center py-8">
                      <Loader2 className="w-6 h-6 animate-spin text-purple-400" />
                    </div>
                  ) : (
                    <div className="space-y-1">
                      {Object.values(taxa)
                        .filter((t) => !t.parent)
                        .map((taxon) => (
                          <TaxonTreeItem
                            key={taxon.id}
                            taxon={taxon}
                            selected={selectedTaxon?.id === taxon.id}
                            onSelect={setSelectedTaxon}
                            getChildren={getChildren}
                          />
                        ))}
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* Selected Taxon Details */}
            <div className="lg:col-span-2">
              {selectedTaxon ? (
                <div className="rounded-xl bg-gray-800/50 border border-gray-700/50 overflow-hidden">
                  <div className="p-6">
                    <div className="flex items-start justify-between mb-6">
                      <div>
                        <div className="text-sm text-purple-400 uppercase tracking-wider mb-1">
                          {selectedTaxon.rank}
                        </div>
                        <h2 className="text-2xl font-bold italic">{selectedTaxon.scientific_name}</h2>
                        {selectedTaxon.common_name && (
                          <div className="text-lg text-gray-400">{selectedTaxon.common_name}</div>
                        )}
                        {selectedTaxon.gbif_id && (
                          <a
                            href={`https://www.gbif.org/species/${selectedTaxon.gbif_id}`}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-xs text-blue-400 hover:underline mt-1 inline-block"
                          >
                            GBIF: {selectedTaxon.gbif_id} ↗
                          </a>
                        )}
                      </div>
                      <div className="text-right">
                        <div className="text-2xl font-bold text-purple-400">
                          {selectedTaxon.children_count.toLocaleString()}
                        </div>
                        <div className="text-xs text-gray-500">child taxa</div>
                      </div>
                    </div>

                    <p className="text-gray-300 mb-6">{selectedTaxon.description}</p>

                    <div className="grid grid-cols-2 gap-4 mb-6">
                      <div className="p-4 rounded-lg bg-gray-900/50">
                        <div className="flex items-center gap-2 mb-2">
                          <Microscope className="w-4 h-4 text-gray-500" />
                          <span className="text-sm text-gray-400">Observations</span>
                        </div>
                        <div className="text-xl font-bold">
                          {selectedTaxon.observations_count.toLocaleString()}
                        </div>
                      </div>
                      <div className="p-4 rounded-lg bg-gray-900/50">
                        <div className="flex items-center gap-2 mb-2">
                          <Database className="w-4 h-4 text-gray-500" />
                          <span className="text-sm text-gray-400">In MINDEX</span>
                        </div>
                        <div className="text-xl font-bold text-green-400">Yes</div>
                      </div>
                    </div>

                    {/* Child Taxa */}
                    <div>
                      <h3 className="font-semibold mb-3">Child Taxa</h3>
                      <div className="space-y-2">
                        {getChildren(selectedTaxon.id).length > 0 ? (
                          getChildren(selectedTaxon.id).map((child) => (
                            <button
                              key={child.id}
                              onClick={() => setSelectedTaxon(child)}
                              className="w-full p-3 rounded-lg bg-gray-900/50 hover:bg-gray-700/50 text-left flex items-center justify-between transition-colors"
                            >
                              <div>
                                <div className="font-medium italic">{child.scientific_name}</div>
                                <div className="text-xs text-gray-500">
                                  {child.rank} • {child.children_count.toLocaleString()} species
                                </div>
                              </div>
                              <ChevronRight className="w-4 h-4 text-gray-500" />
                            </button>
                          ))
                        ) : (
                          <div className="text-sm text-gray-500">No child taxa available</div>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="rounded-xl bg-gray-800/50 border border-gray-700/50 p-8 text-center">
                  <Activity className="w-12 h-12 mx-auto mb-4 text-gray-600" />
                  <p className="text-gray-400">Select a taxon to view details</p>
                </div>
              )}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

// Tree Item Component
function TaxonTreeItem({
  taxon,
  selected,
  onSelect,
  getChildren,
  depth = 0,
}: {
  taxon: TaxonInfo;
  selected: boolean;
  onSelect: (t: TaxonInfo) => void;
  getChildren: (id: string) => TaxonInfo[];
  depth?: number;
}) {
  const [expanded, setExpanded] = useState(depth < 2);
  const children = getChildren(taxon.id);
  const hasChildren = children.length > 0;

  return (
    <div>
      <button
        onClick={() => {
          onSelect(taxon);
          if (hasChildren) setExpanded(!expanded);
        }}
        className={`w-full flex items-center gap-2 px-2 py-1.5 rounded-lg text-left transition-colors ${
          selected ? "bg-purple-500/20 text-purple-400" : "hover:bg-gray-700/50"
        }`}
        style={{ paddingLeft: `${depth * 12 + 8}px` }}
      >
        {hasChildren && (
          <ChevronRight className={`w-4 h-4 transition-transform ${expanded ? "rotate-90" : ""}`} />
        )}
        {!hasChildren && <span className="w-4" />}
        <span className="text-sm truncate">{taxon.scientific_name}</span>
      </button>
      
      {expanded && hasChildren && (
        <div>
          {children.map((child) => (
            <TaxonTreeItem
              key={child.id}
              taxon={child}
              selected={selected}
              onSelect={onSelect}
              getChildren={getChildren}
              depth={depth + 1}
            />
          ))}
        </div>
      )}
    </div>
  );
}
