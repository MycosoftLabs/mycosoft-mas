"use client";

import { useState } from "react";
import Link from "next/link";
import {
  ArrowLeft,
  Search,
  Dna,
  GitBranch,
  Book,
  Globe,
  Activity,
  Microscope,
  Map,
  BarChart3,
  FileText,
  Layers,
  Maximize2,
  Minimize2,
  X,
  Move,
} from "lucide-react";

interface Widget {
  id: string;
  name: string;
  icon: React.ComponentType<{ className?: string }>;
  component: React.ComponentType<{ isExpanded: boolean }>;
  defaultSize: "small" | "medium" | "large";
}

// Widget Components
function TaxonomySearchWidget({ isExpanded }: { isExpanded: boolean }) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<Array<{ name: string; rank: string }>>([]);

  const handleSearch = () => {
    // Mock search results
    if (query) {
      setResults([
        { name: "Amanita muscaria", rank: "Species" },
        { name: "Amanita phalloides", rank: "Species" },
        { name: "Amanita caesarea", rank: "Species" },
      ]);
    }
  };

  return (
    <div className={isExpanded ? "p-6" : "p-4"}>
      <div className="flex gap-2 mb-4">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSearch()}
          placeholder="Search species..."
          className="flex-1 px-3 py-2 bg-gray-900 border border-gray-700 rounded-lg text-sm"
        />
        <button
          onClick={handleSearch}
          className="px-4 py-2 bg-purple-600 hover:bg-purple-700 rounded-lg text-sm"
        >
          Search
        </button>
      </div>
      {results.length > 0 && (
        <div className="space-y-2">
          {results.map((r, i) => (
            <div key={i} className="p-2 bg-gray-900/50 rounded-lg text-sm">
              <div className="font-medium italic">{r.name}</div>
              <div className="text-xs text-gray-500">{r.rank}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function PhylogeneticTreeWidget({ isExpanded }: { isExpanded: boolean }) {
  return (
    <div className={isExpanded ? "p-6" : "p-4"}>
      <div className="text-center text-gray-500 mb-4">Phylogenetic Tree Visualization</div>
      {/* Simple ASCII tree representation */}
      <pre className="text-xs text-gray-400 font-mono bg-gray-900/50 p-4 rounded-lg overflow-auto">
{`Fungi
├── Ascomycota
│   ├── Pezizomycetes
│   │   └── Pezizales
│   └── Sordariomycetes
│       └── Hypocreales
└── Basidiomycota
    ├── Agaricomycetes
    │   ├── Agaricales
    │   │   ├── Amanitaceae
    │   │   └── Boletaceae
    │   └── Polyporales
    └── Ustilaginomycetes
        └── Ustilaginales`}
      </pre>
    </div>
  );
}

function DistributionMapWidget({ isExpanded }: { isExpanded: boolean }) {
  return (
    <div className={isExpanded ? "p-6" : "p-4"}>
      <div className="aspect-video bg-gray-900/50 rounded-lg flex items-center justify-center relative overflow-hidden">
        {/* Simple world map placeholder */}
        <div 
          className="absolute inset-0 opacity-30"
          style={{
            background: "linear-gradient(to right, #1a1a2e 50%, #16213e 50%)",
          }}
        />
        {/* Distribution dots */}
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="relative w-full h-full">
            {[
              { x: 25, y: 35 }, { x: 45, y: 40 }, { x: 55, y: 30 },
              { x: 75, y: 45 }, { x: 30, y: 55 }, { x: 60, y: 50 },
            ].map((pos, i) => (
              <div
                key={i}
                className="absolute w-3 h-3 bg-green-500 rounded-full animate-pulse"
                style={{ left: `${pos.x}%`, top: `${pos.y}%` }}
              />
            ))}
          </div>
        </div>
        <Globe className="w-12 h-12 text-gray-600 z-10" />
      </div>
      <div className="mt-3 text-xs text-center text-gray-500">
        Global distribution of selected taxon
      </div>
    </div>
  );
}

function StatisticsWidget({ isExpanded }: { isExpanded: boolean }) {
  const stats = [
    { label: "Species in MINDEX", value: "12,450" },
    { label: "Genera", value: "1,230" },
    { label: "Families", value: "156" },
    { label: "Observations", value: "2.5M" },
  ];

  return (
    <div className={isExpanded ? "p-6" : "p-4"}>
      <div className="grid grid-cols-2 gap-3">
        {stats.map((stat) => (
          <div key={stat.label} className="p-3 bg-gray-900/50 rounded-lg text-center">
            <div className="text-xl font-bold text-purple-400">{stat.value}</div>
            <div className="text-xs text-gray-500">{stat.label}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

function RecentActivityWidget({ isExpanded }: { isExpanded: boolean }) {
  const activities = [
    { action: "New species added", name: "Russula cyanoxantha", time: "2 hours ago" },
    { action: "Synonym merged", name: "Agaricus campestris", time: "5 hours ago" },
    { action: "Distribution updated", name: "Boletus edulis", time: "1 day ago" },
    { action: "DNA sequence added", name: "Trametes versicolor", time: "2 days ago" },
  ];

  return (
    <div className={isExpanded ? "p-6" : "p-4"}>
      <div className="space-y-3">
        {activities.slice(0, isExpanded ? undefined : 3).map((activity, i) => (
          <div key={i} className="flex items-start gap-3 p-2 bg-gray-900/50 rounded-lg">
            <Activity className="w-4 h-4 text-purple-400 mt-0.5" />
            <div className="flex-1 min-w-0">
              <div className="text-sm">{activity.action}</div>
              <div className="text-xs text-gray-500 italic truncate">{activity.name}</div>
            </div>
            <div className="text-xs text-gray-600 whitespace-nowrap">{activity.time}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

function LiteratureWidget({ isExpanded }: { isExpanded: boolean }) {
  const papers = [
    { title: "Molecular phylogeny of Amanitaceae", authors: "Smith et al.", year: 2023 },
    { title: "New species of Cortinarius from Europe", authors: "Jones & Brown", year: 2024 },
    { title: "Bioactive compounds in Ganoderma", authors: "Lee et al.", year: 2023 },
  ];

  return (
    <div className={isExpanded ? "p-6" : "p-4"}>
      <div className="space-y-3">
        {papers.map((paper, i) => (
          <div key={i} className="p-3 bg-gray-900/50 rounded-lg">
            <div className="text-sm font-medium">{paper.title}</div>
            <div className="text-xs text-gray-500">
              {paper.authors} ({paper.year})
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

const widgets: Widget[] = [
  {
    id: "taxonomy-search",
    name: "Taxonomy Search",
    icon: Search,
    component: TaxonomySearchWidget,
    defaultSize: "medium",
  },
  {
    id: "phylogenetic-tree",
    name: "Phylogenetic Tree",
    icon: GitBranch,
    component: PhylogeneticTreeWidget,
    defaultSize: "large",
  },
  {
    id: "distribution-map",
    name: "Distribution Map",
    icon: Globe,
    component: DistributionMapWidget,
    defaultSize: "large",
  },
  {
    id: "statistics",
    name: "Statistics",
    icon: BarChart3,
    component: StatisticsWidget,
    defaultSize: "small",
  },
  {
    id: "recent-activity",
    name: "Recent Activity",
    icon: Activity,
    component: RecentActivityWidget,
    defaultSize: "medium",
  },
  {
    id: "literature",
    name: "Literature",
    icon: Book,
    component: LiteratureWidget,
    defaultSize: "medium",
  },
];

interface WidgetState {
  id: string;
  visible: boolean;
  expanded: boolean;
  size: "small" | "medium" | "large";
}

export default function AncestryToolsPage() {
  const [widgetStates, setWidgetStates] = useState<WidgetState[]>(
    widgets.map((w) => ({
      id: w.id,
      visible: true,
      expanded: false,
      size: w.defaultSize,
    }))
  );

  const toggleExpand = (id: string) => {
    setWidgetStates((prev) =>
      prev.map((w) => (w.id === id ? { ...w, expanded: !w.expanded } : w))
    );
  };

  const hideWidget = (id: string) => {
    setWidgetStates((prev) =>
      prev.map((w) => (w.id === id ? { ...w, visible: false } : w))
    );
  };

  const showWidget = (id: string) => {
    setWidgetStates((prev) =>
      prev.map((w) => (w.id === id ? { ...w, visible: true } : w))
    );
  };

  const getGridClass = (size: string, expanded: boolean) => {
    if (expanded) return "col-span-full";
    switch (size) {
      case "small":
        return "col-span-1";
      case "large":
        return "col-span-2";
      default:
        return "col-span-1 md:col-span-1";
    }
  };

  const hiddenWidgets = widgetStates.filter((w) => !w.visible);

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 text-white">
      {/* Header */}
      <header className="border-b border-gray-700/50 bg-gray-900/80 backdrop-blur-sm sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link href="/ancestry" className="p-2 hover:bg-gray-800 rounded-lg transition-colors">
              <ArrowLeft className="w-5 h-5" />
            </Link>
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-purple-500/20">
                <Layers className="w-6 h-6 text-purple-400" />
              </div>
              <div>
                <h1 className="text-xl font-bold">Ancestry Tools</h1>
                <p className="text-xs text-gray-400">Customizable research widgets</p>
              </div>
            </div>
          </div>

          {/* Hidden Widgets Dropdown */}
          {hiddenWidgets.length > 0 && (
            <div className="relative group">
              <button className="flex items-center gap-2 px-3 py-2 bg-gray-800 hover:bg-gray-700 rounded-lg text-sm">
                <Layers className="w-4 h-4" />
                {hiddenWidgets.length} hidden
              </button>
              <div className="absolute right-0 top-full mt-2 w-48 bg-gray-800 border border-gray-700 rounded-lg shadow-xl opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all">
                {hiddenWidgets.map((ws) => {
                  const widget = widgets.find((w) => w.id === ws.id)!;
                  return (
                    <button
                      key={ws.id}
                      onClick={() => showWidget(ws.id)}
                      className="w-full px-4 py-2 text-left text-sm hover:bg-gray-700 flex items-center gap-2"
                    >
                      <widget.icon className="w-4 h-4" />
                      {widget.name}
                    </button>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 py-6">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {widgetStates
            .filter((ws) => ws.visible)
            .map((ws) => {
              const widget = widgets.find((w) => w.id === ws.id)!;
              const WidgetComponent = widget.component;

              return (
                <div
                  key={ws.id}
                  className={`rounded-xl bg-gray-800/50 border border-gray-700/50 overflow-hidden transition-all ${getGridClass(
                    ws.size,
                    ws.expanded
                  )}`}
                >
                  {/* Widget Header */}
                  <div className="px-4 py-3 border-b border-gray-700/50 flex items-center justify-between bg-gray-800/30">
                    <div className="flex items-center gap-2">
                      <widget.icon className="w-4 h-4 text-purple-400" />
                      <span className="font-medium text-sm">{widget.name}</span>
                    </div>
                    <div className="flex items-center gap-1">
                      <button
                        onClick={() => toggleExpand(ws.id)}
                        className="p-1 hover:bg-gray-700 rounded"
                        title={ws.expanded ? "Minimize" : "Maximize"}
                      >
                        {ws.expanded ? (
                          <Minimize2 className="w-4 h-4" />
                        ) : (
                          <Maximize2 className="w-4 h-4" />
                        )}
                      </button>
                      <button
                        onClick={() => hideWidget(ws.id)}
                        className="p-1 hover:bg-gray-700 rounded"
                        title="Hide"
                      >
                        <X className="w-4 h-4" />
                      </button>
                    </div>
                  </div>

                  {/* Widget Content */}
                  <WidgetComponent isExpanded={ws.expanded} />
                </div>
              );
            })}
        </div>
      </main>
    </div>
  );
}
