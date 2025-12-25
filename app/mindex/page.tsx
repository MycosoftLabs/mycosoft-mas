"use client"

import { useState } from "react"
import { Search, Database, Dna, MapPin, BookOpen, Microscope, Globe } from "lucide-react"

const SEARCH_CATEGORIES = [
  { id: "all", name: "All", icon: Search },
  { id: "species", name: "Species", icon: Microscope },
  { id: "genetics", name: "Genetics", icon: Dna },
  { id: "taxonomy", name: "Taxonomy", icon: BookOpen },
  { id: "geography", name: "Geography", icon: MapPin },
  { id: "documents", name: "Documents", icon: Database },
]

export default function MindexPage() {
  const [query, setQuery] = useState("")
  const [category, setCategory] = useState("all")
  const [results, setResults] = useState<unknown[]>([])
  const [loading, setLoading] = useState(false)

  const handleSearch = async () => {
    if (!query.trim()) return
    
    setLoading(true)
    try {
      // Search via MAS API
      const response = await fetch(`/api/mas/search?q=${encodeURIComponent(query)}&category=${category}`)
      const data = await response.json()
      setResults(data.results || [])
    } catch {
      // Fallback mock results
      setResults([
        {
          id: "1",
          type: "species",
          title: "Psilocybe cubensis",
          description: "Common psychoactive mushroom species found worldwide",
          taxonomy: "Fungi > Basidiomycota > Agaricomycetes > Agaricales > Hymenogastraceae",
        },
        {
          id: "2", 
          type: "species",
          title: "Ganoderma lucidum",
          description: "Reishi mushroom, used in traditional medicine",
          taxonomy: "Fungi > Basidiomycota > Agaricomycetes > Polyporales > Ganodermataceae",
        },
      ])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-[#0a1929] to-[#0a0a0f] text-white">
      {/* Hero Search */}
      <div className="px-4 py-16 md:py-24">
        <div className="max-w-4xl mx-auto text-center">
          <div className="flex items-center justify-center gap-3 mb-6">
            <Globe className="h-12 w-12 text-green-400" />
            <h1 className="text-4xl md:text-5xl font-bold bg-gradient-to-r from-green-400 to-blue-500 bg-clip-text text-transparent">
              MINDEX
            </h1>
          </div>
          <p className="text-lg text-gray-400 mb-8">
            Search the Mycosoft knowledge base — species, genetics, taxonomy, ancestry, and scientific documents
          </p>

          {/* Search Box */}
          <div className="relative max-w-2xl mx-auto">
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSearch()}
              placeholder="Search species, genetics, documents..."
              className="w-full rounded-xl bg-[#1e293b] border border-gray-700 px-6 py-4 pl-14 text-lg text-white placeholder-gray-500 focus:border-green-500 focus:outline-none focus:ring-2 focus:ring-green-500/20"
            />
            <Search className="absolute left-5 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-500" />
            <button
              onClick={handleSearch}
              disabled={loading}
              className="absolute right-3 top-1/2 -translate-y-1/2 rounded-lg bg-green-600 px-4 py-2 text-sm font-medium hover:bg-green-700 disabled:opacity-50"
            >
              {loading ? "Searching..." : "Search"}
            </button>
          </div>

          {/* Category Filters */}
          <div className="flex flex-wrap justify-center gap-2 mt-6">
            {SEARCH_CATEGORIES.map((cat) => (
              <button
                key={cat.id}
                onClick={() => setCategory(cat.id)}
                className={`flex items-center gap-2 rounded-full px-4 py-2 text-sm transition ${
                  category === cat.id
                    ? "bg-green-600 text-white"
                    : "bg-gray-800 text-gray-400 hover:bg-gray-700 hover:text-white"
                }`}
              >
                <cat.icon className="h-4 w-4" />
                {cat.name}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Results */}
      {results.length > 0 && (
        <div className="max-w-4xl mx-auto px-4 pb-16">
          <h2 className="text-lg font-medium text-gray-300 mb-4">
            {results.length} results found
          </h2>
          <div className="space-y-4">
            {results.map((result: Record<string, unknown>, i) => (
              <div
                key={String(result.id) || i}
                className="rounded-xl bg-[#1e293b] border border-gray-700 p-6 hover:border-green-500/50 transition cursor-pointer"
              >
                <div className="flex items-start gap-4">
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-green-600/20">
                    <Microscope className="h-5 w-5 text-green-400" />
                  </div>
                  <div className="flex-1">
                    <h3 className="text-lg font-semibold text-white">
                      {String(result.title || "Untitled")}
                    </h3>
                    <p className="text-gray-400 mt-1">
                      {String(result.description || "")}
                    </p>
                    {result.taxonomy && (
                      <p className="text-xs text-gray-500 mt-2 font-mono">
                        {String(result.taxonomy)}
                      </p>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Quick Links */}
      <div className="max-w-6xl mx-auto px-4 pb-16">
        <h2 className="text-xl font-semibold text-white mb-6">Explore Knowledge</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="rounded-xl bg-gradient-to-br from-purple-900/50 to-purple-600/20 border border-purple-500/30 p-6">
            <Dna className="h-8 w-8 text-purple-400 mb-3" />
            <h3 className="text-lg font-semibold text-white">Genetics Database</h3>
            <p className="text-gray-400 text-sm mt-1">DNA sequences, phenotypes, and genetic markers</p>
          </div>
          <div className="rounded-xl bg-gradient-to-br from-green-900/50 to-green-600/20 border border-green-500/30 p-6">
            <Microscope className="h-8 w-8 text-green-400 mb-3" />
            <h3 className="text-lg font-semibold text-white">Species Encyclopedia</h3>
            <p className="text-gray-400 text-sm mt-1">Comprehensive species data and taxonomy</p>
          </div>
          <div className="rounded-xl bg-gradient-to-br from-blue-900/50 to-blue-600/20 border border-blue-500/30 p-6">
            <MapPin className="h-8 w-8 text-blue-400 mb-3" />
            <h3 className="text-lg font-semibold text-white">Geospatial Data</h3>
            <p className="text-gray-400 text-sm mt-1">Distribution maps and habitat information</p>
          </div>
        </div>
      </div>
    </div>
  )
}

