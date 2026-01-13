"use client";

/**
 * Earth Simulator Component
 * Interactive 3D globe with weather, geological, and biological layers
 * Integrates with NatureOS API
 */

import React, { useRef, useEffect, useState, Suspense } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { OrbitControls, Sphere, Html, useTexture } from "@react-three/drei";
import * as THREE from "three";

// Types
interface WeatherData {
  location: { lat: number; lng: number };
  temperature: number;
  humidity: number;
  windSpeed: number;
  conditions: string;
}

interface GeoEvent {
  id: string;
  type: "earthquake" | "volcano" | "storm";
  location: { lat: number; lng: number };
  magnitude?: number;
  timestamp: string;
}

interface BiologicalMarker {
  id: string;
  species: string;
  location: { lat: number; lng: number };
  population?: number;
  status: "stable" | "endangered" | "thriving";
}

interface EarthSimulatorProps {
  apiUrl?: string;
  showWeather?: boolean;
  showGeo?: boolean;
  showBio?: boolean;
  onLocationSelect?: (lat: number, lng: number) => void;
}

// Earth Globe Component
function EarthGlobe({ 
  weatherData, 
  geoEvents, 
  bioMarkers,
  onLocationClick 
}: {
  weatherData: WeatherData[];
  geoEvents: GeoEvent[];
  bioMarkers: BiologicalMarker[];
  onLocationClick?: (lat: number, lng: number) => void;
}) {
  const meshRef = useRef<THREE.Mesh>(null);
  const cloudsRef = useRef<THREE.Mesh>(null);
  
  // Rotation animation
  useFrame((state, delta) => {
    if (meshRef.current) {
      meshRef.current.rotation.y += delta * 0.05;
    }
    if (cloudsRef.current) {
      cloudsRef.current.rotation.y += delta * 0.06;
    }
  });

  // Convert lat/lng to 3D position
  const latLngToVector3 = (lat: number, lng: number, radius: number = 2.05) => {
    const phi = (90 - lat) * (Math.PI / 180);
    const theta = (lng + 180) * (Math.PI / 180);
    return new THREE.Vector3(
      -radius * Math.sin(phi) * Math.cos(theta),
      radius * Math.cos(phi),
      radius * Math.sin(phi) * Math.sin(theta)
    );
  };

  return (
    <group>
      {/* Earth */}
      <Sphere ref={meshRef} args={[2, 64, 64]}>
        <meshStandardMaterial
          color="#1a4d7c"
          roughness={0.8}
          metalness={0.2}
        />
      </Sphere>

      {/* Clouds layer */}
      <Sphere ref={cloudsRef} args={[2.02, 64, 64]}>
        <meshStandardMaterial
          color="#ffffff"
          transparent
          opacity={0.3}
        />
      </Sphere>

      {/* Atmosphere glow */}
      <Sphere args={[2.1, 64, 64]}>
        <meshBasicMaterial
          color="#4da6ff"
          transparent
          opacity={0.1}
          side={THREE.BackSide}
        />
      </Sphere>

      {/* Geo Events */}
      {geoEvents.map((event) => {
        const pos = latLngToVector3(event.location.lat, event.location.lng);
        const color = event.type === "earthquake" ? "#ff4444" 
                    : event.type === "volcano" ? "#ff8800" 
                    : "#4488ff";
        return (
          <mesh key={event.id} position={pos}>
            <sphereGeometry args={[0.03 + (event.magnitude || 1) * 0.01, 16, 16]} />
            <meshBasicMaterial color={color} />
          </mesh>
        );
      })}

      {/* Biological Markers */}
      {bioMarkers.map((marker) => {
        const pos = latLngToVector3(marker.location.lat, marker.location.lng);
        const color = marker.status === "endangered" ? "#ff4444" 
                    : marker.status === "thriving" ? "#44ff44" 
                    : "#ffff44";
        return (
          <mesh key={marker.id} position={pos}>
            <sphereGeometry args={[0.02, 8, 8]} />
            <meshBasicMaterial color={color} />
          </mesh>
        );
      })}
    </group>
  );
}

// Loading fallback
function LoadingFallback() {
  return (
    <Html center>
      <div className="text-white text-lg animate-pulse">
        Loading Earth Simulator...
      </div>
    </Html>
  );
}

