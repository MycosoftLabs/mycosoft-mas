"use client";

import { useEffect, useRef, useState, useMemo } from "react";

interface ParticleGlobe2DProps {
  size?: number;
  pointCount?: number;
  color?: string;
  orbitCount?: number;
  rotationSpeed?: number;
  opacity?: number;
  className?: string;
}

interface Particle {
  id: number;
  x: number;
  y: number;
  z: number;
  size: number;
  phase: number;
}

interface OrbitRing {
  id: number;
  tilt: number;
  phase: number;
  speed: number;
}

export function ParticleGlobe2D({
  size = 200,
  pointCount = 100,
  color = "#a855f7",
  orbitCount = 3,
  rotationSpeed = 0.5,
  opacity = 0.6,
  className = "",
}: ParticleGlobe2DProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [time, setTime] = useState(0);
  const animationRef = useRef<number>();

  // Generate particles on sphere using Fibonacci lattice
  const particles = useMemo(() => {
    const pts: Particle[] = [];
    const golden = Math.PI * (3 - Math.sqrt(5));
    
    for (let i = 0; i < pointCount; i++) {
      const y = 1 - (i / (pointCount - 1)) * 2;
      const radius = Math.sqrt(1 - y * y);
      const theta = golden * i;
      const x = Math.cos(theta) * radius;
      const z = Math.sin(theta) * radius;
      
      pts.push({
        id: i,
        x,
        y,
        z,
        size: 0.5 + Math.random() * 1.5,
        phase: Math.random() * Math.PI * 2,
      });
    }
    return pts;
  }, [pointCount]);

  // Generate orbit rings
  const orbits = useMemo(() => {
    const rings: OrbitRing[] = [];
    for (let i = 0; i < orbitCount; i++) {
      rings.push({
        id: i,
        tilt: (i * 0.4 + 0.2) * Math.PI * 0.5,
        phase: (i * 0.3) * Math.PI,
        speed: 0.3 + i * 0.15,
      });
    }
    return rings;
  }, [orbitCount]);

  // Parse color to RGB
  const rgb = useMemo(() => {
    const hex = color.replace("#", "");
    return {
      r: parseInt(hex.substring(0, 2), 16),
      g: parseInt(hex.substring(2, 4), 16),
      b: parseInt(hex.substring(4, 6), 16),
    };
  }, [color]);

  // Animation loop
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const radius = size * 0.4;
    const centerX = size / 2;
    const centerY = size / 2;

    const animate = () => {
      setTime((t) => t + 0.016);

      ctx.clearRect(0, 0, size, size);

      // Rotate and project particles
      const rotatedParticles = particles.map((p) => {
        // Rotate around Y axis
        const cosR = Math.cos(time * rotationSpeed);
        const sinR = Math.sin(time * rotationSpeed);
        const x = p.x * cosR - p.z * sinR;
        const z = p.x * sinR + p.z * cosR;
        const y = p.y;

        // Simple perspective projection
        const scale = 1 / (2 - z * 0.5);
        const projX = centerX + x * radius * scale;
        const projY = centerY + y * radius * scale;

        // Twinkle effect
        const twinkle = 0.5 + 0.5 * Math.sin(time * 2 + p.phase);

        return {
          x: projX,
          y: projY,
          z,
          size: p.size * scale * (0.8 + 0.4 * twinkle),
          opacity: opacity * (0.3 + 0.7 * (z * 0.5 + 0.5)) * twinkle,
        };
      });

      // Sort by z for proper layering
      rotatedParticles.sort((a, b) => a.z - b.z);

      // Draw particles
      rotatedParticles.forEach((p) => {
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(${rgb.r}, ${rgb.g}, ${rgb.b}, ${p.opacity})`;
        ctx.fill();

        // Add glow
        if (p.opacity > 0.5) {
          ctx.beginPath();
          ctx.arc(p.x, p.y, p.size * 2, 0, Math.PI * 2);
          ctx.fillStyle = `rgba(${rgb.r}, ${rgb.g}, ${rgb.b}, ${p.opacity * 0.2})`;
          ctx.fill();
        }
      });

      // Draw orbit rings
      orbits.forEach((orbit) => {
        const orbitRadius = radius * (1.1 + orbit.id * 0.08);
        const ringPoints = 60;
        
        ctx.beginPath();
        for (let i = 0; i <= ringPoints; i++) {
          const angle = (i / ringPoints) * Math.PI * 2;
          
          // 3D ring coordinates
          let x = Math.cos(angle) * orbitRadius;
          let y = Math.sin(angle) * orbitRadius * Math.cos(orbit.tilt);
          const z = Math.sin(angle) * Math.sin(orbit.tilt);
          
          // Rotate with globe
          const cosR = Math.cos(time * rotationSpeed * orbit.speed);
          const sinR = Math.sin(time * rotationSpeed * orbit.speed);
          const rx = x * cosR - z * sinR * orbitRadius;
          
          // Project
          const scale = 1 / (2 - z * 0.3);
          const projX = centerX + rx * scale / orbitRadius * orbitRadius;
          const projY = centerY + y * scale;
          
          if (i === 0) {
            ctx.moveTo(projX, projY);
          } else {
            ctx.lineTo(projX, projY);
          }
        }
        
        const orbitOpacity = 0.15 + 0.1 * Math.sin(time * 0.5 + orbit.phase);
        ctx.strokeStyle = `rgba(${rgb.r}, ${rgb.g}, ${rgb.b}, ${orbitOpacity})`;
        ctx.lineWidth = 1;
        ctx.stroke();
      });

      animationRef.current = requestAnimationFrame(animate);
    };

    animate();

    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
    };
  }, [size, particles, orbits, rgb, opacity, rotationSpeed, time]);

  return (
    <canvas
      ref={canvasRef}
      width={size}
      height={size}
      className={`${className}`}
      style={{ opacity }}
    />
  );
}
