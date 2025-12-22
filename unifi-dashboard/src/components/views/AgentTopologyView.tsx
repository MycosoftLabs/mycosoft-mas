"use client";

import { useState, useRef, useEffect, useCallback, useMemo } from "react";
import { ZoomIn, ZoomOut, Maximize2, RotateCcw, Pause, Play } from "lucide-react";
import { dataService } from "@/lib/data-service";
import type { TopologyNode, TopologyConnection } from "@/types";

interface AgentTopologyViewProps {
  onNodeClick?: (node: TopologyNode) => void;
}

// Smaller particle for realistic data flow
interface Particle {
  id: number;
  progress: number;
  speed: number;
  size: number;
  opacity: number;
  connectionIndex: number;
  reverse: boolean;
  trail: number; // Trail length
}

// Organic wave offset for mycelium-like movement
interface WaveOffset {
  amplitude: number;
  frequency: number;
  phase: number;
  speed: number;
}

// Icon components for different node types
function getNodeIcon(type: string, status: string) {
  const isOnline = status === "online" || status === "active";
  const baseColor = isOnline ? "text-blue-400" : "text-gray-500";
  
  switch (type) {
    case "internet":
      return (
        <svg className={`h-6 w-6 ${baseColor}`} fill="currentColor" viewBox="0 0 24 24">
          <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 17.93c-3.95-.49-7-3.85-7-7.93 0-.62.08-1.21.21-1.79L9 15v1c0 1.1.9 2 2 2v1.93zm6.9-2.54c-.26-.81-1-1.39-1.9-1.39h-1v-3c0-.55-.45-1-1-1H8v-2h2c.55 0 1-.45 1-1V7h2c1.1 0 2-.9 2-2v-.41c2.93 1.19 5 4.06 5 7.41 0 2.08-.8 3.97-2.1 5.39z" />
        </svg>
      );
    case "orchestrator":
      return (
        <svg className={`h-8 w-8 ${isOnline ? "text-purple-400" : "text-gray-500"}`} fill="none" stroke="currentColor" strokeWidth="1.5" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" d="M9.75 3.104v5.714a2.25 2.25 0 01-.659 1.591L5 14.5M9.75 3.104c-.251.023-.501.05-.75.082m.75-.082a24.301 24.301 0 014.5 0m0 0v5.714c0 .597.237 1.17.659 1.591L19.8 15.3M14.25 3.104c.251.023.501.05.75.082M19.8 15.3l-1.57.393A9.065 9.065 0 0112 15a9.065 9.065 0 00-6.23.693L5 15.5m14.8-.2a2.25 2.25 0 01-1.311 2.046l-5.104 2.217a2.25 2.25 0 01-1.77 0L6.511 17.346A2.25 2.25 0 015.2 15.3" />
        </svg>
      );
    case "agent":
      return (
        <svg className={`h-5 w-5 ${isOnline ? "text-cyan-400" : "text-gray-500"}`} fill="none" stroke="currentColor" strokeWidth="1.5" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 3v1.5M4.5 8.25H3m18 0h-1.5M4.5 12H3m18 0h-1.5m-15 3.75H3m18 0h-1.5M8.25 19.5V21M12 3v1.5m0 15V21m3.75-18v1.5m0 15V21m-9-1.5h10.5a2.25 2.25 0 002.25-2.25V6.75a2.25 2.25 0 00-2.25-2.25H6.75A2.25 2.25 0 004.5 6.75v10.5a2.25 2.25 0 002.25 2.25zm.75-12h9v9h-9v-9z" />
        </svg>
      );
    case "person":
      return (
        <svg className={`h-5 w-5 ${isOnline ? "text-green-400" : "text-gray-500"}`} fill="none" stroke="currentColor" strokeWidth="1.5" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z" />
        </svg>
      );
    case "database":
      return (
        <svg className={`h-5 w-5 ${isOnline ? "text-orange-400" : "text-gray-500"}`} fill="none" stroke="currentColor" strokeWidth="1.5" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" d="M20.25 6.375c0 2.278-3.694 4.125-8.25 4.125S3.75 8.653 3.75 6.375m16.5 0c0-2.278-3.694-4.125-8.25-4.125S3.75 4.097 3.75 6.375m16.5 0v11.25c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125V6.375m16.5 0v3.75m-16.5-3.75v3.75m16.5 0v3.75C20.25 16.153 16.556 18 12 18s-8.25-1.847-8.25-4.125v-3.75m16.5 0c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125" />
        </svg>
      );
    case "service":
      return (
        <svg className={`h-5 w-5 ${isOnline ? "text-yellow-400" : "text-gray-500"}`} fill="none" stroke="currentColor" strokeWidth="1.5" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" d="M5.25 14.25h13.5m-13.5 0a3 3 0 01-3-3m3 3a3 3 0 100 6h13.5a3 3 0 100-6m-16.5-3a3 3 0 013-3h13.5a3 3 0 013 3m-19.5 0a4.5 4.5 0 01.9-2.7L5.737 5.1a3.375 3.375 0 012.7-1.35h7.126c1.062 0 2.062.5 2.7 1.35l2.587 3.45a4.5 4.5 0 01.9 2.7m0 0a3 3 0 01-3 3m0 3h.008v.008h-.008v-.008zm0-6h.008v.008h-.008v-.008zm-3 6h.008v.008h-.008v-.008zm0-6h.008v.008h-.008v-.008z" />
        </svg>
      );
    case "external":
      return (
        <svg className={`h-5 w-5 ${isOnline ? "text-pink-400" : "text-gray-500"}`} fill="none" stroke="currentColor" strokeWidth="1.5" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 6H5.25A2.25 2.25 0 003 8.25v10.5A2.25 2.25 0 005.25 21h10.5A2.25 2.25 0 0018 18.75V10.5m-10.5 6L21 3m0 0h-5.25M21 3v5.25" />
        </svg>
      );
    case "user":
      return (
        <svg className={`h-5 w-5 ${isOnline ? "text-indigo-400" : "text-gray-500"}`} fill="none" stroke="currentColor" strokeWidth="1.5" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" d="M9 17.25v1.007a3 3 0 01-.879 2.122L7.5 21h9l-.621-.621A3 3 0 0115 18.257V17.25m6-12V15a2.25 2.25 0 01-2.25 2.25H5.25A2.25 2.25 0 013 15V5.25m18 0A2.25 2.25 0 0018.75 3H5.25A2.25 2.25 0 003 5.25m18 0V12a2.25 2.25 0 01-2.25 2.25H5.25A2.25 2.25 0 013 12V5.25" />
        </svg>
      );
    case "cache":
      return (
        <svg className={`h-5 w-5 ${isOnline ? "text-red-400" : "text-gray-500"}`} fill="none" stroke="currentColor" strokeWidth="1.5" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" d="M20.25 7.5l-.625 10.632a2.25 2.25 0 01-2.247 2.118H6.622a2.25 2.25 0 01-2.247-2.118L3.75 7.5m8.25 3v6.75m0 0l-3-3m3 3l3-3M3.375 7.5h17.25c.621 0 1.125-.504 1.125-1.125v-1.5c0-.621-.504-1.125-1.125-1.125H3.375c-.621 0-1.125.504-1.125 1.125v1.5c0 .621.504 1.125 1.125 1.125z" />
        </svg>
      );
    default:
      return (
        <svg className={`h-5 w-5 ${baseColor}`} fill="none" stroke="currentColor" strokeWidth="1.5" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" d="M21 7.5l-9-5.25L3 7.5m18 0l-9 5.25m9-5.25v9l-9 5.25M3 7.5l9 5.25M3 7.5v9l9 5.25m0-9v9" />
        </svg>
      );
  }
}