// Main Earth Simulator Component
export function EarthSimulator({
  apiUrl = "/api/natureos",
  showWeather = true,
  showGeo = true,
  showBio = true,
  onLocationSelect,
}: EarthSimulatorProps) {
  const [weatherData, setWeatherData] = useState<WeatherData[]>([]);
  const [geoEvents, setGeoEvents] = useState<GeoEvent[]>([]);
  const [bioMarkers, setBioMarkers] = useState<BiologicalMarker[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedLayer, setSelectedLayer] = useState<"weather" | "geo" | "bio">("geo");

  // Fetch data from NatureOS API
  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        
        // Fetch all layers in parallel
        const [weatherRes, geoRes, bioRes] = await Promise.all([
          showWeather ? fetch(`${apiUrl}/weather/global`).catch(() => null) : null,
          showGeo ? fetch(`${apiUrl}/events/geological`).catch(() => null) : null,
          showBio ? fetch(`${apiUrl}/species/distribution`).catch(() => null) : null,
        ]);

        if (weatherRes?.ok) {
          const data = await weatherRes.json();
          setWeatherData(data.locations || []);
        }
        
        if (geoRes?.ok) {
          const data = await geoRes.json();
          setGeoEvents(data.events || []);
        }
        
        if (bioRes?.ok) {
          const data = await bioRes.json();
          setBioMarkers(data.markers || []);
        }

        setLoading(false);
      } catch (err) {
        setError("Failed to load Earth data");
        setLoading(false);
        
        // Load sample data for demo
        setGeoEvents([
          { id: "eq1", type: "earthquake", location: { lat: 35.6, lng: 139.7 }, magnitude: 4.2, timestamp: new Date().toISOString() },
          { id: "eq2", type: "earthquake", location: { lat: 37.5, lng: -122.4 }, magnitude: 3.1, timestamp: new Date().toISOString() },
          { id: "v1", type: "volcano", location: { lat: 19.4, lng: -155.3 }, magnitude: 2.0, timestamp: new Date().toISOString() },
        ]);
        setBioMarkers([
          { id: "b1", species: "Amanita muscaria", location: { lat: 52.5, lng: 13.4 }, status: "stable" },
          { id: "b2", species: "Ganoderma lucidum", location: { lat: 35.0, lng: 135.0 }, status: "thriving" },
          { id: "b3", species: "Ophiocordyceps", location: { lat: -3.0, lng: -60.0 }, status: "endangered" },
        ]);
      }
    };

    fetchData();
    
    // Refresh every 5 minutes
    const interval = setInterval(fetchData, 5 * 60 * 1000);
    return () => clearInterval(interval);
  }, [apiUrl, showWeather, showGeo, showBio]);

  return (
    <div className="relative w-full h-[600px] bg-gradient-to-b from-slate-900 to-slate-950 rounded-lg overflow-hidden">
      {/* Layer Controls */}
      <div className="absolute top-4 left-4 z-10 flex gap-2">
        <button
          onClick={() => setSelectedLayer("weather")}
          className={`px-3 py-1.5 rounded text-sm font-medium transition-colors ${
            selectedLayer === "weather" 
              ? "bg-blue-600 text-white" 
              : "bg-slate-800 text-slate-300 hover:bg-slate-700"
          }`}
        >
          Weather
        </button>
        <button
          onClick={() => setSelectedLayer("geo")}
          className={`px-3 py-1.5 rounded text-sm font-medium transition-colors ${
            selectedLayer === "geo" 
              ? "bg-red-600 text-white" 
              : "bg-slate-800 text-slate-300 hover:bg-slate-700"
          }`}
        >
          Geological
        </button>
        <button
          onClick={() => setSelectedLayer("bio")}
          className={`px-3 py-1.5 rounded text-sm font-medium transition-colors ${
            selectedLayer === "bio" 
              ? "bg-green-600 text-white" 
              : "bg-slate-800 text-slate-300 hover:bg-slate-700"
          }`}
        >
          Biological
        </button>
      </div>

      {/* Stats Panel */}
      <div className="absolute top-4 right-4 z-10 bg-slate-800/80 backdrop-blur-sm rounded-lg p-3 text-sm">
        <div className="text-slate-400">Active Events</div>
        <div className="flex gap-4 mt-1">
          <div className="text-center">
            <div className="text-red-400 font-bold">{geoEvents.filter(e => e.type === "earthquake").length}</div>
            <div className="text-xs text-slate-500">Earthquakes</div>
          </div>
          <div className="text-center">
            <div className="text-orange-400 font-bold">{geoEvents.filter(e => e.type === "volcano").length}</div>
            <div className="text-xs text-slate-500">Volcanoes</div>
          </div>
          <div className="text-center">
            <div className="text-green-400 font-bold">{bioMarkers.length}</div>
            <div className="text-xs text-slate-500">Species</div>
          </div>
        </div>
      </div>

      {/* 3D Globe Canvas */}
      <Canvas camera={{ position: [0, 0, 6], fov: 45 }}>
        <Suspense fallback={<LoadingFallback />}>
          <ambientLight intensity={0.3} />
          <directionalLight position={[5, 3, 5]} intensity={1} />
          <pointLight position={[-5, -3, -5]} intensity={0.3} color="#4da6ff" />
          
          <EarthGlobe
            weatherData={weatherData}
            geoEvents={selectedLayer === "geo" ? geoEvents : []}
            bioMarkers={selectedLayer === "bio" ? bioMarkers : []}
            onLocationClick={onLocationSelect}
          />
          
          <OrbitControls
            enablePan={false}
            minDistance={3}
            maxDistance={10}
            autoRotate={false}
          />
        </Suspense>
      </Canvas>

      {/* Legend */}
      <div className="absolute bottom-4 left-4 z-10 bg-slate-800/80 backdrop-blur-sm rounded-lg p-3 text-xs">
        {selectedLayer === "geo" && (
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-red-500"></div>
              <span className="text-slate-300">Earthquake</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-orange-500"></div>
              <span className="text-slate-300">Volcanic Activity</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-blue-500"></div>
              <span className="text-slate-300">Storm System</span>
            </div>
          </div>
        )}
        {selectedLayer === "bio" && (
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-green-500"></div>
              <span className="text-slate-300">Thriving</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-yellow-500"></div>
              <span className="text-slate-300">Stable</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-red-500"></div>
              <span className="text-slate-300">Endangered</span>
            </div>
          </div>
        )}
      </div>

      {/* Loading Overlay */}
      {loading && (
        <div className="absolute inset-0 bg-slate-900/50 flex items-center justify-center">
          <div className="text-white animate-pulse">Loading Earth data...</div>
        </div>
      )}
    </div>
  );
}

export default EarthSimulator;
