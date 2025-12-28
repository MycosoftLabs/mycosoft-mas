"use client";

import { useState } from "react";
import Link from "next/link";
import { Network, ArrowLeft, Play, ChevronDown, ChevronRight, Copy, Check } from "lucide-react";

interface APIEndpoint {
  path: string;
  method: "GET" | "POST" | "PUT" | "DELETE";
  description: string;
  category: string;
  exampleRequest?: Record<string, unknown>;
}

const API_ENDPOINTS: APIEndpoint[] = [
  // System
  { path: "/api/system", method: "GET", description: "Get system statistics (CPU, memory, disk, Docker)", category: "System" },
  { path: "/api/network", method: "GET", description: "Get network devices and health", category: "System" },
  
  // Agents
  { path: "/api/agents", method: "GET", description: "List all agents", category: "Agents" },
  { path: "/api/agents", method: "POST", description: "Send command to agent", category: "Agents", exampleRequest: { agentId: "myca", message: "status" } },
  { path: "/api/agents/create", method: "POST", description: "Create new agent", category: "Agents", exampleRequest: { agent_id: "my_agent", name: "MyAgent", description: "A custom agent" } },
  
  // Search
  { path: "/api/search", method: "GET", description: "Search across all entities", category: "Search" },
  
  // n8n
  { path: "/api/n8n", method: "GET", description: "Get n8n status and workflows", category: "n8n" },
  { path: "/api/n8n", method: "POST", description: "Trigger workflow execution", category: "n8n", exampleRequest: { workflowId: "abc123", instance: "local" } },
  
  // MYCA
  { path: "/api/myca/chat", method: "POST", description: "Chat with MYCA", category: "MYCA", exampleRequest: { message: "Hello MYCA" } },
  { path: "/api/myca/tts", method: "POST", description: "Text-to-speech synthesis", category: "MYCA", exampleRequest: { text: "Hello world", voice: "myca" } },
  { path: "/api/myca/tts", method: "GET", description: "TTS health check", category: "MYCA" },
  
  // MAS
  { path: "/api/mas/topology", method: "GET", description: "Get agent topology", category: "MAS" },
  { path: "/api/mas/defense", method: "GET", description: "Get defense system status", category: "MAS" },
  { path: "/api/mas/environmental", method: "GET", description: "Get environmental data", category: "MAS" },
  { path: "/api/mas/space-weather", method: "GET", description: "Get space weather data", category: "MAS" },
  { path: "/api/mas/financial", method: "GET", description: "Get financial data", category: "MAS" },
];

