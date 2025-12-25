"use client"

import Link from "next/link"
import { Bot, Leaf, Search, Activity, Database, Cpu, Globe, ArrowRight } from "lucide-react"

const features = [
  {
    name: "MYCA Orchestrator",
    description: "42+ AI agents working 24/7 to manage research, data, and operations",
    href: "/myca",
    icon: Bot,
    color: "from-purple-600 to-purple-400",
    stats: "7 Active Agents",
  },
  {
    name: "NatureOS",
    description: "Earth system dashboard with weather, geospatial, and environmental data",
    href: "/natureos",
    icon: Leaf,
    color: "from-green-600 to-green-400",
    stats: "Live Earth Data",
  },
  {
    name: "MINDEX Search",
    description: "Search species, genetics, taxonomy, and scientific knowledge",
    href: "/mindex",
    icon: Search,
    color: "from-blue-600 to-blue-400",
    stats: "1M+ Species",
  },
  {
    name: "N8n Workflows",
    description: "Automated workflows connecting voice, data, and AI systems",
    href: "/n8n",
    icon: Activity,
    color: "from-orange-600 to-orange-400",
    stats: "23 Active Workflows",
  },
]

const stats = [
  { label: "AI Agents", value: "42+" },
  { label: "Workflows", value: "23" },
  { label: "Data Sources", value: "50+" },
  { label: "Species Records", value: "1M+" },
]

export default function HomePage() {
  return (
    <div className="min-h-screen bg-gradient-to-b from-[#0a0a0f] via-[#0a1929] to-[#0a0a0f]">
      {/* Hero */}
      <section className="relative px-4 py-20 md:py-32 overflow-hidden">
        {/* Background effects */}
        <div className="absolute inset-0 overflow-hidden">
          <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-purple-600/20 rounded-full blur-3xl" />
          <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-green-600/20 rounded-full blur-3xl" />
        </div>

        <div className="relative max-w-6xl mx-auto text-center">
          <div className="inline-flex items-center gap-2 rounded-full bg-purple-600/20 border border-purple-500/30 px-4 py-2 text-sm text-purple-300 mb-8">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-green-500"></span>
            </span>
            System Online — 7 Agents Active
          </div>

          <h1 className="text-5xl md:text-7xl font-bold mb-6">
            <span className="bg-gradient-to-r from-purple-400 via-green-400 to-blue-400 bg-clip-text text-transparent">
              Mycosoft MAS
            </span>
          </h1>
          <p className="text-xl md:text-2xl text-gray-400 max-w-3xl mx-auto mb-10">
            Multi-Agent System for mycology research, earth science, and autonomous operations.
            Powered by MYCA — your cognitive AI orchestrator.
          </p>

          <div className="flex flex-wrap justify-center gap-4">
            <Link
              href="/myca"
              className="group flex items-center gap-2 rounded-xl bg-purple-600 px-6 py-3 text-lg font-medium hover:bg-purple-700 transition-all hover:scale-105"
            >
              <Bot className="h-5 w-5" />
              Open MYCA Dashboard
              <ArrowRight className="h-4 w-4 group-hover:translate-x-1 transition-transform" />
            </Link>
            <Link
              href="/mindex"
              className="flex items-center gap-2 rounded-xl bg-gray-800 border border-gray-700 px-6 py-3 text-lg font-medium hover:bg-gray-700 transition"
            >
              <Search className="h-5 w-5" />
              Search Knowledge
            </Link>
          </div>
        </div>
      </section>

      {/* Stats */}
      <section className="px-4 py-12 border-y border-gray-800 bg-gray-900/50">
        <div className="max-w-6xl mx-auto grid grid-cols-2 md:grid-cols-4 gap-8">
          {stats.map((stat) => (
            <div key={stat.label} className="text-center">
              <div className="text-3xl md:text-4xl font-bold text-white">{stat.value}</div>
              <div className="text-sm text-gray-400 mt-1">{stat.label}</div>
            </div>
          ))}
        </div>
      </section>

      {/* Features */}
      <section className="px-4 py-20">
        <div className="max-w-6xl mx-auto">
          <h2 className="text-3xl font-bold text-white text-center mb-4">Platform Features</h2>
          <p className="text-gray-400 text-center mb-12 max-w-2xl mx-auto">
            Integrated AI agents, earth science data, and knowledge systems working together
          </p>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {features.map((feature) => (
              <Link
                key={feature.name}
                href={feature.href}
                className="group relative rounded-2xl bg-gray-900/50 border border-gray-800 p-8 hover:border-gray-700 transition-all hover:scale-[1.02]"
              >
                <div className={`inline-flex rounded-xl bg-gradient-to-r ${feature.color} p-3 mb-4`}>
                  <feature.icon className="h-6 w-6 text-white" />
                </div>
                <h3 className="text-xl font-semibold text-white mb-2">{feature.name}</h3>
                <p className="text-gray-400 mb-4">{feature.description}</p>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-500">{feature.stats}</span>
                  <ArrowRight className="h-5 w-5 text-gray-600 group-hover:text-white group-hover:translate-x-1 transition-all" />
                </div>
              </Link>
            ))}
          </div>
        </div>
      </section>

      {/* System Architecture */}
      <section className="px-4 py-20 bg-gray-900/30">
        <div className="max-w-6xl mx-auto">
          <h2 className="text-3xl font-bold text-white text-center mb-12">System Architecture</h2>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="rounded-xl bg-gradient-to-br from-purple-900/30 to-transparent border border-purple-500/20 p-6">
              <Cpu className="h-8 w-8 text-purple-400 mb-4" />
              <h3 className="text-lg font-semibold text-white mb-2">Agent Orchestration</h3>
              <p className="text-gray-400 text-sm">
                42+ specialized agents managed by MYCA orchestrator. Categories include research, financial, mycology, data, infrastructure, and more.
              </p>
            </div>
            <div className="rounded-xl bg-gradient-to-br from-green-900/30 to-transparent border border-green-500/20 p-6">
              <Database className="h-8 w-8 text-green-400 mb-4" />
              <h3 className="text-lg font-semibold text-white mb-2">Knowledge Systems</h3>
              <p className="text-gray-400 text-sm">
                PostgreSQL, Redis, and Qdrant vector DB for long-term memory, short-term caching, and semantic search across knowledge graphs.
              </p>
            </div>
            <div className="rounded-xl bg-gradient-to-br from-blue-900/30 to-transparent border border-blue-500/20 p-6">
              <Globe className="h-8 w-8 text-blue-400 mb-4" />
              <h3 className="text-lg font-semibold text-white mb-2">Data Integration</h3>
              <p className="text-gray-400 text-sm">
                Real-time data from space, weather, environmental sensors, MycoBrain devices, and laboratory systems flowing into NatureOS Earth simulator.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="px-4 py-8 border-t border-gray-800">
        <div className="max-w-6xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <span className="text-xl">🍄</span>
            <span className="text-gray-400">Mycosoft Labs © 2024</span>
          </div>
          <div className="flex gap-6 text-sm text-gray-500">
            <Link href="/docs" className="hover:text-white transition">Documentation</Link>
            <Link href="/apps" className="hover:text-white transition">Applications</Link>
            <a href="https://github.com/MycosoftLabs" className="hover:text-white transition">GitHub</a>
          </div>
        </div>
      </footer>
    </div>
  )
}
