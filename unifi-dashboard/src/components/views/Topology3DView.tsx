"use client";

import { useState, useEffect, useMemo, Suspense, useRef } from "react";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { OrbitControls, Text, Html, Stars } from "@react-three/drei";
import * as THREE from "three";
import { dataService } from "@/lib/data-service";
import type { TopologyNode, TopologyConnection } from "@/types";
import { MyceliumLinks } from "../three/MyceliumLinks";
import { ZoomIn, ZoomOut, RotateCcw, Maximize2, Box, Layers } from "lucide-react";

interface Topology3DViewProps {
  onNodeClick?: (node: TopologyNode) => void;
}

// Convert 2D topology coordinates to 3D space
function convertTo3D(node: TopologyNode, index: number): [number, number, number] {
  // Map percentage coordinates (0-100) to 3D space (-10 to 10)
  const x = ((node.x || 50) - 50) / 5;
  const z = ((node.y || 50) - 50) / 5;
  
  // Add some vertical variation based on node type
  let y = 0;
  switch (node.type) {
    case "internet": y = 4; break;
    case "orchestrator": y = 2; break;
    case "database": case "cache": y = -1; break;
    case "service": y = 0; break;
    case "agent": y = -2 + Math.sin(index * 0.5) * 0.5; break;
    case "person": case "user": y = -3; break;
    case "external": y = 0.5; break;
    default: y = 0;
  }
  
  return [x, y, z];
}

// Get color based on node type
function getNodeColor(type: string, status: string): string {
  if (status !== "online" && status !== "active") return "#6b7280";
  
  switch (type) {
    case "internet": return "#22d3ee";
    case "orchestrator": return "#a855f7";
    case "database": return "#f97316";
    case "cache": return "#ef4444";
    case "service": return "#eab308";
    case "agent": return "#06b6d4";
    case "person": return "#22c55e";
    case "user": return "#6366f1";
    case "external": return "#ec4899";
    default: return "#64748b";
  }
}

// 3D Node component
function Node3D({ 
  node, 
  position, 
  onClick 
}: { 
  node: TopologyNode; 
  position: [number, number, number]; 
  onClick?: () => void;
}) {
  const meshRef = useRef<THREE.Mesh>(null);
  const [hovered, setHovered] = useState(false);
  const color = getNodeColor(node.type, node.status);
  const isActive = node.status === "online" || node.status === "active";
  
  // Animate the node
  useFrame((state) => {
    if (meshRef.current && isActive) {
      // Gentle floating animation
      meshRef.current.position.y = position[1] + Math.sin(state.clock.elapsedTime * 0.5 + position[0]) * 0.05;
      // Subtle rotation
      meshRef.current.rotation.y += 0.002;
    }
  });

  const nodeSize = node.type === "orchestrator" ? 0.6 : node.type === "internet" ? 0.5 : 0.35;

  return (
    <group position={position}>
      <mesh
        ref={meshRef}
        onClick={onClick}
        onPointerOver={() => setHovered(true)}
        onPointerOut={() => setHovered(false)}
        scale={hovered ? 1.2 : 1}
      >
        {node.type === "orchestrator" ? (
          <octahedronGeometry args={[nodeSize, 0]} />
        ) : node.type === "database" || node.type === "cache" ? (
          <cylinderGeometry args={[nodeSize * 0.7, nodeSize * 0.7, nodeSize, 8]} />
        ) : node.type === "internet" ? (
          <icosahedronGeometry args={[nodeSize, 1]} />
        ) : node.type === "person" || node.type === "user" ? (
          <sphereGeometry args={[nodeSize * 0.8, 16, 16]} />
        ) : (
          <boxGeometry args={[nodeSize, nodeSize, nodeSize]} />
        )}
        <meshStandardMaterial
          color={color}
          emissive={color}
          emissiveIntensity={isActive ? (hovered ? 0.8 : 0.4) : 0.1}
          metalness={0.3}
          roughness={0.4}
          transparent
          opacity={isActive ? 0.9 : 0.4}
        />
      </mesh>
      
      {/* Glow effect */}
      {isActive && (
        <mesh scale={1.3}>
          <sphereGeometry args={[nodeSize, 16, 16]} />
          <meshBasicMaterial
            color={color}
            transparent
            opacity={hovered ? 0.15 : 0.08}
            side={THREE.BackSide}
          />
        </mesh>
      )}
      
      {/* Label */}
      <Html
        position={[0, -nodeSize - 0.3, 0]}
        center
        style={{
          pointerEvents: "none",
          userSelect: "none",
        }}
      >
        <div className="whitespace-nowrap text-center">
          <div 
            className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-black/60 backdrop-blur-sm"
            style={{ color }}
          >
            {node.name}
          </div>
        </div>
      </Html>
    </group>
  );
}

