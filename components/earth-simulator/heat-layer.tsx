"use client";

import { useRef } from "react";
import * as THREE from "three";
import { shaderMaterial } from "@react-three/drei";
import { extend } from "@react-three/fiber";
import { heatMapFragmentShader, vertexShader } from "@/lib/earth-simulator/shaders";

const HeatMaterial = shaderMaterial(
  {
    temperature: 20.0,
    minTemp: -20.0,
    maxTemp: 50.0,
    opacity: 0.5,
  },
  vertexShader,
  heatMapFragmentShader
);

extend({ HeatMaterial });

declare global {
  namespace JSX {
    interface IntrinsicElements {
      heatMaterial: any;
    }
  }
}

interface HeatLayerProps {
  zoom: number;
  viewport?: { north: number; south: number; east: number; west: number };
}

export function HeatLayer({ zoom, viewport }: HeatLayerProps) {
  const meshRef = useRef<THREE.Mesh>(null);

  // In production, this would fetch temperature data from NASA/NOAA APIs
  // For now, render a placeholder

  return (
    <mesh ref={meshRef} rotation={[0, 0, 0]}>
      <sphereGeometry args={[1.003, 64, 64]} />
      <heatMaterial
        temperature={20.0}
        minTemp={-20.0}
        maxTemp={50.0}
        opacity={0.3}
        transparent
        side={THREE.DoubleSide}
      />
    </mesh>
  );
}
