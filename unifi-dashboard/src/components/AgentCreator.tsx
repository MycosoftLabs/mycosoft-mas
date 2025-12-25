"use client";

import { useState } from "react";
import { X, Wand2, Plus, Check, AlertCircle, Loader2 } from "lucide-react";

interface AgentCreatorProps {
  isOpen: boolean;
  onClose: () => void;
  onAgentCreated?: (agent: NewAgent) => void;
}

interface NewAgent {
  agent_id: string;
  name: string;
  display_name: string;
  description: string;
  category: string;
  capabilities: string[];
  keywords: string[];
  voice_triggers: string[];
  requires_confirmation: boolean;
}

const CATEGORIES = [
  "core", "financial", "mycology", "research", "data", 
  "infrastructure", "simulation", "communication", "security", "dao", "integration"
];

const CAPABILITIES = ["read", "write", "execute", "analyze", "notify", "manage", "control"];

export function AgentCreator({ isOpen, onClose, onAgentCreated }: AgentCreatorProps) {
  const [mode, setMode] = useState<"manual" | "ai">("ai");
  const [prompt, setPrompt] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  
  // Manual form state
  const [agent, setAgent] = useState<NewAgent>({
    agent_id: "",
    name: "",
    display_name: "",
    description: "",
    category: "core",
    capabilities: ["read"],
    keywords: [],
    voice_triggers: [],
    requires_confirmation: false,
  });
  
  const [keywordInput, setKeywordInput] = useState("");
  const [triggerInput, setTriggerInput] = useState("");

  const handleAIGenerate = async () => {
    if (!prompt.trim()) return;
    
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch("/api/myca/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: `Create a new agent based on this request: "${prompt}". 
          Respond with a JSON object containing: agent_id (snake_case), name (PascalCaseAgent), 
          display_name (human readable), description, category (one of: ${CATEGORIES.join(", ")}), 
          capabilities (array from: ${CAPABILITIES.join(", ")}), keywords (array), 
          voice_triggers (array of phrases), requires_confirmation (boolean).
          Only respond with valid JSON, no markdown.`,
          context: { intent: "agent_creation" }
        })
      });
      
      const data = await response.json();
      
      // Try to parse the response as JSON
      let agentConfig: NewAgent;
      try {
        const jsonMatch = data.response?.match(/\{[\s\S]*\}/);
        if (jsonMatch) {
          agentConfig = JSON.parse(jsonMatch[0]);
          setAgent(agentConfig);
          setMode("manual"); // Switch to manual to review
        } else {
          throw new Error("No JSON found in response");
        }
      } catch {
        // If AI doesn't return JSON, generate from prompt
        const words = prompt.toLowerCase().split(/\s+/);
        const agentId = words.slice(0, 3).join("_").replace(/[^a-z_]/g, "");
        agentConfig = {
          agent_id: agentId || "custom_agent",
          name: words.map(w => w.charAt(0).toUpperCase() + w.slice(1)).join("") + "Agent",
          display_name: prompt.split(" ").slice(0, 4).join(" ") + " Agent",
          description: prompt,
          category: "core",
          capabilities: ["read", "analyze"],
          keywords: words.filter(w => w.length > 3),
          voice_triggers: [prompt.toLowerCase()],
          requires_confirmation: false,
        };
        setAgent(agentConfig);
        setMode("manual");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to generate agent");
    } finally {
      setLoading(false);
    }
  };

  const handleCreateAgent = async () => {
    if (!agent.agent_id || !agent.name || !agent.description) {
      setError("Please fill in required fields: ID, Name, and Description");
      return;
    }
    
    setLoading(true);
    setError(null);
    
    try {
      // Create agent in the registry
      const response = await fetch("http://localhost:8001/agents/registry/create", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(agent)
      });
      
      if (!response.ok) {
        // Fallback - add to local registry file
        const localResponse = await fetch("/api/agents/create", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(agent)
        });
        
        if (!localResponse.ok) {
          throw new Error("Failed to create agent");
        }
      }
      
      setSuccess(true);
      onAgentCreated?.(agent);
      
      // Reset after success
      setTimeout(() => {
        setSuccess(false);
        setAgent({
          agent_id: "",
          name: "",
          display_name: "",
          description: "",
          category: "core",
          capabilities: ["read"],
          keywords: [],
          voice_triggers: [],
          requires_confirmation: false,
        });
        setPrompt("");
        onClose();
      }, 2000);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create agent");
    } finally {
      setLoading(false);
    }
  };

  const addKeyword = () => {
    if (keywordInput.trim() && !agent.keywords.includes(keywordInput.trim())) {
      setAgent({ ...agent, keywords: [...agent.keywords, keywordInput.trim()] });
      setKeywordInput("");
    }
  };

  const addTrigger = () => {
    if (triggerInput.trim() && !agent.voice_triggers.includes(triggerInput.trim())) {
      setAgent({ ...agent, voice_triggers: [...agent.voice_triggers, triggerInput.trim()] });
      setTriggerInput("");
    }
  };

  const toggleCapability = (cap: string) => {
    if (agent.capabilities.includes(cap)) {
      setAgent({ ...agent, capabilities: agent.capabilities.filter(c => c !== cap) });
    } else {
      setAgent({ ...agent, capabilities: [...agent.capabilities, cap] });
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-4" onClick={onClose}>
      <div 
        className="relative w-full max-w-2xl max-h-[90vh] overflow-y-auto rounded-lg bg-[#1E293B] shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="sticky top-0 z-10 flex items-center justify-between border-b border-gray-700 bg-[#1E293B] p-4">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-purple-600">
              <Wand2 className="h-5 w-5 text-white" />
            </div>
            <div>
              <h2 className="text-xl font-semibold text-white">Create New Agent</h2>
              <p className="text-sm text-gray-400">Build an AI agent for MYCA</p>
            </div>
          </div>
          <button onClick={onClose} className="rounded-lg p-2 hover:bg-gray-700">
            <X className="h-5 w-5 text-gray-400" />
          </button>
        </div>

        <div className="p-6 space-y-6">
          {/* Mode Toggle */}
          <div className="flex gap-2">
            <button
              onClick={() => setMode("ai")}
              className={`flex-1 rounded-lg px-4 py-3 text-sm font-medium transition ${
                mode === "ai" 
                  ? "bg-purple-600 text-white" 
                  : "bg-gray-700 text-gray-300 hover:bg-gray-600"
              }`}
            >
              <Wand2 className="inline h-4 w-4 mr-2" />
              AI Generate
            </button>
            <button
              onClick={() => setMode("manual")}
              className={`flex-1 rounded-lg px-4 py-3 text-sm font-medium transition ${
                mode === "manual" 
                  ? "bg-purple-600 text-white" 
                  : "bg-gray-700 text-gray-300 hover:bg-gray-600"
              }`}
            >
              <Plus className="inline h-4 w-4 mr-2" />
              Manual Create
            </button>
          </div>

          {/* AI Mode */}
          {mode === "ai" && (
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Describe the agent you want to create
                </label>
                <textarea
                  value={prompt}
                  onChange={(e) => setPrompt(e.target.value)}
                  placeholder="e.g., An agent that monitors mushroom growth conditions and sends alerts when humidity drops below optimal levels"
                  className="w-full rounded-lg bg-gray-800 border border-gray-600 px-4 py-3 text-white placeholder-gray-500 focus:border-purple-500 focus:outline-none min-h-[120px]"
                />
              </div>
              <button
                onClick={handleAIGenerate}
                disabled={loading || !prompt.trim()}
                className="w-full rounded-lg bg-purple-600 px-4 py-3 text-white font-medium hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
              >
                {loading ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Generating...
                  </>
                ) : (
                  <>
                    <Wand2 className="h-4 w-4" />
                    Generate Agent
                  </>
                )}
              </button>
            </div>
          )}

          {/* Manual Mode */}
          {mode === "manual" && (
            <div className="space-y-4">
              {/* Basic Info */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">Agent ID *</label>
                  <input
                    type="text"
                    value={agent.agent_id}
                    onChange={(e) => setAgent({ ...agent, agent_id: e.target.value.toLowerCase().replace(/\s/g, "_") })}
                    placeholder="my_custom_agent"
                    className="w-full rounded-lg bg-gray-800 border border-gray-600 px-3 py-2 text-white placeholder-gray-500 focus:border-purple-500 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">Name *</label>
                  <input
                    type="text"
                    value={agent.name}
                    onChange={(e) => setAgent({ ...agent, name: e.target.value })}
                    placeholder="MyCustomAgent"
                    className="w-full rounded-lg bg-gray-800 border border-gray-600 px-3 py-2 text-white placeholder-gray-500 focus:border-purple-500 focus:outline-none"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">Display Name</label>
                <input
                  type="text"
                  value={agent.display_name}
                  onChange={(e) => setAgent({ ...agent, display_name: e.target.value })}
                  placeholder="My Custom Agent"
                  className="w-full rounded-lg bg-gray-800 border border-gray-600 px-3 py-2 text-white placeholder-gray-500 focus:border-purple-500 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">Description *</label>
                <textarea
                  value={agent.description}
                  onChange={(e) => setAgent({ ...agent, description: e.target.value })}
                  placeholder="Describe what this agent does..."
                  className="w-full rounded-lg bg-gray-800 border border-gray-600 px-3 py-2 text-white placeholder-gray-500 focus:border-purple-500 focus:outline-none min-h-[80px]"
                />
              </div>

              {/* Category */}
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">Category</label>
                <select
                  value={agent.category}
                  onChange={(e) => setAgent({ ...agent, category: e.target.value })}
                  className="w-full rounded-lg bg-gray-800 border border-gray-600 px-3 py-2 text-white focus:border-purple-500 focus:outline-none"
                >
                  {CATEGORIES.map(cat => (
                    <option key={cat} value={cat}>{cat.charAt(0).toUpperCase() + cat.slice(1)}</option>
                  ))}
                </select>
              </div>

              {/* Capabilities */}
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">Capabilities</label>
                <div className="flex flex-wrap gap-2">
                  {CAPABILITIES.map(cap => (
                    <button
                      key={cap}
                      onClick={() => toggleCapability(cap)}
                      className={`rounded-full px-3 py-1 text-sm transition ${
                        agent.capabilities.includes(cap)
                          ? "bg-purple-600 text-white"
                          : "bg-gray-700 text-gray-300 hover:bg-gray-600"
                      }`}
                    >
                      {cap}
                    </button>
                  ))}
                </div>
              </div>

              {/* Keywords */}
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">Keywords</label>
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={keywordInput}
                    onChange={(e) => setKeywordInput(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && (e.preventDefault(), addKeyword())}
                    placeholder="Add keyword..."
                    className="flex-1 rounded-lg bg-gray-800 border border-gray-600 px-3 py-2 text-white placeholder-gray-500 focus:border-purple-500 focus:outline-none"
                  />
                  <button onClick={addKeyword} className="rounded-lg bg-gray-700 px-3 py-2 hover:bg-gray-600">
                    <Plus className="h-4 w-4 text-white" />
                  </button>
                </div>
                {agent.keywords.length > 0 && (
                  <div className="flex flex-wrap gap-1 mt-2">
                    {agent.keywords.map((kw, i) => (
                      <span key={i} className="rounded bg-gray-700 px-2 py-1 text-xs text-gray-300 flex items-center gap-1">
                        {kw}
                        <button onClick={() => setAgent({ ...agent, keywords: agent.keywords.filter((_, j) => j !== i) })}>
                          <X className="h-3 w-3" />
                        </button>
                      </span>
                    ))}
                  </div>
                )}
              </div>

              {/* Voice Triggers */}
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">Voice Triggers</label>
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={triggerInput}
                    onChange={(e) => setTriggerInput(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && (e.preventDefault(), addTrigger())}
                    placeholder="Add voice trigger phrase..."
                    className="flex-1 rounded-lg bg-gray-800 border border-gray-600 px-3 py-2 text-white placeholder-gray-500 focus:border-purple-500 focus:outline-none"
                  />
                  <button onClick={addTrigger} className="rounded-lg bg-gray-700 px-3 py-2 hover:bg-gray-600">
                    <Plus className="h-4 w-4 text-white" />
                  </button>
                </div>
                {agent.voice_triggers.length > 0 && (
                  <div className="flex flex-wrap gap-1 mt-2">
                    {agent.voice_triggers.map((tr, i) => (
                      <span key={i} className="rounded bg-purple-900/50 px-2 py-1 text-xs text-purple-300 flex items-center gap-1">
                        &quot;{tr}&quot;
                        <button onClick={() => setAgent({ ...agent, voice_triggers: agent.voice_triggers.filter((_, j) => j !== i) })}>
                          <X className="h-3 w-3" />
                        </button>
                      </span>
                    ))}
                  </div>
                )}
              </div>

              {/* Confirmation Toggle */}
              <div className="flex items-center gap-3">
                <button
                  onClick={() => setAgent({ ...agent, requires_confirmation: !agent.requires_confirmation })}
                  className={`relative w-12 h-6 rounded-full transition ${
                    agent.requires_confirmation ? "bg-purple-600" : "bg-gray-600"
                  }`}
                >
                  <div className={`absolute top-1 w-4 h-4 rounded-full bg-white transition ${
                    agent.requires_confirmation ? "left-7" : "left-1"
                  }`} />
                </button>
                <span className="text-sm text-gray-300">Require confirmation for actions</span>
              </div>
            </div>
          )}

          {/* Error/Success Messages */}
          {error && (
            <div className="flex items-center gap-2 rounded-lg bg-red-900/50 border border-red-500 px-4 py-3 text-red-300">
              <AlertCircle className="h-5 w-5" />
              {error}
            </div>
          )}

          {success && (
            <div className="flex items-center gap-2 rounded-lg bg-green-900/50 border border-green-500 px-4 py-3 text-green-300">
              <Check className="h-5 w-5" />
              Agent created successfully!
            </div>
          )}

          {/* Create Button */}
          {mode === "manual" && (
            <button
              onClick={handleCreateAgent}
              disabled={loading || !agent.agent_id || !agent.name || !agent.description}
              className="w-full rounded-lg bg-green-600 px-4 py-3 text-white font-medium hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              {loading ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Creating...
                </>
              ) : (
                <>
                  <Plus className="h-4 w-4" />
                  Create Agent
                </>
              )}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