export default function APIPage() {
  const [selectedEndpoint, setSelectedEndpoint] = useState<APIEndpoint | null>(null);
  const [response, setResponse] = useState<string>("");
  const [loading, setLoading] = useState(false);
  const [expandedCategories, setExpandedCategories] = useState<Set<string>>(new Set(["System", "Agents"]));
  const [copied, setCopied] = useState(false);
  const [customBody, setCustomBody] = useState("");

  const categories = [...new Set(API_ENDPOINTS.map((e) => e.category))];

  const toggleCategory = (category: string) => {
    const newExpanded = new Set(expandedCategories);
    if (newExpanded.has(category)) {
      newExpanded.delete(category);
    } else {
      newExpanded.add(category);
    }
    setExpandedCategories(newExpanded);
  };

  const executeRequest = async () => {
    if (!selectedEndpoint) return;

    setLoading(true);
    setResponse("");

    try {
      const options: RequestInit = {
        method: selectedEndpoint.method,
        headers: { "Content-Type": "application/json" },
      };

      if (selectedEndpoint.method !== "GET" && customBody) {
        options.body = customBody;
      }

      const res = await fetch(selectedEndpoint.path, options);
      const data = await res.json();
      setResponse(JSON.stringify(data, null, 2));
    } catch (error) {
      setResponse(`Error: ${error instanceof Error ? error.message : "Unknown error"}`);
    } finally {
      setLoading(false);
    }
  };

  const copyResponse = () => {
    navigator.clipboard.writeText(response);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const getMethodColor = (method: string) => {
    switch (method) {
      case "GET":
        return "bg-green-500/20 text-green-400";
      case "POST":
        return "bg-blue-500/20 text-blue-400";
      case "PUT":
        return "bg-yellow-500/20 text-yellow-400";
      case "DELETE":
        return "bg-red-500/20 text-red-400";
      default:
        return "bg-gray-500/20 text-gray-400";
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 text-white">
      {/* Header */}
      <header className="border-b border-gray-700/50 bg-gray-900/80 backdrop-blur-sm sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-4 flex items-center gap-4">
          <Link href="/natureos" className="p-2 hover:bg-gray-800 rounded-lg transition-colors">
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-blue-500/20">
              <Network className="w-6 h-6 text-blue-400" />
            </div>
            <div>
              <h1 className="text-xl font-bold">API Explorer</h1>
              <p className="text-xs text-gray-400">Browse and test all MYCOSOFT APIs</p>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 py-6">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Endpoints List */}
          <div className="lg:col-span-1">
            <div className="rounded-xl bg-gray-800/50 border border-gray-700/50 overflow-hidden">
              <div className="p-4 border-b border-gray-700/50">
                <h2 className="font-semibold">Endpoints</h2>
              </div>
              
              <div className="divide-y divide-gray-700/50">
                {categories.map((category) => (
                  <div key={category}>
                    <button
                      onClick={() => toggleCategory(category)}
                      className="w-full px-4 py-3 flex items-center justify-between hover:bg-gray-800/50 transition-colors"
                    >
                      <span className="font-medium">{category}</span>
                      {expandedCategories.has(category) ? (
                        <ChevronDown className="w-4 h-4" />
                      ) : (
                        <ChevronRight className="w-4 h-4" />
                      )}
                    </button>
                    
                    {expandedCategories.has(category) && (
                      <div className="bg-gray-900/50">
                        {API_ENDPOINTS.filter((e) => e.category === category).map((endpoint, idx) => (
                          <button
                            key={`${endpoint.path}-${endpoint.method}-${idx}`}
                            onClick={() => {
                              setSelectedEndpoint(endpoint);
                              setCustomBody(endpoint.exampleRequest ? JSON.stringify(endpoint.exampleRequest, null, 2) : "");
                              setResponse("");
                            }}
                            className={`w-full px-4 py-2 flex items-center gap-2 text-left hover:bg-gray-800/50 transition-colors ${
                              selectedEndpoint?.path === endpoint.path && selectedEndpoint?.method === endpoint.method
                                ? "bg-gray-800"
                                : ""
                            }`}
                          >
                            <span className={`px-2 py-0.5 rounded text-xs font-mono ${getMethodColor(endpoint.method)}`}>
                              {endpoint.method}
                            </span>
                            <span className="text-sm truncate flex-1">{endpoint.path}</span>
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Request/Response Panel */}
          <div className="lg:col-span-2 space-y-6">
            {selectedEndpoint ? (
              <>
                {/* Request */}
                <div className="rounded-xl bg-gray-800/50 border border-gray-700/50 overflow-hidden">
                  <div className="p-4 border-b border-gray-700/50 flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <span className={`px-2 py-1 rounded text-sm font-mono ${getMethodColor(selectedEndpoint.method)}`}>
                        {selectedEndpoint.method}
                      </span>
                      <span className="font-mono text-sm">{selectedEndpoint.path}</span>
                    </div>
                    <button
                      onClick={executeRequest}
                      disabled={loading}
                      className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 rounded-lg text-sm font-medium"
                    >
                      <Play className="w-4 h-4" />
                      {loading ? "Executing..." : "Execute"}
                    </button>
                  </div>
                  
                  <div className="p-4">
                    <p className="text-sm text-gray-400 mb-4">{selectedEndpoint.description}</p>
                    
                    {selectedEndpoint.method !== "GET" && (
                      <div>
                        <label className="block text-sm font-medium mb-2">Request Body</label>
                        <textarea
                          value={customBody}
                          onChange={(e) => setCustomBody(e.target.value)}
                          className="w-full h-32 p-3 bg-gray-900 border border-gray-700 rounded-lg font-mono text-sm resize-none"
                          placeholder="Enter JSON body..."
                        />
                      </div>
                    )}
                  </div>
                </div>

                {/* Response */}
                <div className="rounded-xl bg-gray-800/50 border border-gray-700/50 overflow-hidden">
                  <div className="p-4 border-b border-gray-700/50 flex items-center justify-between">
                    <h3 className="font-semibold">Response</h3>
                    {response && (
                      <button
                        onClick={copyResponse}
                        className="flex items-center gap-2 px-3 py-1 hover:bg-gray-700 rounded-lg text-sm transition-colors"
                      >
                        {copied ? <Check className="w-4 h-4 text-green-400" /> : <Copy className="w-4 h-4" />}
                        {copied ? "Copied!" : "Copy"}
                      </button>
                    )}
                  </div>
                  
                  <div className="p-4">
                    {loading ? (
                      <div className="text-center py-8 text-gray-500">Loading...</div>
                    ) : response ? (
                      <pre className="bg-gray-900 p-4 rounded-lg overflow-auto max-h-96 text-sm font-mono text-gray-300">
                        {response}
                      </pre>
                    ) : (
                      <div className="text-center py-8 text-gray-500">
                        Click Execute to send the request
                      </div>
                    )}
                  </div>
                </div>
              </>
            ) : (
              <div className="rounded-xl bg-gray-800/50 border border-gray-700/50 p-8 text-center">
                <Network className="w-12 h-12 mx-auto mb-4 text-gray-600" />
                <p className="text-gray-400">Select an endpoint from the list to get started</p>
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
