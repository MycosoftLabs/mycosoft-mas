"use client";

import { useState, useEffect, useCallback } from "react";
import { Search, X, Cpu, Database, Workflow, Globe, Server, Loader2 } from "lucide-react";

interface SearchResult {
  type: "agent" | "service" | "database" | "workflow" | "integration";
  name: string;
  subtitle: string;
  id: string;
  status?: string;
  category?: string;
}

interface SearchBarProps {
  onSearch?: (query: string, result?: SearchResult) => void;
}

export function SearchBar({ onSearch }: SearchBarProps) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [isOpen, setIsOpen] = useState(false);
  const [loading, setLoading] = useState(false);

  // Debounced search
  const searchAPI = useCallback(async (searchQuery: string) => {
    if (!searchQuery.trim()) {
      setResults([]);
      setIsOpen(false);
      return;
    }
    
    setLoading(true);
    try {
      const res = await fetch(`/api/search?q=${encodeURIComponent(searchQuery)}`);
      if (res.ok) {
        const data = await res.json();
        setResults(data.results || []);
        setIsOpen(true);
      }
    } catch (error) {
      console.error("Search error:", error);
      setResults([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const timer = setTimeout(() => {
      searchAPI(query);
    }, 200); // 200ms debounce
    
    return () => clearTimeout(timer);
  }, [query, searchAPI]);

  const handleSelect = (result: SearchResult) => {
    setQuery("");
    setIsOpen(false);
    if (onSearch) {
      onSearch(result.name, result);
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
      case "workflow":
        return "bg-cyan-500/20 text-cyan-400";
      case "integration":
        return "bg-green-500/20 text-green-400";
      default:
        return "bg-gray-500/20 text-gray-400";
    }
  };

  const getTypeIcon = (type: string) => {
    switch (type) {
      case "agent":
        return <Cpu className="h-5 w-5" />;
      case "service":
        return <Server className="h-5 w-5" />;
      case "database":
        return <Database className="h-5 w-5" />;
      case "workflow":
        return <Workflow className="h-5 w-5" />;
      case "integration":
        return <Globe className="h-5 w-5" />;
      default:
        return <Server className="h-5 w-5" />;
    }
  };

  return (
    <div className="relative w-full max-w-md">
      <div className="relative">
        {loading ? (
          <Loader2 className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-purple-400 animate-spin" />
        ) : (
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
        )}
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
                key={result.id || index}
                onClick={() => handleSelect(result)}
                className="flex w-full items-center gap-3 border-b border-gray-700 px-4 py-3 text-left hover:bg-gray-700 last:border-b-0"
              >
                <div className={`flex h-10 w-10 items-center justify-center rounded-lg ${getTypeColor(result.type)}`}>
                  {getTypeIcon(result.type)}
                </div>
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-white">{result.name}</span>
                    {result.status === "active" && (
                      <span className="h-2 w-2 rounded-full bg-green-500" />
                    )}
                  </div>
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

      {isOpen && query && results.length === 0 && !loading && (
        <div className="absolute top-full z-50 mt-2 w-full rounded-lg border border-gray-700 bg-[#1E293B] p-4 text-center text-sm text-gray-400 shadow-xl">
          No results found for &quot;{query}&quot;
        </div>
      )}
    </div>
  );
}
