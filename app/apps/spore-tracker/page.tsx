"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import {
  MapPin,
  ArrowLeft,
  RefreshCw,
  Filter,
  Layers,
  Thermometer,
  Droplets,
  Calendar,
  Eye,
  Plus,
} from "lucide-react";

interface Observation {
  id: string;
  scientific_name: string;
  common_name: string;
  latitude: number;
  longitude: number;
  observed_on: string;
  observer: string;
  quality_grade: string;
  photo_url?: string;
}

interface MapFilters {
  species: string;
  dateRange: "week" | "month" | "year" | "all";
  qualityGrade: "research" | "needs_id" | "all";
}

// Mock observation data (would come from MINDEX/iNaturalist API)
const mockObservations: Observation[] = [
  {
    id: "1",
    scientific_name: "Amanita muscaria",
    common_name: "Fly Agaric",
    latitude: 47.6062,
    longitude: -122.3321,
    observed_on: "2024-12-15",
    observer: "mycologist_01",
    quality_grade: "research",
    photo_url: "https://inaturalist-open-data.s3.amazonaws.com/photos/1/medium.jpg",
  },
  {
    id: "2",
    scientific_name: "Morchella esculenta",
    common_name: "Yellow Morel",
    latitude: 45.5152,
    longitude: -122.6784,
    observed_on: "2024-12-10",
    observer: "fungi_finder",
    quality_grade: "research",
  },
  {
    id: "3",
    scientific_name: "Cantharellus cibarius",
    common_name: "Golden Chanterelle",
    latitude: 48.4284,
    longitude: -123.3656,
    observed_on: "2024-12-20",
    observer: "mushroom_hunter",
    quality_grade: "needs_id",
  },
  {
    id: "4",
    scientific_name: "Pleurotus ostreatus",
    common_name: "Oyster Mushroom",
    latitude: 37.7749,
    longitude: -122.4194,
    observed_on: "2024-12-18",
    observer: "bay_forager",
    quality_grade: "research",
  },
  {
    id: "5",
    scientific_name: "Hericium erinaceus",
    common_name: "Lion's Mane",
    latitude: 40.7128,
    longitude: -74.006,
    observed_on: "2024-12-22",
    observer: "east_coast_fungi",
    quality_grade: "research",
  },
];

