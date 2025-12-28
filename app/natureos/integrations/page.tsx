"use client";

import { useState } from "react";
import Link from "next/link";
import {
  Plug,
  ArrowLeft,
  CheckCircle,
  XCircle,
  Settings,
  ExternalLink,
  Plus,
  Trash2,
} from "lucide-react";

interface Integration {
  id: string;
  name: string;
  description: string;
  category: string;
  icon: string;
  status: "connected" | "disconnected" | "error";
  url?: string;
  configurable: boolean;
}

const integrations: Integration[] = [
  // Workflow Automation
  {
    id: "n8n-local",
    name: "n8n (Local)",
    description: "Local workflow automation instance",
    category: "Workflow",
    icon: "🔄",
    status: "connected",
    url: "http://localhost:5678",
    configurable: true,
  },
  {
    id: "n8n-cloud",
    name: "n8n Cloud",
    description: "Cloud workflow automation (mycosoft.app.n8n.cloud)",
    category: "Workflow",
    icon: "☁️",
    status: "disconnected",
    url: "https://mycosoft.app.n8n.cloud",
    configurable: true,
  },
  {
    id: "zapier",
    name: "Zapier",
    description: "Third-party automation platform",
    category: "Workflow",
    icon: "⚡",
    status: "disconnected",
    url: "https://zapier.com",
    configurable: true,
  },
  {
    id: "ifttt",
    name: "IFTTT",
    description: "If This Then That automations",
    category: "Workflow",
    icon: "🔗",
    status: "disconnected",
    url: "https://ifttt.com",
    configurable: true,
  },

  // AI & Voice
  {
    id: "elevenlabs",
    name: "ElevenLabs",
    description: "Text-to-speech and voice synthesis",
    category: "AI & Voice",
    icon: "🎙️",
    status: "connected",
    url: "https://elevenlabs.io",
    configurable: true,
  },
  {
    id: "openai",
    name: "OpenAI",
    description: "GPT-4 and other AI models",
    category: "AI & Voice",
    icon: "🤖",
    status: "connected",
    url: "https://openai.com",
    configurable: true,
  },
  {
    id: "anthropic",
    name: "Anthropic Claude",
    description: "Claude AI assistant",
    category: "AI & Voice",
    icon: "🧠",
    status: "disconnected",
    configurable: true,
  },

  // Cloud Services
  {
    id: "google",
    name: "Google Cloud",
    description: "Google Cloud Platform services",
    category: "Cloud",
    icon: "🌐",
    status: "disconnected",
    url: "https://cloud.google.com",
    configurable: true,
  },
  {
    id: "azure",
    name: "Microsoft Azure",
    description: "Azure cloud services",
    category: "Cloud",
    icon: "☁️",
    status: "connected",
    url: "https://azure.microsoft.com",
    configurable: true,
  },

  // Network
  {
    id: "unifi",
    name: "UniFi",
    description: "Ubiquiti UniFi network controller",
    category: "Network",
    icon: "📡",
    status: "connected",
    url: "https://unifi.ui.com",
    configurable: true,
  },

  // Data & Storage
  {
    id: "mcp-filesystem",
    name: "MCP Filesystem",
    description: "Local filesystem MCP server",
    category: "MCP Servers",
    icon: "📁",
    status: "connected",
    configurable: false,
  },
  {
    id: "mcp-browser",
    name: "MCP Browser",
    description: "Browser automation MCP server",
    category: "MCP Servers",
    icon: "🌐",
    status: "connected",
    configurable: false,
  },
  {
    id: "mcp-memory",
    name: "MCP Memory",
    description: "Knowledge graph MCP server",
    category: "MCP Servers",
    icon: "🧠",
    status: "connected",
    configurable: false,
  },
];

