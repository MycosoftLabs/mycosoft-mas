"use client";

/**
 * GraphCanvas - Cytoscape.js graph visualization for ancestry data
 * Displays phylogenetic relationships as an interactive network
 */

import { useEffect, useRef, useCallback, useState } from "react";
import cytoscape, { Core, NodeSingular } from "cytoscape";

export interface GraphNode {
  id: string;
  label: string;
  type: "taxon" | "specimen" | "sequencing_run" | "assembly" | "variant_set";
  rank?: string;
  data?: Record<string, unknown>;
}

export interface GraphEdge {
  source: string;
  target: string;
  relationship: "parent_of" | "assigned_to" | "sequenced_by" | "assembled_into" | "has_variants";
}

interface GraphCanvasProps {
  nodes: GraphNode[];
  edges: GraphEdge[];
  layout?: "breadthfirst" | "cose" | "circle" | "grid";
  onNodeClick?: (node: GraphNode) => void;
  onNodeDoubleClick?: (node: GraphNode) => void;
  selectedNodeId?: string | null;
  className?: string;
}

// Node colors by type
const NODE_COLORS: Record<string, string> = {
  taxon: "#7c3aed",        // purple
  specimen: "#0891b2",     // cyan
  sequencing_run: "#059669", // green
  assembly: "#ea580c",     // orange
  variant_set: "#db2777",  // pink
};

// Node shapes by type
const NODE_SHAPES: Record<string, string> = {
  taxon: "roundrectangle",
  specimen: "ellipse",
  sequencing_run: "diamond",
  assembly: "rectangle",
  variant_set: "triangle",
};

// Edge colors by relationship
const EDGE_COLORS: Record<string, string> = {
  parent_of: "#8b5cf6",
  assigned_to: "#06b6d4",
  sequenced_by: "#10b981",
  assembled_into: "#f97316",
  has_variants: "#ec4899",
};