// Central animated core
function CentralCore() {
  const meshRef = useRef<THREE.Mesh>(null);
  const ringRef = useRef<THREE.Mesh>(null);
  
  useFrame((state) => {
    if (meshRef.current) {
      meshRef.current.rotation.y += 0.005;
      meshRef.current.rotation.x = Math.sin(state.clock.elapsedTime * 0.3) * 0.1;
    }
    if (ringRef.current) {
      ringRef.current.rotation.z += 0.003;
    }
  });

  return (
    <group position={[0, 0, 0]}>
      {/* Central glowing core */}
      <mesh ref={meshRef}>
        <dodecahedronGeometry args={[0.3, 0]} />
        <meshStandardMaterial
          color="#a855f7"
          emissive="#a855f7"
          emissiveIntensity={0.6}
          metalness={0.5}
          roughness={0.2}
        />
      </mesh>
      
      {/* Orbiting ring */}
      <mesh ref={ringRef} rotation={[Math.PI / 2, 0, 0]}>
        <torusGeometry args={[0.5, 0.02, 8, 32]} />
        <meshBasicMaterial color="#a855f7" transparent opacity={0.4} />
      </mesh>
      
      {/* Outer glow */}
      <mesh>
        <sphereGeometry args={[0.8, 16, 16]} />
        <meshBasicMaterial
          color="#a855f7"
          transparent
          opacity={0.05}
          side={THREE.BackSide}
        />
      </mesh>
    </group>
  );
}

// Floating particles in the scene
function FloatingParticles() {
  const points = useMemo(() => {
    const positions = new Float32Array(200 * 3);
    for (let i = 0; i < 200; i++) {
      positions[i * 3] = (Math.random() - 0.5) * 30;
      positions[i * 3 + 1] = (Math.random() - 0.5) * 20;
      positions[i * 3 + 2] = (Math.random() - 0.5) * 30;
    }
    return positions;
  }, []);

  const pointsRef = useRef<THREE.Points>(null);

  useFrame((state) => {
    if (pointsRef.current) {
      pointsRef.current.rotation.y = state.clock.elapsedTime * 0.02;
    }
  });

  return (
    <points ref={pointsRef}>
      <bufferGeometry>
        <bufferAttribute
          attach="attributes-position"
          count={200}
          array={points}
          itemSize={3}
        />
      </bufferGeometry>
      <pointsMaterial
        size={0.03}
        color="#6366f1"
        transparent
        opacity={0.4}
        sizeAttenuation
      />
    </points>
  );
}

// Scene camera controller
function CameraController({ autoRotate }: { autoRotate: boolean }) {
  const { camera } = useThree();
  
  useEffect(() => {
    camera.position.set(8, 6, 12);
    camera.lookAt(0, 0, 0);
  }, [camera]);

  return (
    <OrbitControls
      enablePan
      enableZoom
      enableRotate
      autoRotate={autoRotate}
      autoRotateSpeed={0.5}
      minDistance={5}
      maxDistance={30}
      maxPolarAngle={Math.PI / 1.5}
    />
  );
}

