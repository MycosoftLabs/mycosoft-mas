"use client"

import * as React from "react"
import mermaid from "mermaid"

interface Node {
  id: string
  type: string
  label: string
}
interface Edge {
  source: string
  target: string
  type: string
}
interface SystemGraph {
  nodes: Node[]
  edges: Edge[]
}
interface AgentStatus {
  status: string
  last_heartbeat: string
  metrics: Record<string, any>
}

const NODE_TYPES = ["all", "agent", "service", "tool", "orchestrator"] as const

type NodeType = typeof NODE_TYPES[number]

export function SystemGraphPanel() {
  const [graph, setGraph] = React.useState<SystemGraph | null>(null)
  const [loading, setLoading] = React.useState(false)
  const [error, setError] = React.useState<string | null>(null)
  const [selectedNode, setSelectedNode] = React.useState<Node | null>(null)
  const [agentData, setAgentData] = React.useState<Record<string, AgentStatus>>({})
  const [filter, setFilter] = React.useState<NodeType>("all")
  const [hoveredNode, setHoveredNode] = React.useState<string | null>(null)
  const diagramRef = React.useRef<HTMLDivElement>(null)

  async function fetchGraph() {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch("/api/graph")
      if (!res.ok) throw new Error("Failed to fetch graph")
      const data = await res.json()
      setGraph(data)
    } catch (e: any) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  async function fetchAgentData() {
    try {
      const res = await fetch("/api/agents")
      if (!res.ok) return
      const data = await res.json()
      setAgentData(data.agents || {})
    } catch {}
  }

  React.useEffect(() => {
    fetchGraph()
    fetchAgentData()
  }, [])

  function renderMermaid(graph: SystemGraph) {
    let def = "graph TD\n"
    for (const node of graph.nodes) {
      if (filter !== "all" && node.type !== filter) continue
      def += `  ${node.id}[${node.label}]:::${node.type}`
      if (hoveredNode && node.id === hoveredNode) def += ":::highlight"
      def += "\n"
    }
    for (const edge of graph.edges) {
      if (filter !== "all") {
        const src = graph.nodes.find(n => n.id === edge.source)
        const tgt = graph.nodes.find(n => n.id === edge.target)
        if (!src || !tgt || src.type !== filter && tgt.type !== filter) continue
      }
      def += `  ${edge.source}--|${edge.type}|${edge.target}`
      if (hoveredNode && (edge.source === hoveredNode || edge.target === hoveredNode)) def += ":::highlight"
      def += "\n"
    }
    def += "\n"
    def += "classDef highlight fill:#fde68a,stroke:#f59e42,stroke-width:3px;\n"
    return def
  }

  React.useEffect(() => {
    if (!graph || !diagramRef.current) return
    const code = renderMermaid(graph)
    try {
      mermaid.initialize({ startOnLoad: false })
      ;(async () => {
        const { svg } = await mermaid.render("system-graph", code)
        if (diagramRef.current) {
          diagramRef.current.innerHTML = svg
          // Add click/hover event delegation
          diagramRef.current.querySelectorAll("g[class*=node]").forEach((el) => {
            el.addEventListener("click", (e) => {
              const id = (el as SVGGElement).id.replace(/-.*$/, "")
              const node = graph.nodes.find(n => n.id === id)
              if (node) setSelectedNode(node)
            })
            el.addEventListener("mouseenter", () => {
              const id = (el as SVGGElement).id.replace(/-.*$/, "")
              setHoveredNode(id)
            })
            el.addEventListener("mouseleave", () => setHoveredNode(null))
            el.setAttribute("style", "cursor:pointer")
          })
        }
      })()
    } catch (err) {
      setError("Failed to render diagram")
    }
  }, [graph, filter, hoveredNode])

  return (
    <section className="w-full max-w-4xl mx-auto my-8 p-4 bg-white rounded shadow flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-bold">System Dependency Graph</h2>
        <div className="flex gap-2 items-center">
          <label htmlFor="node-type" className="text-sm">Filter:</label>
          <select
            id="node-type"
            className="border rounded px-2 py-1 text-sm"
            value={filter}
            onChange={e => setFilter(e.target.value as NodeType)}
          >
            {NODE_TYPES.map(type => (
              <option key={type} value={type}>{type.charAt(0).toUpperCase() + type.slice(1)}</option>
            ))}
          </select>
          <button
            className="px-3 py-1 rounded bg-blue-500 text-white hover:bg-blue-600 ml-2"
            onClick={fetchGraph}
            disabled={loading}
          >
            Refresh
          </button>
        </div>
      </div>
      {loading && <div>Loading graph...</div>}
      {error && <div className="text-red-500">{error}</div>}
      {graph && (
        <>
          <div ref={diagramRef} className="overflow-x-auto bg-gray-100 p-2 rounded border border-gray-200" />
          <p className="text-xs text-gray-500 mt-2">Click any node for details. If the diagram does not render, copy the code below into <a href="https://mermaid.live/" target="_blank" rel="noopener noreferrer" className="underline">Mermaid Live Editor</a>.</p>
          <pre className="overflow-x-auto text-xs bg-gray-100 p-2 rounded border border-gray-200 mt-2">{renderMermaid(graph)}</pre>
        </>
      )}
      {/* Node details modal */}
      {selectedNode && (
        <div className="fixed inset-0 flex items-center justify-center z-50 bg-black bg-opacity-40" onClick={() => setSelectedNode(null)}>
          <div className="bg-white rounded shadow-lg p-6 min-w-[300px] max-w-[90vw]" onClick={e => e.stopPropagation()}>
            <h3 className="font-bold text-lg mb-2">Node Details</h3>
            <div className="mb-2"><span className="font-semibold">ID:</span> {selectedNode.id}</div>
            <div className="mb-2"><span className="font-semibold">Type:</span> {selectedNode.type}</div>
            <div className="mb-2"><span className="font-semibold">Label:</span> {selectedNode.label}</div>
            {selectedNode.type === "agent" && agentData[selectedNode.id] && (
              <>
                <div className="mb-2"><span className="font-semibold">Status:</span> {agentData[selectedNode.id].status}</div>
                <div className="mb-2"><span className="font-semibold">Last Heartbeat:</span> {agentData[selectedNode.id].last_heartbeat}</div>
                <div className="mb-2"><span className="font-semibold">Metrics:</span>
                  <pre className="bg-gray-100 rounded p-2 text-xs max-h-32 overflow-y-auto">{JSON.stringify(agentData[selectedNode.id].metrics, null, 2)}</pre>
                </div>
              </>
            )}
            {selectedNode.type !== "agent" && (
              <div className="mb-2 text-gray-500">No live metrics available for this node type.</div>
            )}
            <button className="mt-4 px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600" onClick={() => setSelectedNode(null)}>Close</button>
          </div>
        </div>
      )}
    </section>
  )
} 