export function GraphCanvas({
  nodes,
  edges,
  layout = "breadthfirst",
  onNodeClick,
  onNodeDoubleClick,
  selectedNodeId,
  className = "",
}: GraphCanvasProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<Core | null>(null);
  const [isReady, setIsReady] = useState(false);

  // Initialize Cytoscape
  useEffect(() => {
    if (!containerRef.current) return;

    const cy = cytoscape({
      container: containerRef.current,
      style: [
        {
          selector: "node",
          style: {
            "background-color": "data(color)",
            label: "data(label)",
            color: "#e5e7eb",
            "text-valign": "bottom",
            "text-halign": "center",
            "font-size": "10px",
            "text-margin-y": 4,
            width: 30,
            height: 30,
            shape: "data(shape)" as cytoscape.Css.NodeShape,
            "border-width": 2,
            "border-color": "#1f2937",
          },
        },
        {
          selector: "node:selected",
          style: {
            "border-width": 3,
            "border-color": "#60a5fa",
            "background-color": "#3b82f6",
          },
        },
        {
          selector: "node.highlighted",
          style: {
            "border-width": 3,
            "border-color": "#fbbf24",
          },
        },
        {
          selector: "edge",
          style: {
            width: 2,
            "line-color": "data(color)",
            "target-arrow-color": "data(color)",
            "target-arrow-shape": "triangle",
            "curve-style": "bezier",
            opacity: 0.7,
          },
        },
        {
          selector: "edge:selected",
          style: {
            width: 3,
            opacity: 1,
          },
        },
      ],
      layout: { name: "preset" }, // We'll run layout after adding elements
      wheelSensitivity: 0.3,
      minZoom: 0.2,
      maxZoom: 3,
    });

    cyRef.current = cy;
    setIsReady(true);

    // Event handlers
    cy.on("tap", "node", (evt) => {
      const node = evt.target;
      const nodeData: GraphNode = {
        id: node.id(),
        label: node.data("label"),
        type: node.data("type"),
        rank: node.data("rank"),
        data: node.data("originalData"),
      };
      onNodeClick?.(nodeData);
    });

    cy.on("dbltap", "node", (evt) => {
      const node = evt.target;
      const nodeData: GraphNode = {
        id: node.id(),
        label: node.data("label"),
        type: node.data("type"),
        rank: node.data("rank"),
        data: node.data("originalData"),
      };
      onNodeDoubleClick?.(nodeData);
    });

    return () => {
      cy.destroy();
      cyRef.current = null;
    };
  }, [onNodeClick, onNodeDoubleClick]);

  // Update graph data
  useEffect(() => {
    if (!cyRef.current || !isReady) return;

    const cy = cyRef.current;

    // Clear existing elements
    cy.elements().remove();

    // Add nodes
    const cyNodes = nodes.map((node) => ({
      data: {
        id: node.id,
        label: node.label,
        type: node.type,
        rank: node.rank,
        color: NODE_COLORS[node.type] || "#6b7280",
        shape: NODE_SHAPES[node.type] || "ellipse",
        originalData: node.data,
      },
    }));

    // Add edges
    const cyEdges = edges.map((edge, idx) => ({
      data: {
        id: `edge-${idx}`,
        source: edge.source,
        target: edge.target,
        relationship: edge.relationship,
        color: EDGE_COLORS[edge.relationship] || "#6b7280",
      },
    }));

    cy.add([...cyNodes, ...cyEdges]);

    // Run layout
    const layoutConfig = getLayoutConfig(layout);
    cy.layout(layoutConfig).run();

    // Fit to view
    setTimeout(() => {
      cy.fit(undefined, 50);
    }, 100);
  }, [nodes, edges, layout, isReady]);

  // Handle selected node
  useEffect(() => {
    if (!cyRef.current || !isReady) return;

    const cy = cyRef.current;

    // Remove previous highlights
    cy.nodes().removeClass("highlighted");

    if (selectedNodeId) {
      const node = cy.getElementById(selectedNodeId);
      if (node.length > 0) {
        node.addClass("highlighted");
        // Center on selected node
        cy.animate({
          center: { eles: node },
          zoom: 1.5,
          duration: 300,
        });
      }
    }
  }, [selectedNodeId, isReady]);

  // Change layout
  const runLayout = useCallback(
    (newLayout: "breadthfirst" | "cose" | "circle" | "grid") => {
      if (!cyRef.current) return;
      const layoutConfig = getLayoutConfig(newLayout);
      cyRef.current.layout(layoutConfig).run();
    },
    []
  );

  // Fit to viewport
  const fit = useCallback(() => {
    cyRef.current?.fit(undefined, 50);
  }, []);

  // Export position
  const getPositions = useCallback(() => {
    if (!cyRef.current) return {};
    const positions: Record<string, { x: number; y: number }> = {};
    cyRef.current.nodes().forEach((node: NodeSingular) => {
      positions[node.id()] = node.position();
    });
    return positions;
  }, []);

  return (
    <div className={`relative ${className}`}>
      <div
        ref={containerRef}
        className="w-full h-full bg-gray-900 rounded-lg"
        style={{ minHeight: 400 }}
      />

      {/* Layout controls */}
      <div className="absolute top-3 right-3 flex gap-2">
        <button
          onClick={() => runLayout("breadthfirst")}
          className={`px-2 py-1 text-xs rounded ${
            layout === "breadthfirst" ? "bg-purple-600" : "bg-gray-700"
          } text-white hover:bg-purple-500 transition-colors`}
        >
          Tree
        </button>
        <button
          onClick={() => runLayout("cose")}
          className={`px-2 py-1 text-xs rounded ${
            layout === "cose" ? "bg-purple-600" : "bg-gray-700"
          } text-white hover:bg-purple-500 transition-colors`}
        >
          Force
        </button>
        <button
          onClick={() => runLayout("circle")}
          className={`px-2 py-1 text-xs rounded ${
            layout === "circle" ? "bg-purple-600" : "bg-gray-700"
          } text-white hover:bg-purple-500 transition-colors`}
        >
          Circle
        </button>
        <button
          onClick={fit}
          className="px-2 py-1 text-xs rounded bg-gray-700 text-white hover:bg-gray-600 transition-colors"
        >
          Fit
        </button>
      </div>

      {/* Legend */}
      <div className="absolute bottom-3 left-3 p-2 rounded bg-black/60 backdrop-blur-sm text-xs">
        <div className="text-gray-400 mb-1">Node Types</div>
        <div className="grid grid-cols-2 gap-x-4 gap-y-1">
          {Object.entries(NODE_COLORS).map(([type, color]) => (
            <div key={type} className="flex items-center gap-1">
              <div
                className="w-3 h-3 rounded"
                style={{ backgroundColor: color }}
              />
              <span className="text-gray-300 capitalize">{type.replace("_", " ")}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// Layout configurations
function getLayoutConfig(layout: string): cytoscape.LayoutOptions {
  switch (layout) {
    case "breadthfirst":
      return {
        name: "breadthfirst",
        directed: true,
        padding: 30,
        spacingFactor: 1.5,
        animate: true,
        animationDuration: 300,
      };
    case "cose":
      return {
        name: "cose",
        animate: true,
        animationDuration: 300,
        nodeRepulsion: () => 10000,
        idealEdgeLength: () => 100,
        padding: 30,
      };
    case "circle":
      return {
        name: "circle",
        padding: 30,
        animate: true,
        animationDuration: 300,
      };
    case "grid":
      return {
        name: "grid",
        padding: 30,
        animate: true,
        animationDuration: 300,
      };
    default:
      return { name: "preset" };
  }
}

export default GraphCanvas;
