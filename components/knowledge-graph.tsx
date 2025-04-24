"use client"

import * as React from "react";
import { useRef, useState } from "react";
import dynamic from "next/dynamic";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useQuery } from "@tanstack/react-query";

// Dynamically import Three.js components to avoid SSR issues
const ThreeCanvas = dynamic(() => import("@react-three/fiber").then(mod => mod.Canvas), {
  ssr: false
});
const ThreeOrbitControls = dynamic(() => import("@react-three/drei").then(mod => mod.OrbitControls), {
  ssr: false
});
const ThreeText = dynamic(() => import("@react-three/drei").then(mod => mod.Text), {
  ssr: false
});
const ThreeLine = dynamic(() => import("@react-three/drei").then(mod => mod.Line), {
  ssr: false
});

interface Node {
  id: string;
  label: string;
  position: [number, number, number];
  connections: string[];
}

interface Edge {
  from: string;
  to: string;
}

const NodeComponent: React.FC<{ position: [number, number, number]; label: string }> = ({ position, label }) => {
  return (
    <group position={position}>
      <mesh>
        <sphereGeometry args={[0.5, 32, 32]} />
        <meshStandardMaterial color="#00ff88" />
      </mesh>
      <ThreeText
        position={[0, 0.7, 0]}
        fontSize={0.3}
        color="#ffffff"
        anchorX="center"
        anchorY="middle"
      >
        {label}
      </ThreeText>
    </group>
  );
};

const EdgeComponent: React.FC<{ start: [number, number, number]; end: [number, number, number] }> = ({ start, end }) => {
  return (
    <ThreeLine
      points={[start, end]}
      color="#00ff88"
      lineWidth={1}
      dashed={false}
    />
  );
};

export function KnowledgeGraph() {
  const containerRef = useRef<HTMLDivElement>(null);
  const [hoveredNode, setHoveredNode] = useState<string | null>(null);

  const { data: graphData } = useQuery({
    queryKey: ["knowledge-graph"],
    queryFn: async () => {
      const response = await fetch("/api/knowledge-graph");
      return response.json();
    },
  });

  return (
    <Card className="col-span-1 md:col-span-2 h-[600px]">
      <CardHeader>
        <CardTitle>Knowledge Graph</CardTitle>
      </CardHeader>
      <CardContent className="h-[500px]">
        <ThreeCanvas
          camera={{ position: [0, 0, 15], fov: 75 }}
          style={{ background: "transparent" }}
        >
          <ambientLight intensity={0.5} />
          <pointLight position={[10, 10, 10]} />
          
          {graphData?.nodes.map((node: Node) => (
            <NodeComponent key={node.id} position={node.position} label={node.label} />
          ))}
          
          {graphData?.edges.map((edge: Edge, index: number) => {
            const startNode = graphData.nodes.find((n: Node) => n.id === edge.from);
            const endNode = graphData.nodes.find((n: Node) => n.id === edge.to);
            if (!startNode || !endNode) return null;
            return (
              <EdgeComponent
                key={`${edge.from}-${edge.to}`}
                start={startNode.position}
                end={endNode.position}
              />
            );
          })}
          
          <ThreeOrbitControls
            enablePan={true}
            enableZoom={true}
            enableRotate={true}
          />
        </ThreeCanvas>
      </CardContent>
    </Card>
  );
} 