export default function SporeTrackerPage() {
  const [observations, setObservations] = useState<Observation[]>(mockObservations);
  const [selectedObservation, setSelectedObservation] = useState<Observation | null>(null);
  const [loading, setLoading] = useState(false);
  const [filters, setFilters] = useState<MapFilters>({
    species: "",
    dateRange: "month",
    qualityGrade: "all",
  });
  const [showFilters, setShowFilters] = useState(false);
  const [mapCenter] = useState({ lat: 39.8283, lng: -98.5795 }); // Center of USA

  useEffect(() => {
    // In production, fetch from MINDEX API
    // fetchObservations();
  }, [filters]);

  const fetchObservations = async () => {
    setLoading(true);
    try {
      // This would call the MINDEX API in production
      const response = await fetch("/api/mindex/observations?" + new URLSearchParams({
        species: filters.species,
        dateRange: filters.dateRange,
        qualityGrade: filters.qualityGrade,
      }));
      if (response.ok) {
        const data = await response.json();
        setObservations(data.observations || mockObservations);
      }
    } catch (error) {
      console.error("Error fetching observations:", error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-900 text-white">
      {/* Header */}
      <header className="border-b border-gray-700/50 bg-gray-900/80 backdrop-blur-sm sticky top-0 z-20">
        <div className="max-w-full mx-auto px-4 sm:px-6 py-3 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link href="/apps" className="p-2 hover:bg-gray-800 rounded-lg transition-colors">
              <ArrowLeft className="w-5 h-5" />
            </Link>
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-green-500/20">
                <MapPin className="w-6 h-6 text-green-400" />
              </div>
              <div>
                <h1 className="text-xl font-bold">Spore Tracker</h1>
                <p className="text-xs text-gray-400">{observations.length} observations</p>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => setShowFilters(!showFilters)}
              className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                showFilters ? "bg-green-600" : "bg-gray-800 hover:bg-gray-700"
              }`}
            >
              <Filter className="w-4 h-4" />
              Filters
            </button>
            <button
              onClick={fetchObservations}
              className="p-2 hover:bg-gray-800 rounded-lg transition-colors"
              title="Refresh"
            >
              <RefreshCw className={`w-5 h-5 ${loading ? "animate-spin" : ""}`} />
            </button>
            <button className="flex items-center gap-2 px-4 py-2 bg-green-600 hover:bg-green-700 rounded-lg text-sm font-medium">
              <Plus className="w-4 h-4" />
              Add Observation
            </button>
          </div>
        </div>

        {/* Filters Panel */}
        {showFilters && (
          <div className="border-t border-gray-700/50 px-4 sm:px-6 py-4 bg-gray-800/50">
            <div className="flex flex-wrap gap-4">
              <div>
                <label className="block text-xs text-gray-400 mb-1">Species</label>
                <input
                  type="text"
                  value={filters.species}
                  onChange={(e) => setFilters({ ...filters, species: e.target.value })}
                  placeholder="Search species..."
                  className="px-3 py-1.5 bg-gray-900 border border-gray-700 rounded-lg text-sm w-48"
                />
              </div>
              <div>
                <label className="block text-xs text-gray-400 mb-1">Date Range</label>
                <select
                  value={filters.dateRange}
                  onChange={(e) => setFilters({ ...filters, dateRange: e.target.value as MapFilters["dateRange"] })}
                  className="px-3 py-1.5 bg-gray-900 border border-gray-700 rounded-lg text-sm"
                >
                  <option value="week">Past Week</option>
                  <option value="month">Past Month</option>
                  <option value="year">Past Year</option>
                  <option value="all">All Time</option>
                </select>
              </div>
              <div>
                <label className="block text-xs text-gray-400 mb-1">Quality</label>
                <select
                  value={filters.qualityGrade}
                  onChange={(e) => setFilters({ ...filters, qualityGrade: e.target.value as MapFilters["qualityGrade"] })}
                  className="px-3 py-1.5 bg-gray-900 border border-gray-700 rounded-lg text-sm"
                >
                  <option value="all">All</option>
                  <option value="research">Research Grade</option>
                  <option value="needs_id">Needs ID</option>
                </select>
              </div>
            </div>
          </div>
        )}
      </header>

      <main className="flex h-[calc(100vh-65px)]">
        {/* Map Container */}
        <div className="flex-1 relative">
          {/* Placeholder Map - In production, use Leaflet, Mapbox, or Google Maps */}
          <div className="absolute inset-0 bg-gradient-to-br from-blue-900/30 to-gray-900">
            {/* Static map background image */}
            <div 
              className="absolute inset-0 opacity-60"
              style={{
                backgroundImage: "url('https://api.mapbox.com/styles/v1/mapbox/dark-v11/static/-98.5795,39.8283,3,0/1200x800?access_token=placeholder')",
                backgroundSize: "cover",
                backgroundPosition: "center",
              }}
            />
            
            {/* Map Grid Overlay */}
            <div className="absolute inset-0" style={{
              backgroundImage: `
                linear-gradient(rgba(100, 255, 218, 0.03) 1px, transparent 1px),
                linear-gradient(90deg, rgba(100, 255, 218, 0.03) 1px, transparent 1px)
              `,
              backgroundSize: "50px 50px",
            }} />

            {/* Observation Markers */}
            {observations.map((obs, index) => {
              // Simple projection for demo (not accurate, just for visualization)
              const x = ((obs.longitude + 130) / 60) * 100;
              const y = ((50 - obs.latitude) / 30) * 100;
              
              return (
                <button
                  key={obs.id}
                  onClick={() => setSelectedObservation(obs)}
                  className={`absolute transform -translate-x-1/2 -translate-y-1/2 transition-all ${
                    selectedObservation?.id === obs.id ? "scale-150 z-10" : "hover:scale-125"
                  }`}
                  style={{ left: `${x}%`, top: `${y}%` }}
                >
                  <div className={`w-4 h-4 rounded-full border-2 border-white shadow-lg ${
                    obs.quality_grade === "research" ? "bg-green-500" : "bg-yellow-500"
                  }`}>
                    <div className="absolute inset-0 rounded-full animate-ping opacity-50 bg-current" />
                  </div>
                </button>
              );
            })}

            {/* Map Controls */}
            <div className="absolute top-4 right-4 flex flex-col gap-2">
              <button className="p-2 bg-gray-800/90 hover:bg-gray-700 rounded-lg">
                <Layers className="w-5 h-5" />
              </button>
            </div>

            {/* Legend */}
            <div className="absolute bottom-4 left-4 p-3 bg-gray-800/90 rounded-lg text-xs">
              <div className="flex items-center gap-2 mb-2">
                <div className="w-3 h-3 rounded-full bg-green-500" />
                <span>Research Grade</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full bg-yellow-500" />
                <span>Needs ID</span>
              </div>
            </div>
          </div>
        </div>

        {/* Sidebar - Observation Details */}
        <div className="w-80 border-l border-gray-700/50 bg-gray-800/50 overflow-auto">
          {selectedObservation ? (
            <div className="p-4">
              <div className="flex items-center justify-between mb-4">
                <h2 className="font-semibold">Observation Details</h2>
                <button
                  onClick={() => setSelectedObservation(null)}
                  className="text-gray-400 hover:text-white"
                >
                  ×
                </button>
              </div>

              {/* Species Photo Placeholder */}
              <div className="aspect-video rounded-lg bg-gray-700/50 mb-4 flex items-center justify-center">
                <MapPin className="w-12 h-12 text-gray-600" />
              </div>

              <div className="space-y-4">
                <div>
                  <div className="text-lg font-bold text-green-400">
                    {selectedObservation.scientific_name}
                  </div>
                  <div className="text-sm text-gray-400">
                    {selectedObservation.common_name}
                  </div>
                </div>

                <div className="space-y-2 text-sm">
                  <div className="flex items-center gap-2">
                    <Calendar className="w-4 h-4 text-gray-500" />
                    <span>{new Date(selectedObservation.observed_on).toLocaleDateString()}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Eye className="w-4 h-4 text-gray-500" />
                    <span>@{selectedObservation.observer}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <MapPin className="w-4 h-4 text-gray-500" />
                    <span>
                      {selectedObservation.latitude.toFixed(4)}, {selectedObservation.longitude.toFixed(4)}
                    </span>
                  </div>
                </div>

                <div className={`px-3 py-1 rounded-full text-xs inline-block ${
                  selectedObservation.quality_grade === "research"
                    ? "bg-green-500/20 text-green-400"
                    : "bg-yellow-500/20 text-yellow-400"
                }`}>
                  {selectedObservation.quality_grade === "research" ? "Research Grade" : "Needs ID"}
                </div>

                <div className="pt-4 space-y-2">
                  <button className="w-full py-2 px-4 bg-green-600 hover:bg-green-700 rounded-lg text-sm font-medium">
                    View Full Details
                  </button>
                  <button className="w-full py-2 px-4 bg-gray-700 hover:bg-gray-600 rounded-lg text-sm font-medium">
                    Similar Species Nearby
                  </button>
                </div>
              </div>
            </div>
          ) : (
            <div className="p-4">
              <h2 className="font-semibold mb-4">Recent Observations</h2>
              <div className="space-y-3">
                {observations.slice(0, 10).map((obs) => (
                  <button
                    key={obs.id}
                    onClick={() => setSelectedObservation(obs)}
                    className="w-full p-3 rounded-lg bg-gray-900/50 hover:bg-gray-700/50 text-left transition-colors"
                  >
                    <div className="font-medium text-sm">{obs.common_name}</div>
                    <div className="text-xs text-gray-500 italic">{obs.scientific_name}</div>
                    <div className="flex items-center gap-2 mt-1 text-xs text-gray-400">
                      <Calendar className="w-3 h-3" />
                      {new Date(obs.observed_on).toLocaleDateString()}
                    </div>
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
