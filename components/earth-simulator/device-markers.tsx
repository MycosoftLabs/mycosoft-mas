"use client";

import { useEffect, useState, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";

interface DeviceMarkersProps {
  zoom: number;
}

export function DeviceMarkers({ zoom }: DeviceMarkersProps) {
  const [devices, setDevices] = useState<any[]>([]);
  const groupRef = useRef<THREE.Group>(null);

  useEffect(() => {
    const fetchDevices = async () => {
      try {
        const response = await fetch("/api/earth-simulator/devices");
        const data = await response.json();
        if (data.success) {
          setDevices(data.devices || []);
        }
      } catch (error) {
        console.error("Error fetching devices:", error);
      }
    };

    fetchDevices();
    const interval = setInterval(fetchDevices, 30000); // Update every 30 seconds
    return () => clearInterval(interval);
  }, []);

  // Convert lat/lon to 3D position on sphere
  const latLonToPosition = (lat: number, lon: number, radius: number = 1.005): [number, number, number] => {
    const phi = (90 - lat) * (Math.PI / 180);
    const theta = (lon + 180) * (Math.PI / 180);
    const x = -(radius * Math.sin(phi) * Math.cos(theta));
    const z = radius * Math.sin(phi) * Math.sin(theta);
    const y = radius * Math.cos(phi);
    return [x, y, z];
  };

  if (devices.length === 0) {
    return null;
  }

  return (
    <group ref={groupRef}>
      {devices
        .filter((device) => device.location && device.location.lat && device.location.lon)
        .map((device) => {
          const [x, y, z] = latLonToPosition(device.location.lat, device.location.lon);
          const color = device.status === "connected" ? 0x00ff00 : 0xff0000;
          
          return (
            <mesh key={device.id} position={[x, y, z]}>
              <sphereGeometry args={[0.015, 8, 8]} />
              <meshStandardMaterial color={color} emissive={color} emissiveIntensity={0.5} />
            </mesh>
          );
        })}
    </group>
  );
}
