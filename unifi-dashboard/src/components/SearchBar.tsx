"use client";

import { useState, useEffect } from "react";
import { Search, X, Cpu, Users, Database, Workflow, Globe } from "lucide-react";

interface SearchResult {
  type: "agent" | "service" | "person" | "database";
  name: string;
  subtitle: string;
  icon: React.ComponentType<{ className?: string }>;
}

interface SearchBarProps {
  onSearch?: (query: string) => void;
}

const allResults: SearchResult[] = [
  // Agents
  {
    type: "agent",
    name: "MYCA Orchestrator",
    subtitle: "10.0.0.1 • Core",
    icon: Cpu,
  },
  {
    type: "agent",
    name: "Financial Agent",
    subtitle: "10.0.0.172 • Financial",
    icon: Cpu,
  },
  {
    type: "agent",
    name: "Mycology Research",
    subtitle: "10.0.0.248 • Mycology",
    icon: Cpu,
  },
  {
    type: "agent",
    name: "Project Manager",
    subtitle: "10.0.0.90 • Core",
    icon: Cpu,
  },
  {
    type: "agent",
    name: "Opportunity Scout",
    subtitle: "10.0.0.91 • Research",
    icon: Cpu,
  },
  {
    type: "agent",
    name: "Marketing Agent",
    subtitle: "10.0.0.228 • Communication",
    icon: Cpu,
  },
  {
    type: "agent",
    name: "MycoDAO Agent",
    subtitle: "10.0.0.105 • DAO",
    icon: Cpu,
  },
  {
    type: "agent",
    name: "Dashboard Agent",
    subtitle: "10.0.0.184 • Core",
    icon: Cpu,
  },
  // Services
  { 
    type: "service", 
    name: "n8n Workflows", 
    subtitle: "Workflow Automation", 
    icon: Workflow 
  },
  { 
    type: "service", 
    name: "External APIs", 
    subtitle: "Third-party Integrations", 
    icon: Globe 
  },
  // Databases
  { 
    type: "database", 
    name: "PostgreSQL", 
    subtitle: "Primary Database", 
    icon: Database 
  },
  { 
    type: "database", 
    name: "Redis Cache", 
    subtitle: "Caching Layer", 
    icon: Database 
  },
  { 
    type: "database", 
    name: "Knowledge Graph", 
    subtitle: "Graph Database", 
    icon: Database 
  },
  // People
  { 
    type: "person", 
    name: "Human Operator", 
    subtitle: "System Administrator", 
    icon: Users 
  },
];

export function SearchBar({ onSearch }: SearchBarProps) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [isOpen, setIsOpen] = useState(false);

  useEffect(() => {
    if (query.length > 0) {
      const filtered = allResults.filter(
        (result) =>
          result.name.toLowerCase().includes(query.toLowerCase()) ||
          result.subtitle.toLowerCase().includes(query.toLowerCase())
      );
      setResults(filtered);
      setIsOpen(true);
    } else {
      setResults([]);
      setIsOpen(false);
    }
  }, [query]);

  const handleSelect = (result: SearchResult) => {
    setQuery("");
    setIsOpen(false);
    if (onSearch) {
      onSearch(result.name);
    }
  };

  const getTypeColor = (type: string) => {
    switch (type) {
      case "agent":
        return "bg-purple-500/20 text-purple-400";
      case "service":
        return "bg-blue-500/20 text-blue-400";
      case "database":
        return "bg-orange-500/20 text-orange-400";
      case "person":
        return "bg-green-500/20 text-green-400";
      default:
        return "bg-gray-500/20 text-gray-400";
    }
  };

  return (
    <div className="relative w-full max-w-md">
      <div className="relative">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search agents, services, databases..."
          className="w-full rounded-lg bg-[#0F172A] py-2 pl-10 pr-10 text-sm text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-purple-500"
        />
        {query && (
          <button
            onClick={() => setQuery("")}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-white"
          >
            <X className="h-4 w-4" />
          </button>
        )}
      </div>

      {/* Search Results Dropdown */}
      {isOpen && results.length > 0 && (
        <div className="absolute top-full z-50 mt-2 w-full rounded-lg border border-gray-700 bg-[#1E293B] shadow-xl">
          <div className="max-h-80 overflow-auto">
            {results.map((result, index) => (
              <button
                key={index}
                onClick={() => handleSelect(result)}
                className="flex w-full items-center gap-3 border-b border-gray-700 px-4 py-3 text-left hover:bg-gray-700 last:border-b-0"
              >
                <div className={`flex h-10 w-10 items-center justify-center rounded-lg ${getTypeColor(result.type)}`}>
                  <result.icon className="h-5 w-5" />
                </div>
                <div className="flex-1">
                  <div className="text-sm font-medium text-white">{result.name}</div>
                  <div className="text-xs text-gray-400">{result.subtitle}</div>
                </div>
                <div className={`rounded px-2 py-1 text-xs capitalize ${getTypeColor(result.type)}`}>
                  {result.type}
                </div>
              </button>
            ))}
          </div>
        </div>
      )}

      {isOpen && query && results.length === 0 && (
        <div className="absolute top-full z-50 mt-2 w-full rounded-lg border border-gray-700 bg-[#1E293B] p-4 text-center text-sm text-gray-400 shadow-xl">
          No results found for "{query}"
        </div>
      )}
    </div>
  );
}