export function Topology3DView({ onNodeClick }: Topology3DViewProps) {
  const [nodes, setNodes] = useState<TopologyNode[]>([]);
  const [connections, setConnections] = useState<TopologyConnection[]>([]);
  const [autoRotate, setAutoRotate] = useState(true);
  const [showMycelium, setShowMycelium] = useState(true);
  const [selectedNode, setSelectedNode] = useState<TopologyNode | null>(null);

  // Subscribe to topology updates
  useEffect(() => {
    const unsubscribe = dataService.subscribe("topology", (data) => {
      const topologyData = data as { nodes: TopologyNode[]; connections: TopologyConnection[] };
      setNodes(topologyData.nodes);
      setConnections(topologyData.connections);
    });

    return unsubscribe;
  }, []);

  // Convert nodes to 3D format for MyceliumLinks
  const nodes3D = useMemo(() => {
    return nodes.map((node, index) => ({
      id: node.id,
      position: convertTo3D(node, index),
    }));
  }, [nodes]);

  // Convert connections to links format
  const links = useMemo(() => {
    return connections
      .filter((c) => c.active)
      .map((c) => ({
        source: c.source,
        target: c.target,
        weight: Math.min(2, (c.bandwidth || 50) / 100 + 0.5),
        type: c.type,
      }));
  }, [connections]);

  const handleNodeClick = (node: TopologyNode) => {
    setSelectedNode(node);
    onNodeClick?.(node);
  };

  return (
    <div className="flex h-full flex-col">
      {/* Top Bar */}
      <div className="flex items-center justify-between border-b border-gray-800 bg-[#1E293B] px-4 py-3">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <Box className="h-5 w-5 text-purple-400" />
            <h2 className="text-lg font-semibold">3D Mycelium Network</h2>
          </div>
          <div className="flex items-center gap-3 text-xs">
            <label className="flex items-center gap-1.5 cursor-pointer">
              <input
                type="checkbox"
                checked={showMycelium}
                onChange={(e) => setShowMycelium(e.target.checked)}
                className="h-3 w-3 rounded border-gray-600 bg-gray-700 text-purple-500 focus:ring-purple-500"
              />
              <span className="text-gray-400">Mycelium Links</span>
            </label>
            <label className="flex items-center gap-1.5 cursor-pointer">
              <input
                type="checkbox"
                checked={autoRotate}
                onChange={(e) => setAutoRotate(e.target.checked)}
                className="h-3 w-3 rounded border-gray-600 bg-gray-700 text-purple-500 focus:ring-purple-500"
              />
              <span className="text-gray-400">Auto Rotate</span>
            </label>
          </div>
        </div>
        <div className="flex items-center gap-1 text-gray-400">
          <span className="text-xs mr-2">{nodes.length} nodes · {connections.filter(c => c.active).length} links</span>
          <button className="rounded p-1.5 hover:bg-gray-700 hover:text-white">
            <Layers className="h-4 w-4" />
          </button>
        </div>
      </div>

      {/* 3D Canvas */}
      <div className="flex-1 relative bg-[#0a0f1a]">
        <Canvas
          camera={{ position: [8, 6, 12], fov: 50 }}
          gl={{ antialias: true, alpha: true }}
          style={{ background: "linear-gradient(180deg, #0a0f1a 0%, #1a1f2e 100%)" }}
        >
          <Suspense fallback={null}>
            {/* Lighting */}
            <ambientLight intensity={0.3} />
            <pointLight position={[10, 10, 10]} intensity={0.8} color="#ffffff" />
            <pointLight position={[-10, -10, -10]} intensity={0.4} color="#a855f7" />
            <spotLight
              position={[0, 15, 0]}
              angle={0.3}
              penumbra={1}
              intensity={0.5}
              color="#06b6d4"
            />

            {/* Background elements */}
            <Stars radius={50} depth={50} count={1000} factor={2} saturation={0} fade speed={0.5} />
            <FloatingParticles />

            {/* Mycelium connections */}
            {showMycelium && nodes3D.length > 0 && links.length > 0 && (
              <MyceliumLinks
                nodes={nodes3D}
                links={links}
                scale={1}
                curl={1.3}
                segmentsPerLink={24}
                fuzz={0.4}
                color="#a78bfa"
              />
            )}

            {/* Nodes */}
            {nodes.map((node, index) => (
              <Node3D
                key={node.id}
                node={node}
                position={convertTo3D(node, index)}
                onClick={() => handleNodeClick(node)}
              />
            ))}

            {/* Central decorative core */}
            <CentralCore />

            {/* Grid helper (subtle) */}
            <gridHelper args={[30, 30, "#1e293b", "#1e293b"]} position={[0, -5, 0]} />

            {/* Controls */}
            <CameraController autoRotate={autoRotate} />
          </Suspense>
        </Canvas>

        {/* Legend */}
        <div className="absolute bottom-4 left-4 rounded bg-[#1E293B]/90 p-3 text-[10px] backdrop-blur-sm border border-gray-700/50">
          <div className="font-medium text-white mb-2">Node Types</div>
          <div className="grid grid-cols-2 gap-x-4 gap-y-1">
            <span className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-purple-500" />
              <span className="text-gray-400">Orchestrator</span>
            </span>
            <span className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-cyan-400" />
              <span className="text-gray-400">Agent</span>
            </span>
            <span className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-orange-500" />
              <span className="text-gray-400">Database</span>
            </span>
            <span className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-yellow-500" />
              <span className="text-gray-400">Service</span>
            </span>
            <span className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-green-500" />
              <span className="text-gray-400">Person</span>
            </span>
            <span className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-pink-500" />
              <span className="text-gray-400">External</span>
            </span>
          </div>
        </div>

        {/* Selected node details */}
        {selectedNode && (
          <div className="absolute top-4 right-4 w-56 rounded bg-[#1E293B]/95 p-3 backdrop-blur-sm border border-gray-700/50">
            <div className="flex items-center justify-between mb-2">
              <span className="font-medium text-white truncate">{selectedNode.name}</span>
              <button onClick={() => setSelectedNode(null)} className="text-gray-400 hover:text-white">×</button>
            </div>
            <div className="space-y-1.5 text-xs">
              <div className="flex justify-between">
                <span className="text-gray-400">Type:</span>
                <span className="text-white capitalize">{selectedNode.type}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Status:</span>
                <span className={selectedNode.status === "online" ? "text-green-400" : "text-gray-400"}>
                  {selectedNode.status}
                </span>
              </div>
              {selectedNode.category && (
                <div className="flex justify-between">
                  <span className="text-gray-400">Category:</span>
                  <span className="text-white capitalize">{selectedNode.category}</span>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Controls hint */}
        <div className="absolute bottom-4 right-4 text-[10px] text-gray-500">
          Drag to rotate · Scroll to zoom · Right-click to pan
        </div>
      </div>
    </div>
  );
}
