"use client";

/**
 * Earth Simulator Page
 * Interactive visualization of Earth's systems
 */

import React, { Suspense } from "react";
import dynamic from "next/dynamic";

// Dynamic import for Three.js component (no SSR)
const EarthSimulator = dynamic(
  () => import("@/components/earth-simulator").then(mod => mod.EarthSimulator),
  { 
    ssr: false,
    loading: () => (
      <div className="w-full h-[600px] bg-slate-900 rounded-lg flex items-center justify-center">
        <div className="text-slate-400 animate-pulse">Loading 3D Earth...</div>
      </div>
    )
  }
);

export default function EarthSimulatorPage() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950">
      {/* Header */}
      <header className="border-b border-slate-800 bg-slate-900/50 backdrop-blur-sm">
        <div className="container mx-auto px-4 py-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-white tracking-tight">
                NatureOS Earth Simulator
              </h1>
              <p className="text-slate-400 mt-1">
                Real-time visualization of geological, meteorological, and biological systems
              </p>
            </div>
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2 text-sm text-slate-400">
                <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></div>
                Live Data
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto px-4 py-8">
        {/* Earth Globe */}
        <section className="mb-8">
          <EarthSimulator
            apiUrl={process.env.NEXT_PUBLIC_API_URL || "/api/natureos"}
            showWeather={true}
            showGeo={true}
            showBio={true}
          />
        </section>

        {/* Data Panels */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Weather Panel */}
          <div className="bg-slate-900/50 border border-slate-800 rounded-lg p-6">
            <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
              <svg className="w-5 h-5 text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 15a4 4 0 004 4h9a5 5 0 10-.1-9.999 5.002 5.002 0 10-9.78 2.096A4.001 4.001 0 003 15z" />
              </svg>
              Weather Systems
            </h3>
            <div className="space-y-3 text-sm">
              <div className="flex justify-between">
                <span className="text-slate-400">Active Storms</span>
                <span className="text-white font-medium">3</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Hurricanes</span>
                <span className="text-white font-medium">1</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Global Avg Temp</span>
                <span className="text-white font-medium">14.2°C</span>
              </div>
            </div>
          </div>

          {/* Geological Panel */}
          <div className="bg-slate-900/50 border border-slate-800 rounded-lg p-6">
            <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
              <svg className="w-5 h-5 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
              Geological Activity
            </h3>
            <div className="space-y-3 text-sm">
              <div className="flex justify-between">
                <span className="text-slate-400">Earthquakes (24h)</span>
                <span className="text-white font-medium">127</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Active Volcanoes</span>
                <span className="text-white font-medium">45</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Largest Quake</span>
                <span className="text-white font-medium">5.2 Mag</span>
              </div>
            </div>
          </div>

          {/* Biological Panel */}
          <div className="bg-slate-900/50 border border-slate-800 rounded-lg p-6">
            <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
              <svg className="w-5 h-5 text-green-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
              </svg>
              Mycological Watch
            </h3>
            <div className="space-y-3 text-sm">
              <div className="flex justify-between">
                <span className="text-slate-400">Species Tracked</span>
                <span className="text-white font-medium">14,892</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">New Sightings</span>
                <span className="text-white font-medium">23</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Conservation Alerts</span>
                <span className="text-orange-400 font-medium">5</span>
              </div>
            </div>
          </div>
        </div>

        {/* Info Section */}
        <section className="mt-12 text-center">
          <h2 className="text-xl font-semibold text-white mb-4">
            Powered by NatureOS
          </h2>
          <p className="text-slate-400 max-w-2xl mx-auto">
            The Earth Simulator integrates real-time data from seismological networks, 
            weather stations, and biological observation systems worldwide to provide 
            a comprehensive view of our planet's dynamic systems.
          </p>
          <div className="mt-6 flex justify-center gap-4">
            <a href="/encyclopedia" className="text-blue-400 hover:text-blue-300 text-sm">
              Explore Encyclopedia →
            </a>
            <a href="/search" className="text-blue-400 hover:text-blue-300 text-sm">
              Search Species →
            </a>
          </div>
        </section>
      </main>
    </div>
  );
}
