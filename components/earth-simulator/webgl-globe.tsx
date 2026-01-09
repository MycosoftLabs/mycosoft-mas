"use client";

import { useRef, useState, useEffect } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { OrbitControls, PerspectiveCamera, Stars } from "@react-three/drei";
import * as THREE from "three";
import { GridOverlay } from "./grid-overlay";
import { LayerManager } from "./layer-manager";

interface WebGLGlobeProps {
  onCellClick?: (cellId: string, lat: number, lon: number) => void;
  onViewportChange?: (viewport: { north: number; south: number; east: number; west: number }) => void;
  layers?: {
    mycelium: boolean;
    heat: boolean;
    organisms: boolean;
    weather: boolean;
  };
}

function Globe({ onViewportChange }: { onViewportChange?: (viewport: { north: number; south: number; east: number; west: number }) => void }) {
  const globeRef = useRef<THREE.Mesh>(null);
  const [rotation, setRotation] = useState({ x: 0, y: 0 });

  useFrame(() => {
    if (globeRef.current) {
      globeRef.current.rotation.y += 0.001; // Slow rotation
    }
  });

  return (
    <>
      <mesh ref={globeRef}>
        <sphereGeometry args={[1, 64, 64]} />
        <meshStandardMaterial
          color="#1a4d80"
          roughness={0.8}
          metalness={0.2}
        />
      </mesh>
      <Stars radius={300} depth={50} count={5000} factor={4} fade speed={1} />
    </>
  );
}

export function WebGLGlobe({ onCellClick, onViewportChange, layers }: WebGLGlobeProps) {
  const controlsRef = useRef<any>(null);
  const [zoom, setZoom] = useState(2);
  const [viewport, setViewport] = useState<{ north: number; south: number; east: number; west: number } | null>(null);

  useEffect(() => {
    if (onViewportChange && viewport) {
      onViewportChange(viewport);
    }
  }, [viewport, onViewportChange]);

  return (
    <div className="w-full h-full relative">
      <Canvas
        gl={{ antialias: true, alpha: true }}
        camera={{ position: [0, 0, 3], fov: 50 }}
        onCreated={(state) => {
          state.gl.setClearColor("#000000", 0);
        }}
      >
        <PerspectiveCamera makeDefault position={[0, 0, 3]} fov={50} />
        <ambientLight intensity={0.5} />
        <directionalLight position={[5, 5, 5]} intensity={1} />
        <pointLight position={[-5, -5, -5]} intensity={0.5} />
        
        <Globe onViewportChange={setViewport} />
        
        <GridOverlay zoom={zoom} onCellClick={onCellClick} />
        <LayerManager zoom={zoom} viewport={viewport || undefined} layers={layers} />
        
        <OrbitControls
          ref={controlsRef}
          enablePan={true}
          enableZoom={true}
          enableRotate={true}
          minDistance={1.5}
          maxDistance={10}
          onChange={(e) => {
            if (e?.target) {
              const distance = e.target.getDistance();
              const newZoom = Math.max(1, Math.min(20, Math.round(20 - distance * 2)));
              if (newZoom !== zoom) {
                setZoom(newZoom);
              }
            }
          }}
        />
      </Canvas>
    </div>
  );
}
