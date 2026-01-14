"use client";

/**
 * Cinematic Dashboard - Jarvis-style 3D visualization
 * 
 * Features:
 * - React Three Fiber with post-processing effects
 * - GPU-instanced holographic particles
 * - On-demand frame loop for power efficiency
 * - Overlay HUD with live metrics
 * 
 * Route: /dashboard/cinematic
 */

import { Suspense, useState, useEffect } from "react";
import { Canvas } from "@react-three/fiber";
import {
  OrbitControls,
  AdaptiveDpr,
  AdaptiveEvents,
  PerspectiveCamera,
  Environment,
  Float,
  Text,
  Ring,
} from "@react-three/drei";
import { EffectsRig } from "@/components/fx/EffectsRig";
import { HoloTokens } from "@/components/widgets/HoloTokens";
import { HUD } from "@/components/widgets/HUD";
import Link from "next/link";
import { ArrowLeft, Maximize2, Minimize2 } from "lucide-react";

// Central holographic core
function HoloCore() {
  return (
    <group>
      {/* Outer rings */}
      <Float speed={1.5} rotationIntensity={0.3} floatIntensity={0.2}>
        <Ring args={[1.8, 1.9, 64]} rotation={[Math.PI / 2, 0, 0]}>
          <meshBasicMaterial color="#00d4ff" transparent opacity={0.4} />
        </Ring>
      </Float>
      <Float speed={2} rotationIntensity={0.5} floatIntensity={0.3}>
        <Ring args={[1.4, 1.5, 64]} rotation={[Math.PI / 2, 0, 0]}>
          <meshBasicMaterial color="#7fffcc" transparent opacity={0.3} />
        </Ring>
      </Float>
      <Float speed={1.2} rotationIntensity={0.2} floatIntensity={0.15}>
        <Ring args={[2.2, 2.25, 64]} rotation={[Math.PI / 2, 0, 0]}>
          <meshBasicMaterial color="#00a8cc" transparent opacity={0.2} />
        </Ring>
      </Float>

      {/* Center sphere */}
      <mesh>
        <sphereGeometry args={[0.3, 32, 32]} />
        <meshStandardMaterial
          color="#001830"
          emissive="#00d4ff"
          emissiveIntensity={0.5}
          metalness={0.9}
          roughness={0.1}
        />
      </mesh>

      {/* Center label */}
      <Text
        position={[0, -0.8, 0]}
        fontSize={0.12}
        color="#7fffcc"
        anchorX="center"
        anchorY="middle"
        font="/fonts/SpaceMono-Bold.ttf"
      >
        MYCOSOFT
      </Text>
    </group>
  );
}

// Scene content
function Scene() {
  return (
    <>
      {/* Lighting */}
      <ambientLight intensity={0.15} />
      <pointLight position={[5, 5, 5]} intensity={0.8} color="#00d4ff" />
      <pointLight position={[-5, -5, -5]} intensity={0.4} color="#7fffcc" />

      {/* Core visualization */}
      <HoloCore />

      {/* Particle systems */}
      <HoloTokens count={600} color="#00d4ff" secondaryColor="#7fffcc" />
      <HoloTokens count={300} color="#ff6b9d" secondaryColor="#c792ea" />

      {/* Post-processing */}
      <EffectsRig />

      {/* Environment for reflections */}
      <Environment preset="night" />
    </>
  );
}

// Loading fallback
function LoadingFallback() {
  return (
    <div className="flex items-center justify-center h-full">
      <div className="text-cyan-400 text-sm font-mono animate-pulse">
        INITIALIZING...
      </div>
    </div>
  );
}

export default function CinematicDashboardPage() {
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  const toggleFullscreen = () => {
    if (!document.fullscreenElement) {
      document.documentElement.requestFullscreen();
      setIsFullscreen(true);
    } else {
      document.exitFullscreen();
      setIsFullscreen(false);
    }
  };

  useEffect(() => {
    const handleFullscreenChange = () => {
      setIsFullscreen(!!document.fullscreenElement);
    };
    document.addEventListener("fullscreenchange", handleFullscreenChange);
    return () =>
      document.removeEventListener("fullscreenchange", handleFullscreenChange);
  }, []);

  if (!mounted) {
    return (
      <div className="min-h-screen bg-[#050810] flex items-center justify-center">
        <LoadingFallback />
      </div>
    );
  }

  return (
    <div className="relative w-full h-screen bg-[#050810] overflow-hidden">
      {/* Navigation controls */}
      <div className="absolute top-4 left-4 z-50 flex items-center gap-3">
        <Link
          href="/natureos"
          className="p-2 rounded-lg bg-black/40 backdrop-blur-sm border border-cyan-500/20 
                     hover:border-cyan-400/40 transition-colors"
        >
          <ArrowLeft className="w-5 h-5 text-cyan-400" />
        </Link>
        <button
          onClick={toggleFullscreen}
          className="p-2 rounded-lg bg-black/40 backdrop-blur-sm border border-cyan-500/20 
                     hover:border-cyan-400/40 transition-colors"
        >
          {isFullscreen ? (
            <Minimize2 className="w-5 h-5 text-cyan-400" />
          ) : (
            <Maximize2 className="w-5 h-5 text-cyan-400" />
          )}
        </button>
      </div>

      {/* 3D Canvas */}
      <Canvas
        gl={{
          antialias: false,
          powerPreference: "high-performance",
          alpha: false,
        }}
        dpr={[1, 1.5]}
        frameloop="demand"
        className="w-full h-full"
      >
        <color attach="background" args={["#050810"]} />
        <fog attach="fog" args={["#050810", 4, 15]} />

        <PerspectiveCamera
          makeDefault
          position={[0, 1.2, 4]}
          fov={50}
          near={0.1}
          far={100}
        />

        <Suspense fallback={null}>
          <Scene />
        </Suspense>

        <OrbitControls
          enableDamping
          dampingFactor={0.05}
          minDistance={2}
          maxDistance={10}
          maxPolarAngle={Math.PI / 1.5}
          minPolarAngle={Math.PI / 4}
        />

        <AdaptiveDpr pixelated />
        <AdaptiveEvents />
      </Canvas>

      {/* HUD Overlay */}
      <HUD
        title="NATUREOS"
        subtitle="Observation & Environmental Intelligence"
      />
    </div>
  );
}
