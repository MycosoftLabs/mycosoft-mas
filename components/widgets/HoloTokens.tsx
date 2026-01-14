"use client";

/**
 * Holographic token particles for cinematic dashboard
 * Uses GPU instancing for performance with 1000+ particles
 */

import * as THREE from "three";
import { useMemo, useRef } from "react";
import { useFrame, invalidate } from "@react-three/fiber";

interface HoloTokensProps {
  count?: number;
  color?: string;
  secondaryColor?: string;
}

export function HoloTokens({
  count = 800,
  color = "#00d4ff",
  secondaryColor = "#7fffcc",
}: HoloTokensProps) {
  const meshRef = useRef<THREE.InstancedMesh>(null!);
  const dummy = useMemo(() => new THREE.Object3D(), []);

  // Pre-compute initial positions and properties
  const particles = useMemo(() => {
    return Array.from({ length: count }, (_, i) => ({
      angle: (i / count) * Math.PI * 2,
      radius: 1.5 + (i % 50) * 0.03,
      y: ((i % 20) - 10) * 0.08,
      speed: 0.02 + Math.random() * 0.03,
      scale: 0.4 + Math.random() * 0.6,
      phase: Math.random() * Math.PI * 2,
    }));
  }, [count]);

  // Create shader material for holographic effect
  const material = useMemo(() => {
    return new THREE.ShaderMaterial({
      uniforms: {
        uTime: { value: 0 },
        uColor: { value: new THREE.Color(color) },
        uSecondaryColor: { value: new THREE.Color(secondaryColor) },
      },
      vertexShader: `
        varying vec2 vUv;
        varying float vDepth;
        
        void main() {
          vUv = uv;
          vec4 mvPosition = modelViewMatrix * instanceMatrix * vec4(position, 1.0);
          vDepth = -mvPosition.z;
          gl_Position = projectionMatrix * mvPosition;
        }
      `,
      fragmentShader: `
        uniform float uTime;
        uniform vec3 uColor;
        uniform vec3 uSecondaryColor;
        varying vec2 vUv;
        varying float vDepth;
        
        void main() {
          // Circular gradient from center
          float dist = length(vUv - 0.5) * 2.0;
          float alpha = 1.0 - smoothstep(0.0, 1.0, dist);
          
          // Scanline effect
          float scanline = 0.5 + 0.5 * sin(vUv.y * 40.0 + uTime * 3.0);
          
          // Color mixing based on depth and time
          float colorMix = 0.5 + 0.5 * sin(uTime * 0.5 + vDepth * 0.1);
          vec3 finalColor = mix(uColor, uSecondaryColor, colorMix * scanline);
          
          // Glow at edges
          float glow = smoothstep(0.6, 0.8, dist) * 0.5;
          finalColor += glow * uSecondaryColor;
          
          gl_FragColor = vec4(finalColor, alpha * 0.85);
        }
      `,
      transparent: true,
      depthWrite: false,
      blending: THREE.AdditiveBlending,
    });
  }, [color, secondaryColor]);

  // Animation loop - updates positions and time uniform
  useFrame((state) => {
    const time = state.clock.getElapsedTime();
    material.uniforms.uTime.value = time;

    particles.forEach((p, i) => {
      const angle = p.angle + time * p.speed;
      const wobble = Math.sin(time * 2 + p.phase) * 0.05;

      dummy.position.set(
        Math.cos(angle) * (p.radius + wobble),
        p.y + Math.sin(time + p.phase) * 0.1,
        Math.sin(angle) * (p.radius + wobble)
      );
      dummy.rotation.y = angle + time * 0.1;
      dummy.scale.setScalar(p.scale * (0.8 + 0.2 * Math.sin(time * 2 + p.phase)));
      dummy.updateMatrix();
      meshRef.current.setMatrixAt(i, dummy.matrix);
    });

    meshRef.current.instanceMatrix.needsUpdate = true;
    invalidate(); // Trigger render for demand mode
  });

  const geometry = useMemo(() => new THREE.CircleGeometry(0.06, 16), []);

  return (
    <instancedMesh
      ref={meshRef}
      args={[geometry, material, count]}
      frustumCulled={false}
    />
  );
}
