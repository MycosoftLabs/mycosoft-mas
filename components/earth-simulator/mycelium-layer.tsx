"use client";

import { useMemo, useEffect, useState } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";
import { shaderMaterial } from "@react-three/drei";
import { extend } from "@react-three/fiber";
import { myceliumFragmentShader, vertexShader } from "@/lib/earth-simulator/shaders";

const MyceliumMaterial = shaderMaterial(
  {
    probability: 0.0,
    opacity: 0.6,
    highColor: new THREE.Color(1.0, 0.2, 0.0), // Red/orange
    lowColor: new THREE.Color(0.0, 1.0, 0.0), // Green
    noDataColor: new THREE.Color(0.3, 0.3, 0.3), // Gray
  },
  vertexShader,
  myceliumFragmentShader
);

extend({ MyceliumMaterial });

declare global {
  namespace JSX {
    interface IntrinsicElements {
      myceliumMaterial: any;
    }
  }
}

interface MyceliumLayerProps {
  zoom: number;
  viewport?: { north: number; south: number; east: number; west: number };
}

export function MyceliumLayer({ zoom, viewport }: MyceliumLayerProps) {
  const [probabilities, setProbabilities] = useState<Map<string, number>>(new Map());
  const meshRef = useRef<THREE.Mesh>(null);

  useEffect(() => {
    if (!viewport || zoom < 10) return;

    // Fetch probability data for visible cells
    const fetchProbabilities = async () => {
      try {
        const response = await fetch(
          `/api/earth-simulator/grid?lat=${(viewport.north + viewport.south) / 2}&lon=${(viewport.east + viewport.west) / 2}&zoom=${zoom}&width=1920&height=1080`
        );
        const data = await response.json();
        
        if (data.success && data.gridCells) {
          // Fetch probabilities for each cell
          const cellPromises = data.gridCells.slice(0, 100).map(async (cell: any) => {
            try {
              const probResponse = await fetch(
                `/api/earth-simulator/mycelium-probability?lat=${cell.centerLat}&lon=${cell.centerLon}&zoom=${zoom}`
              );
              const probData = await probResponse.json();
              if (probData.success) {
                return { cellId: cell.id, probability: probData.probability };
              }
            } catch (error) {
              console.error("Error fetching probability:", error);
            }
            return null;
          });

          const results = await Promise.all(cellPromises);
          const newProbabilities = new Map<string, number>();
          results.forEach((result) => {
            if (result) {
              newProbabilities.set(result.cellId, result.probability);
            }
          });
          setProbabilities(newProbabilities);
        }
      } catch (error) {
        console.error("Error fetching grid cells:", error);
      }
    };

    fetchProbabilities();
  }, [viewport, zoom]);

  // For now, render a simple overlay
  // In production, this would render individual grid cells with their probabilities
  return (
    <mesh ref={meshRef} rotation={[0, 0, 0]}>
      <sphereGeometry args={[1.002, 64, 64]} />
      <myceliumMaterial
        probability={0.5} // Average probability for demo
        opacity={0.4}
        transparent
        side={THREE.DoubleSide}
      />
    </mesh>
  );
}
