"use client";

import { useEffect, useState, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";
import { shaderMaterial } from "@react-three/drei";
import { extend } from "@react-three/fiber";
import { organismFragmentShader, vertexShader } from "@/lib/earth-simulator/shaders";

const OrganismMaterial = shaderMaterial(
  {
    organismColor: new THREE.Color(1.0, 0.0, 1.0), // Magenta
    size: 0.1,
    opacity: 0.8,
  },
  vertexShader,
  organismFragmentShader
);

extend({ OrganismMaterial });

declare global {
  namespace JSX {
    interface IntrinsicElements {
      organismMaterial: any;
    }
  }
}

interface OrganismLayerProps {
  zoom: number;
  viewport?: { north: number; south: number; east: number; west: number };
}

export function OrganismLayer({ zoom, viewport }: OrganismLayerProps) {
  const [observations, setObservations] = useState<any[]>([]);
  const groupRef = useRef<THREE.Group>(null);

  useEffect(() => {
    if (!viewport || zoom < 10) return;

    // Fetch iNaturalist observations
    const fetchObservations = async () => {
      try {
        const response = await fetch(
          `/api/earth-simulator/inaturalist?action=bounds&nelat=${viewport.north}&nelng=${viewport.east}&swlat=${viewport.south}&swlng=${viewport.west}&taxon_id=47170&per_page=100`
        );
        const data = await response.json();
        if (data.success) {
          setObservations(data.observations || []);
        }
      } catch (error) {
        console.error("Error fetching observations:", error);
      }
    };

    fetchObservations();
  }, [viewport, zoom]);

  // Convert lat/lon to 3D position on sphere
  const latLonToPosition = (lat: number, lon: number, radius: number = 1.004): [number, number, number] => {
    const phi = (90 - lat) * (Math.PI / 180);
    const theta = (lon + 180) * (Math.PI / 180);
    const x = -(radius * Math.sin(phi) * Math.cos(theta));
    const z = radius * Math.sin(phi) * Math.sin(theta);
    const y = radius * Math.cos(phi);
    return [x, y, z];
  };

  return (
    <group ref={groupRef}>
      {observations.map((obs, index) => {
        const [x, y, z] = latLonToPosition(obs.latitude, obs.longitude);
        return (
          <mesh key={obs.id || index} position={[x, y, z]}>
            <sphereGeometry args={[0.01, 8, 8]} />
            <organismMaterial
              organismColor={new THREE.Color(1.0, 0.0, 1.0)}
              size={0.1}
              opacity={0.8}
              transparent
            />
          </mesh>
        );
      })}
    </group>
  );
}
