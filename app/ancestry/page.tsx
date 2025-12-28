"use client";

import { useState } from "react";
import Link from "next/link";
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
} from "lucide-react";

interface TaxonInfo {
  id: string;
  scientific_name: string;
  common_name?: string;
  rank: string;
  parent?: string;
  children_count: number;
  observations_count: number;
  description?: string;
}

// Mock taxonomic data
const mockTaxa: Record<string, TaxonInfo> = {
  fungi: {
    id: "fungi",
    scientific_name: "Fungi",
    common_name: "Fungi",
    rank: "Kingdom",
    children_count: 144000,
    observations_count: 5000000,
    description: "The kingdom Fungi comprises eukaryotic organisms that include microorganisms such as yeasts and molds, as well as the more familiar mushrooms.",
  },
  ascomycota: {
    id: "ascomycota",
    scientific_name: "Ascomycota",
    common_name: "Sac Fungi",
    rank: "Phylum",
    parent: "fungi",
    children_count: 64000,
    observations_count: 2500000,
    description: "The largest phylum of Fungi, characterized by the ascus, a microscopic sexual structure in which spores are formed.",
  },
  basidiomycota: {
    id: "basidiomycota",
    scientific_name: "Basidiomycota",
    common_name: "Club Fungi",
    rank: "Phylum",
    parent: "fungi",
    children_count: 31500,
    observations_count: 2000000,
    description: "A large division of fungi characterized by the production of spores on club-shaped cells called basidia.",
  },
  agaricales: {
    id: "agaricales",
    scientific_name: "Agaricales",
    common_name: "Gilled Mushrooms",
    rank: "Order",
    parent: "basidiomycota",
    children_count: 13000,
    observations_count: 1500000,
    description: "The order that includes most of the familiar mushrooms, characterized by the presence of gills on the underside of the cap.",
  },
  amanitaceae: {
    id: "amanitaceae",
    scientific_name: "Amanitaceae",
    common_name: "Amanita Family",
    rank: "Family",
    parent: "agaricales",
    children_count: 600,
    observations_count: 200000,
    description: "A family of mushrooms that includes the deadly Amanita phalloides (death cap) as well as edible species like Amanita caesarea.",
  },
};

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
    id: "phylogenetic-tree",
    name: "Phylogenetic Tree",
    description: "Visualize evolutionary relationships",
    icon: Activity,
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
  const [selectedTaxon, setSelectedTaxon] = useState<TaxonInfo | null>(mockTaxa.fungi);
  const [activeTool, setActiveTool] = useState<string>("taxonomy-browser");

  const handleSearch = () => {
    // Search in mock data
    const query = searchQuery.toLowerCase();
    const found = Object.values(mockTaxa).find(
      (t) =>
        t.scientific_name.toLowerCase().includes(query) ||
        t.common_name?.toLowerCase().includes(query)
    );
    if (found) {
      setSelectedTaxon(found);
    }
  };

  const getChildren = (parentId: string): TaxonInfo[] => {
    return Object.values(mockTaxa).filter((t) => t.parent === parentId);
  };

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
                <p className="text-xs text-gray-400">Fungal Taxonomy & Phylogeny</p>
              </div>
            </div>
          </div>

          <Link
            href="/ancestry/tools"
            className="flex items-center gap-2 px-4 py-2 bg-purple-600 hover:bg-purple-700 rounded-lg text-sm font-medium"
          >
            All Tools
            <ChevronRight className="w-4 h-4" />
          </Link>
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
              <div className="p-4">
                {/* Tree View */}
                <div className="space-y-1">
                  {Object.values(mockTaxa)
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