export default function IntegrationsPage() {
  const [filter, setFilter] = useState<string>("all");
  const [selectedIntegration, setSelectedIntegration] = useState<Integration | null>(null);

  const categories = ["all", ...new Set(integrations.map((i) => i.category))];
  const filteredIntegrations = filter === "all" 
    ? integrations 
    : integrations.filter((i) => i.category === filter);

  const connectedCount = integrations.filter((i) => i.status === "connected").length;

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "connected":
        return <CheckCircle className="w-5 h-5 text-green-500" />;
      case "error":
        return <XCircle className="w-5 h-5 text-red-500" />;
      default:
        return <XCircle className="w-5 h-5 text-gray-500" />;
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 text-white">
      {/* Header */}
      <header className="border-b border-gray-700/50 bg-gray-900/80 backdrop-blur-sm sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link href="/natureos" className="p-2 hover:bg-gray-800 rounded-lg transition-colors">
              <ArrowLeft className="w-5 h-5" />
            </Link>
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-yellow-500/20">
                <Plug className="w-6 h-6 text-yellow-400" />
              </div>
              <div>
                <h1 className="text-xl font-bold">Integrations</h1>
                <p className="text-xs text-gray-400">
                  {connectedCount} of {integrations.length} connected
                </p>
              </div>
            </div>
          </div>

          <button className="flex items-center gap-2 px-4 py-2 bg-yellow-600 hover:bg-yellow-700 rounded-lg text-sm font-medium">
            <Plus className="w-4 h-4" />
            Add Integration
          </button>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 py-6">
        {/* Filter Tabs */}
        <div className="flex flex-wrap gap-2 mb-6">
          {categories.map((category) => (
            <button
              key={category}
              onClick={() => setFilter(category)}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors capitalize ${
                filter === category
                  ? "bg-yellow-600 text-white"
                  : "bg-gray-800 text-gray-400 hover:text-white"
              }`}
            >
              {category}
            </button>
          ))}
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Integrations List */}
          <div className="lg:col-span-2">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {filteredIntegrations.map((integration) => (
                <div
                  key={integration.id}
                  onClick={() => setSelectedIntegration(integration)}
                  className={`p-4 rounded-xl bg-gray-800/50 border cursor-pointer transition-all hover:scale-[1.02] ${
                    selectedIntegration?.id === integration.id
                      ? "border-yellow-500"
                      : "border-gray-700/50 hover:border-gray-600"
                  }`}
                >
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex items-center gap-3">
                      <span className="text-2xl">{integration.icon}</span>
                      <div>
                        <div className="font-medium">{integration.name}</div>
                        <div className="text-xs text-gray-500">{integration.category}</div>
                      </div>
                    </div>
                    {getStatusIcon(integration.status)}
                  </div>
                  <p className="text-sm text-gray-400">{integration.description}</p>
                </div>
              ))}
            </div>
          </div>

          {/* Details Panel */}
          <div>
            {selectedIntegration ? (
              <div className="rounded-xl bg-gray-800/50 border border-gray-700/50 overflow-hidden sticky top-24">
                <div className="p-4 border-b border-gray-700/50">
                  <div className="flex items-center gap-3">
                    <span className="text-3xl">{selectedIntegration.icon}</span>
                    <div>
                      <h2 className="font-semibold">{selectedIntegration.name}</h2>
                      <span className={`text-xs ${
                        selectedIntegration.status === "connected"
                          ? "text-green-400"
                          : "text-gray-400"
                      }`}>
                        {selectedIntegration.status}
                      </span>
                    </div>
                  </div>
                </div>

                <div className="p-4 space-y-4">
                  <p className="text-sm text-gray-400">{selectedIntegration.description}</p>

                  <div className="space-y-2">
                    <div className="flex justify-between text-sm">
                      <span className="text-gray-400">Category</span>
                      <span>{selectedIntegration.category}</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span className="text-gray-400">Status</span>
                      <span className={
                        selectedIntegration.status === "connected"
                          ? "text-green-400"
                          : "text-gray-400"
                      }>
                        {selectedIntegration.status}
                      </span>
                    </div>
                    {selectedIntegration.url && (
                      <div className="flex justify-between text-sm">
                        <span className="text-gray-400">URL</span>
                        <a
                          href={selectedIntegration.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-blue-400 hover:underline flex items-center gap-1"
                        >
                          Open <ExternalLink className="w-3 h-3" />
                        </a>
                      </div>
                    )}
                  </div>

                  <div className="pt-4 space-y-2">
                    {selectedIntegration.configurable && (
                      <button className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg text-sm font-medium transition-colors">
                        <Settings className="w-4 h-4" />
                        Configure
                      </button>
                    )}
                    {selectedIntegration.status === "connected" ? (
                      <button className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-red-600/20 hover:bg-red-600/30 text-red-400 rounded-lg text-sm font-medium transition-colors">
                        <Trash2 className="w-4 h-4" />
                        Disconnect
                      </button>
                    ) : (
                      <button className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-green-600 hover:bg-green-700 rounded-lg text-sm font-medium transition-colors">
                        <Plug className="w-4 h-4" />
                        Connect
                      </button>
                    )}
                  </div>
                </div>
              </div>
            ) : (
              <div className="rounded-xl bg-gray-800/50 border border-gray-700/50 p-8 text-center">
                <Plug className="w-12 h-12 mx-auto mb-4 text-gray-600" />
                <p className="text-gray-400">Select an integration to view details</p>
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