function getConnectionColor(type: string, active: boolean): string {
  if (!active) return "#4b5563";
  switch (type) {
    case "data": return "#3b82f6";
    case "control": return "#8b5cf6";
    case "command": return "#22c55e";
    case "ui": return "#06b6d4";
    case "interaction": return "#f59e0b";
    case "transaction": return "#ec4899";
    case "message": return "#14b8a6";
    default: return "#6b7280";
  }
}

function getParticleColor(type: string): string {
  switch (type) {
    case "data": return "#60a5fa";
    case "control": return "#a78bfa";
    case "command": return "#4ade80";
    case "ui": return "#22d3ee";
    case "interaction": return "#fbbf24";
    case "transaction": return "#f472b6";
    case "message": return "#2dd4bf";
    default: return "#9ca3af";
  }
}

export function AgentTopologyView({ onNodeClick }: AgentTopologyViewProps) {
  const [nodes, setNodes] = useState<TopologyNode[]>([]);
  const [connections, setConnections] = useState<TopologyConnection[]>([]);
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [selectedNode, setSelectedNode] = useState<TopologyNode | null>(null);
  const [showTraffic, setShowTraffic] = useState(true);
  const [showLabels, setShowLabels] = useState(true);
  const [dragging, setDragging] = useState<string | null>(null);
  const [dragOffset, setDragOffset] = useState({ x: 0, y: 0 });
  const [isPanning, setIsPanning] = useState(false);
  const [lastPanPoint, setLastPanPoint] = useState({ x: 0, y: 0 });
  const [isAnimating, setIsAnimating] = useState(true);
  const [particles, setParticles] = useState<Particle[]>([]);
  const [time, setTime] = useState(0); // For organic wave animation
  const [waveOffsets, setWaveOffsets] = useState<WaveOffset[]>([]);
  const [mousePos, setMousePos] = useState({ x: 50, y: 50 }); // For mouse-reactive glow
  
  const canvasRef = useRef<HTMLDivElement>(null);
  const svgRef = useRef<SVGSVGElement>(null);
  const animationFrameRef = useRef<number | null>(null);
  const particleIdRef = useRef(0);
  const glowRef = useRef<HTMLDivElement>(null);

  // Subscribe to topology updates
  useEffect(() => {
    const unsubscribe = dataService.subscribe("topology", (data) => {
      const topologyData = data as { nodes: TopologyNode[]; connections: TopologyConnection[] };
      setNodes(topologyData.nodes);
      setConnections(topologyData.connections);
      
      // Generate wave offsets for each connection (mycelium-like movement)
      const offsets = topologyData.connections.map(() => ({
        amplitude: 0.3 + Math.random() * 0.5,
        frequency: 0.5 + Math.random() * 1.5,
        phase: Math.random() * Math.PI * 2,
        speed: 0.5 + Math.random() * 1,
      }));
      setWaveOffsets(offsets);
    });

    return unsubscribe;
  }, []);

  // Initialize particles for active connections
  useEffect(() => {
    if (!isAnimating) return;

    const initialParticles: Particle[] = [];
    connections.forEach((conn, index) => {
      if (conn.active) {
        // More particles, smaller sizes
        const particleCount = Math.max(3, Math.min(12, Math.floor((conn.bandwidth || 50) / 50)));
        for (let i = 0; i < particleCount; i++) {
          initialParticles.push({
            id: particleIdRef.current++,
            progress: Math.random(),
            speed: 0.001 + Math.random() * 0.002, // Slower, more subtle
            size: 0.15 + Math.random() * 0.25, // Much smaller (0.15 - 0.4)
            opacity: 0.4 + Math.random() * 0.5,
            connectionIndex: index,
            reverse: Math.random() > 0.6,
            trail: 2 + Math.random() * 3,
          });
        }
      }
    });
    setParticles(initialParticles);
  }, [connections, isAnimating]);

  // Main animation loop
  useEffect(() => {
    if (!isAnimating || !showTraffic) {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
      return;
    }

    const animate = () => {
      // Update time for organic wave movement
      setTime((t) => t + 0.016); // ~60fps

      // Update particles
      setParticles((prev) =>
        prev.map((particle) => {
          let newProgress = particle.reverse
            ? particle.progress - particle.speed
            : particle.progress + particle.speed;

          if (newProgress > 1 || newProgress < 0) {
            newProgress = particle.reverse ? 1 : 0;
            return {
              ...particle,
              progress: newProgress,
              speed: 0.001 + Math.random() * 0.002,
              size: 0.15 + Math.random() * 0.25,
              opacity: 0.4 + Math.random() * 0.5,
            };
          }

          return { ...particle, progress: newProgress };
        })
      );

      animationFrameRef.current = requestAnimationFrame(animate);
    };

    animationFrameRef.current = requestAnimationFrame(animate);

    return () => {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
    };
  }, [isAnimating, showTraffic]);

  // Calculate organic curved path with wave animation
  const getOrganicPath = useCallback(
    (connection: TopologyConnection, index: number): string => {
      const sourceNode = nodes.find((n) => n.id === connection.source);
      const targetNode = nodes.find((n) => n.id === connection.target);
      if (!sourceNode || !targetNode) return "";

      const x1 = sourceNode.x;
      const y1 = sourceNode.y;
      const x2 = targetNode.x;
      const y2 = targetNode.y;

      const wave = waveOffsets[index] || { amplitude: 0.5, frequency: 1, phase: 0, speed: 1 };
      
      // Calculate perpendicular direction for wave
      const dx = x2 - x1;
      const dy = y2 - y1;
      const len = Math.sqrt(dx * dx + dy * dy);
      const nx = -dy / len;
      const ny = dx / len;

      // Create organic curve with animated wave
      const midX = (x1 + x2) / 2;
      const midY = (y1 + y2) / 2;
      
      // Animated wave offset
      const waveOffset = Math.sin(time * wave.speed + wave.phase) * wave.amplitude;
      
      // Multiple control points for more organic look
      const cp1x = x1 + dx * 0.25 + nx * (waveOffset * 0.5);
      const cp1y = y1 + dy * 0.25 + ny * (waveOffset * 0.5);
      const cp2x = midX + nx * waveOffset;
      const cp2y = midY + ny * waveOffset;
      const cp3x = x1 + dx * 0.75 + nx * (waveOffset * 0.3);
      const cp3y = y1 + dy * 0.75 + ny * (waveOffset * 0.3);

      // Cubic bezier for smoother organic curve
      return `M ${x1} ${y1} C ${cp1x} ${cp1y}, ${cp2x} ${cp2y}, ${midX} ${midY} S ${cp3x} ${cp3y}, ${x2} ${y2}`;
    },
    [nodes, waveOffsets, time]
  );

  // Calculate point on organic path at progress
  const getPointOnPath = useCallback(
    (connection: TopologyConnection, index: number, progress: number): { x: number; y: number } | null => {
      const sourceNode = nodes.find((n) => n.id === connection.source);
      const targetNode = nodes.find((n) => n.id === connection.target);
      if (!sourceNode || !targetNode) return null;

      const x1 = sourceNode.x;
      const y1 = sourceNode.y;
      const x2 = targetNode.x;
      const y2 = targetNode.y;

      const wave = waveOffsets[index] || { amplitude: 0.5, frequency: 1, phase: 0, speed: 1 };
      
      const dx = x2 - x1;
      const dy = y2 - y1;
      const len = Math.sqrt(dx * dx + dy * dy);
      const nx = -dy / len;
      const ny = dx / len;

      const waveOffset = Math.sin(time * wave.speed + wave.phase) * wave.amplitude;
      
      // Interpolate along the path with wave influence
      const t = progress;
      const baseX = x1 + dx * t;
      const baseY = y1 + dy * t;
      
      // Wave influence varies along the path (strongest in middle)
      const waveInfluence = Math.sin(t * Math.PI) * waveOffset;
      
      return {
        x: baseX + nx * waveInfluence,
        y: baseY + ny * waveInfluence,
      };
    },
    [nodes, waveOffsets, time]
  );

  // Handle node dragging
  const handleNodeMouseDown = useCallback((e: React.MouseEvent, nodeId: string) => {
    e.stopPropagation();
    const node = nodes.find((n) => n.id === nodeId);
    if (!node || !canvasRef.current) return;

    const rect = canvasRef.current.getBoundingClientRect();
    setDragging(nodeId);
    setDragOffset({
      x: (e.clientX - rect.left) / zoom - (node.x / 100) * rect.width,
      y: (e.clientY - rect.top) / zoom - (node.y / 100) * rect.height,
    });
  }, [nodes, zoom]);

  const handleMouseMove = useCallback((e: React.MouseEvent) => {
    // Update mouse position for glow effect
    if (canvasRef.current) {
      const rect = canvasRef.current.getBoundingClientRect();
      const mouseX = ((e.clientX - rect.left) / rect.width) * 100;
      const mouseY = ((e.clientY - rect.top) / rect.height) * 100;
      setMousePos({ x: mouseX, y: mouseY });
      
      // Update CSS custom properties for glow effect
      if (glowRef.current) {
        glowRef.current.style.setProperty('--mouse-x', `${mouseX}%`);
        glowRef.current.style.setProperty('--mouse-y', `${mouseY}%`);
      }
    }
    
    if (dragging && canvasRef.current) {
      const rect = canvasRef.current.getBoundingClientRect();
      const newX = (((e.clientX - rect.left) / zoom - dragOffset.x) / rect.width) * 100;
      const newY = (((e.clientY - rect.top) / zoom - dragOffset.y) / rect.height) * 100;

      setNodes((prev) =>
        prev.map((node) =>
          node.id === dragging
            ? { ...node, x: Math.max(5, Math.min(95, newX)), y: Math.max(5, Math.min(95, newY)) }
            : node
        )
      );
    } else if (isPanning) {
      const dx = e.clientX - lastPanPoint.x;
      const dy = e.clientY - lastPanPoint.y;
      setPan((prev) => ({ x: prev.x + dx, y: prev.y + dy }));
      setLastPanPoint({ x: e.clientX, y: e.clientY });
    }
  }, [dragging, dragOffset, zoom, isPanning, lastPanPoint]);

  const handleMouseUp = useCallback(() => {
    setDragging(null);
    setIsPanning(false);
  }, []);

  const handleCanvasMouseDown = useCallback((e: React.MouseEvent) => {
    if (e.target === canvasRef.current || e.target === svgRef.current) {
      setIsPanning(true);
      setLastPanPoint({ x: e.clientX, y: e.clientY });
    }
  }, []);

  const handleNodeClick = useCallback((node: TopologyNode) => {
    setSelectedNode(node);
    onNodeClick?.(node);
  }, [onNodeClick]);

  const handleZoomIn = () => setZoom((z) => Math.min(2, z + 0.1));
  const handleZoomOut = () => setZoom((z) => Math.max(0.5, z - 0.1));
  const handleResetView = () => {
    setZoom(1);
    setPan({ x: 0, y: 0 });
  };

  // Memoize particles rendering data
  const particleRenderData = useMemo(() => {
    return particles.map((particle) => {
      const conn = connections[particle.connectionIndex];
      if (!conn || !conn.active) return null;
      const point = getPointOnPath(conn, particle.connectionIndex, particle.progress);
      if (!point) return null;
      return {
        ...particle,
        x: point.x,
        y: point.y,
        color: getParticleColor(conn.type),
      };
    }).filter(Boolean);
  }, [particles, connections, getPointOnPath]);

  return (
    <div className="flex h-full flex-col">
      {/* Top Bar */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-gray-800 bg-[#1E293B] px-3 sm:px-6 py-2 sm:py-3">
        <div className="flex flex-wrap items-center gap-2 sm:gap-4">
          <h2 className="text-sm sm:text-lg font-semibold">Agent Topology</h2>
          <div className="flex items-center gap-2 sm:gap-4 text-xs">
            <label className="flex items-center gap-1.5 cursor-pointer">
              <input
                type="checkbox"
                checked={showTraffic}
                onChange={(e) => setShowTraffic(e.target.checked)}
                className="h-3 w-3 rounded border-gray-600 bg-gray-700 text-purple-500 focus:ring-purple-500"
              />
              <span className="text-gray-400">Data Flow</span>
            </label>
            <label className="flex items-center gap-1.5 cursor-pointer">
              <input
                type="checkbox"
                checked={showLabels}
                onChange={(e) => setShowLabels(e.target.checked)}
                className="h-3 w-3 rounded border-gray-600 bg-gray-700 text-purple-500 focus:ring-purple-500"
              />
              <span className="text-gray-400">Labels</span>
            </label>
          </div>
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={() => setIsAnimating(!isAnimating)}
            className={`rounded p-1.5 transition-colors ${
              isAnimating ? "bg-purple-600 text-white" : "bg-gray-700 text-gray-400 hover:text-white"
            }`}
            title={isAnimating ? "Pause" : "Play"}
          >
            {isAnimating ? <Pause className="h-3.5 w-3.5" /> : <Play className="h-3.5 w-3.5" />}
          </button>
          <button onClick={handleZoomOut} className="rounded p-1.5 hover:bg-gray-700 text-gray-400 hover:text-white">
            <ZoomOut className="h-3.5 w-3.5" />
          </button>
          <span className="min-w-[40px] text-center text-xs text-gray-400">{Math.round(zoom * 100)}%</span>
          <button onClick={handleZoomIn} className="rounded p-1.5 hover:bg-gray-700 text-gray-400 hover:text-white">
            <ZoomIn className="h-3.5 w-3.5" />
          </button>
          <button onClick={handleResetView} className="rounded p-1.5 hover:bg-gray-700 text-gray-400 hover:text-white">
            <RotateCcw className="h-3.5 w-3.5" />
          </button>
          <button className="rounded p-1.5 hover:bg-gray-700 text-gray-400 hover:text-white">
            <Maximize2 className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>

      {/* Main Canvas */}
      <div
        ref={canvasRef}
        className="relative flex-1 overflow-hidden bg-[#0a0f1a] cursor-grab active:cursor-grabbing"
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
        onMouseDown={handleCanvasMouseDown}
      >
        {/* Animated star field background */}
        <div 
          className="absolute inset-0 topology-starfield"
          style={{
            transform: `scale(${zoom}) translate(${pan.x / zoom}px, ${pan.y / zoom}px)`,
            transformOrigin: "0 0",
          }}
        />
        
        {/* Mouse-reactive glow overlay */}
        <div 
          ref={glowRef}
          className="mouse-glow-overlay"
          style={{
            '--mouse-x': `${mousePos.x}%`,
            '--mouse-y': `${mousePos.y}%`,
          } as React.CSSProperties}
        />
        
        {/* Subtle grid background */}
        <div
          className="absolute inset-0 opacity-10"
          style={{
            backgroundImage: "radial-gradient(circle, #1e293b 1px, transparent 1px)",
            backgroundSize: "40px 40px",
            transform: `scale(${zoom}) translate(${pan.x / zoom}px, ${pan.y / zoom}px)`,
            transformOrigin: "0 0",
          }}
        />

        {/* SVG Layer for connections and particles */}
        <svg
          ref={svgRef}
          className="absolute inset-0 w-full h-full pointer-events-none"
          style={{
            transform: `scale(${zoom}) translate(${pan.x / zoom}px, ${pan.y / zoom}px)`,
            transformOrigin: "0 0",
          }}
          viewBox="0 0 100 100"
          preserveAspectRatio="none"
        >
          <defs>
            {/* Subtle glow filter */}
            <filter id="particleGlow" x="-100%" y="-100%" width="300%" height="300%">
              <feGaussianBlur stdDeviation="0.15" result="blur" />
              <feMerge>
                <feMergeNode in="blur" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>
          </defs>

          {/* Organic connection lines (mycelium-like) */}
          {connections.map((connection, index) => {
            const sourceNode = nodes.find((n) => n.id === connection.source);
            const targetNode = nodes.find((n) => n.id === connection.target);
            if (!sourceNode || !targetNode) return null;

            const color = getConnectionColor(connection.type, connection.active);
            const path = getOrganicPath(connection, index);
            
            return (
              <g key={`${connection.source}-${connection.target}-${index}`}>
                {/* Soft glow behind line */}
                {connection.active && (
                  <path
                    d={path}
                    stroke={color}
                    strokeWidth="0.15"
                    fill="none"
                    opacity="0.2"
                    filter="url(#particleGlow)"
                  />
                )}
                
                {/* Main organic line */}
                <path
                  d={path}
                  stroke={color}
                  strokeWidth="0.08"
                  fill="none"
                  strokeDasharray={connection.active ? "none" : "0.5,0.5"}
                  opacity={connection.active ? 0.5 : 0.2}
                  strokeLinecap="round"
                />
              </g>
            );
          })}

          {/* Tiny particles flowing through connections */}
          {showTraffic && particleRenderData.map((particle) => {
            if (!particle) return null;
            return (
              <g key={particle.id}>
                {/* Tiny particle with subtle glow */}
                <circle
                  cx={particle.x}
                  cy={particle.y}
                  r={particle.size * 0.6}
                  fill={particle.color}
                  opacity={particle.opacity * 0.3}
                  filter="url(#particleGlow)"
                />
                {/* Particle core */}
                <circle
                  cx={particle.x}
                  cy={particle.y}
                  r={particle.size * 0.3}
                  fill={particle.color}
                  opacity={particle.opacity}
                />
                {/* Bright center */}
                <circle
                  cx={particle.x}
                  cy={particle.y}
                  r={particle.size * 0.15}
                  fill="white"
                  opacity={particle.opacity * 0.6}
                />
              </g>
            );
          })}
        </svg>

        {/* Nodes Layer */}
        <div
          className="absolute inset-0 w-full h-full"
          style={{
            transform: `scale(${zoom}) translate(${pan.x / zoom}px, ${pan.y / zoom}px)`,
            transformOrigin: "0 0",
          }}
        >
          {nodes.map((node) => (
            <div
              key={node.id}
              className={`absolute cursor-pointer transition-transform duration-150 ${
                selectedNode?.id === node.id ? "z-20" : "z-10"
              } ${dragging === node.id ? "cursor-grabbing scale-105" : "cursor-grab hover:scale-105"}`}
              style={{
                left: `${node.x}%`,
                top: `${node.y}%`,
                transform: "translate(-50%, -50%)",
              }}
              onMouseDown={(e) => handleNodeMouseDown(e, node.id)}
              onClick={() => handleNodeClick(node)}
            >
              <div className="relative flex flex-col items-center">
                {/* Selection indicator */}
                {selectedNode?.id === node.id && (
                  <div className="absolute inset-0 -m-2 rounded-full border border-blue-400 animate-pulse" />
                )}
                
                {/* Node container - smaller sizes */}
                <div
                  className={`flex items-center justify-center rounded-lg p-1.5 shadow-md transition-all backdrop-blur-sm ${
                    node.type === "orchestrator"
                      ? "bg-gradient-to-br from-purple-500/30 to-blue-600/30 border border-purple-500/70 w-12 h-12"
                      : node.type === "internet"
                      ? "bg-gradient-to-br from-cyan-500/20 to-blue-600/20 border border-cyan-500/40 rounded-full w-10 h-10"
                      : node.type === "person"
                      ? "bg-gradient-to-br from-green-500/20 to-emerald-600/20 border border-green-500/40 rounded-full w-9 h-9"
                      : "bg-[#1E293B]/70 border border-gray-600/50 w-9 h-9"
                  } ${
                    node.status === "online" || node.status === "active"
                      ? "shadow-sm"
                      : "opacity-50"
                  }`}
                >
                  {getNodeIcon(node.type, node.status)}
                </div>
                
                {/* Status dot */}
                <div
                  className={`absolute -bottom-0.5 -right-0.5 w-2 h-2 rounded-full border border-[#0a0f1a] ${
                    node.status === "online" || node.status === "active"
                      ? "bg-green-500"
                      : node.status === "idle"
                      ? "bg-yellow-500"
                      : "bg-gray-500"
                  }`}
                />
                
                {/* Node label */}
                {showLabels && (
                  <div className="mt-1 text-center">
                    <div className="text-[8px] font-medium text-white/80 max-w-[60px] truncate">
                      {node.name}
                    </div>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>

        {/* Compact Legend */}
        <div className="absolute bottom-2 left-2 rounded bg-[#1E293B]/90 p-2 text-[9px] backdrop-blur-sm border border-gray-700/50">
          <div className="font-medium text-white mb-1">Data Flow</div>
          <div className="flex flex-wrap gap-x-2 gap-y-0.5">
            <span className="flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-blue-400" />
              <span className="text-gray-400">Data</span>
            </span>
            <span className="flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-purple-400" />
              <span className="text-gray-400">Control</span>
            </span>
            <span className="flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-green-400" />
              <span className="text-gray-400">Command</span>
            </span>
            <span className="flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-pink-400" />
              <span className="text-gray-400">Transaction</span>
            </span>
          </div>
        </div>

        {/* Selected node details */}
        {selectedNode && (
          <div className="absolute top-2 right-2 w-48 rounded bg-[#1E293B]/95 p-2 backdrop-blur-sm border border-gray-700/50 text-xs">
            <div className="flex items-center justify-between mb-2">
              <span className="font-medium text-white truncate">{selectedNode.name}</span>
              <button onClick={() => setSelectedNode(null)} className="text-gray-400 hover:text-white">×</button>
            </div>
            <div className="space-y-1 text-[10px]">
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
      </div>
    </div>
  );
}
