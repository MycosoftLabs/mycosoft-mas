"use client";

import { useMemo, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";
import { shaderMaterial } from "@react-three/drei";
import { extend } from "@react-three/fiber";
import { gridFragmentShader, vertexShader } from "@/lib/earth-simulator/shaders";

// Create grid material
const GridMaterial = shaderMaterial(
  {
    gridColor: new THREE.Color(0x00ff00),
    gridOpacity: 0.3,
    gridSize: 10.0,
  },
  vertexShader,
  gridFragmentShader
);

extend({ GridMaterial });

declare global {
  namespace JSX {
    interface IntrinsicElements {
      gridMaterial: any;
    }
  }
}

interface GridOverlayProps {
  zoom: number;
  onCellClick?: (cellId: string, lat: number, lon: number) => void;
}

export function GridOverlay({ zoom, onCellClick }: GridOverlayProps) {
  const gridRef = useRef<THREE.Mesh>(null);
  
  // Only show grid when zoomed in enough (zoom > 10)
  const showGrid = zoom > 10;
  
  // Calculate grid density based on zoom
  const gridSize = useMemo(() => {
    if (zoom <= 10) return 0;
    // More grid lines as we zoom in
    return Math.min(100, Math.pow(2, zoom - 10));
  }, [zoom]);

  useFrame(() => {
    if (gridRef.current && showGrid) {
      // Update grid material properties
      const material = gridRef.current.material as any;
      if (material) {
        material.uniforms.gridSize.value = gridSize;
        material.uniforms.gridOpacity.value = Math.min(0.5, (zoom - 10) / 10);
      }
    }
  });

  if (!showGrid) {
    return null;
  }

  return (
    <mesh ref={gridRef} rotation={[0, 0, 0]}>
      <sphereGeometry args={[1.001, 64, 64]} />
      <gridMaterial
        gridColor={new THREE.Color(0x00ff00)}
        gridOpacity={0.3}
        gridSize={gridSize}
        transparent
        side={THREE.DoubleSide}
      />
    </mesh>
  );
}
