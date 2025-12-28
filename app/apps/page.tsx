"use client";

import Link from "next/link";
import {
  MapPin,
  Dna,
  Microscope,
  Leaf,
  Beaker,
  Camera,
  Database,
  Thermometer,
  Wind,
  Droplets,
  Sun,
  Cloud,
  Activity,
  Book,
} from "lucide-react";

interface AppCard {
  id: string;
  name: string;
  description: string;
  icon: React.ComponentType<{ className?: string }>;
  href: string;
  status: "available" | "coming_soon" | "beta";
  category: string;
}

const apps: AppCard[] = [
  // Mycology Apps
  {
    id: "spore-tracker",
    name: "Spore Tracker",
    description: "Track and map fungal observations with real-time data overlay",
    icon: MapPin,
    href: "/apps/spore-tracker",
    status: "available",
    category: "Mycology",
  },
  {
    id: "species-id",
    name: "Species Identifier",
    description: "AI-powered fungal species identification from photos",
    icon: Camera,
    href: "/apps/species-id",
    status: "coming_soon",
    category: "Mycology",
  },
  {
    id: "growth-simulator",
    name: "Growth Simulator",
    description: "Simulate mycelium growth patterns and conditions",
    icon: Leaf,
    href: "/apps/growth-simulator",
    status: "beta",
    category: "Mycology",
  },
  {
    id: "cultivation-guide",
    name: "Cultivation Guide",
    description: "Step-by-step guides for growing edible and medicinal fungi",
    icon: Book,
    href: "/apps/cultivation-guide",
    status: "coming_soon",
    category: "Mycology",
  },
  
  // Research Apps
  {
    id: "dna-analyzer",
    name: "DNA Analyzer",
    description: "Analyze fungal DNA sequences and phylogenetic data",
    icon: Dna,
    href: "/apps/dna-analyzer",
    status: "coming_soon",
    category: "Research",
  },
  {
    id: "compound-explorer",
    name: "Compound Explorer",
    description: "Explore bioactive compounds found in fungi",
    icon: Beaker,
    href: "/apps/compound-explorer",
    status: "coming_soon",
    category: "Research",
  },
  {
    id: "microscopy-lab",
    name: "Microscopy Lab",
    description: "Digital microscopy tools for spore analysis",
    icon: Microscope,
    href: "/apps/microscopy-lab",
    status: "coming_soon",
    category: "Research",
  },
  
  // Environmental Apps
  {
    id: "env-monitor",
    name: "Environment Monitor",
    description: "Monitor environmental conditions for optimal growth",
    icon: Thermometer,
    href: "/apps/env-monitor",
    status: "available",
    category: "Environment",
  },
  {
    id: "weather-tracker",
    name: "Weather Tracker",
    description: "Track weather patterns that affect fungal fruiting",
    icon: Cloud,
    href: "/apps/weather-tracker",
    status: "coming_soon",
    category: "Environment",
  },
  {
    id: "humidity-mapper",
    name: "Humidity Mapper",
    description: "Map humidity levels across monitored areas",
    icon: Droplets,
    href: "/apps/humidity-mapper",
    status: "coming_soon",
    category: "Environment",
  },
  
  // Data Apps
  {
    id: "mindex",
    name: "MINDEX Search",
    description: "Search the MINDEX fungal knowledge database",
    icon: Database,
    href: "/mindex",
    status: "available",
    category: "Data",
  },
  {
    id: "ancestry",
    name: "Ancestry Tools",
    description: "Research and visualize fungal ancestry and lineage",
    icon: Activity,
    href: "/ancestry",
    status: "available",
    category: "Data",
  },
];

export default function AppsPage() {
  const categories = [...new Set(apps.map((app) => app.category))];

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "available":
        return <span className="px-2 py-0.5 text-xs rounded-full bg-green-500/20 text-green-400">Available</span>;
      case "beta":
        return <span className="px-2 py-0.5 text-xs rounded-full bg-yellow-500/20 text-yellow-400">Beta</span>;
      case "coming_soon":
        return <span className="px-2 py-0.5 text-xs rounded-full bg-gray-500/20 text-gray-400">Coming Soon</span>;
      default:
        return null;
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 text-white">
      {/* Header */}
      <header className="border-b border-gray-700/50 bg-gray-900/80 backdrop-blur-sm sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-purple-500 to-blue-600 flex items-center justify-center">
              <svg viewBox="0 0 24 24" className="w-6 h-6 fill-white">
                <path d="M9.5 2A2.5 2.5 0 0 1 12 4.5v15a2.5 2.5 0 0 1-4.96.44 2.5 2.5 0 0 1-2.96-3.08 3 3 0 0 1-.34-5.58 2.5 2.5 0 0 1 1.32-4.24 2.5 2.5 0 0 1 4.44-2.54M14.5 2A2.5 2.5 0 0 0 12 4.5v15a2.5 2.5 0 0 0 4.96.44 2.5 2.5 0 0 0 2.96-3.08 3 3 0 0 0 .34-5.58 2.5 2.5 0 0 0-1.32-4.24 2.5 2.5 0 0 0-4.44-2.54" />
              </svg>
            </div>
            <div>
              <h1 className="text-xl font-bold">MYCOSOFT Apps</h1>
              <p className="text-xs text-gray-400">{apps.length} applications available</p>
            </div>
          </div>
          
          <Link href="/natureos" className="text-sm text-gray-400 hover:text-white transition-colors">
            Back to NatureOS
          </Link>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 py-8">
        {categories.map((category) => (
          <div key={category} className="mb-12">
            <h2 className="text-lg font-semibold mb-4 text-gray-300">{category}</h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
              {apps
                .filter((app) => app.category === category)
                .map((app) => (
                  <Link
                    key={app.id}
                    href={app.status === "coming_soon" ? "#" : app.href}
                    className={`group p-4 rounded-xl bg-gray-800/50 border border-gray-700/50 transition-all ${
                      app.status === "coming_soon"
                        ? "opacity-60 cursor-not-allowed"
                        : "hover:border-purple-500/50 hover:bg-gray-800 hover:scale-[1.02]"
                    }`}
                  >
                    <div className="flex items-start justify-between mb-3">
                      <div className={`p-3 rounded-lg bg-gray-700/50 ${
                        app.status !== "coming_soon" ? "group-hover:bg-purple-500/20" : ""
                      } transition-colors`}>
                        <app.icon className={`w-6 h-6 text-gray-400 ${
                          app.status !== "coming_soon" ? "group-hover:text-purple-400" : ""
                        } transition-colors`} />
                      </div>
                      {getStatusBadge(app.status)}
                    </div>
                    <h3 className="font-semibold text-white mb-1">{app.name}</h3>
                    <p className="text-sm text-gray-500">{app.description}</p>
                  </Link>
                ))}
            </div>
          </div>
        ))}
      </main>
    </div>
  );
}
