"use client";

import { useEffect, useRef, useState, useCallback, useMemo } from "react";

interface MouseFlowLines2DProps {
  width?: number;
  height?: number;
  strandCount?: number;
  color?: string;
  opacity?: number;
  influenceRadius?: number;
  className?: string;
}

interface Strand {
  id: number;
  x1: number;
  y1: number;
  x2: number;
  y2: number;
  phase: number;
  speed: number;
}

export function MouseFlowLines2D({
  width = 400,
  height = 300,
  strandCount = 150,
  color = "#a855f7",
  opacity = 0.4,
  influenceRadius = 80,
  className = "",
}: MouseFlowLines2DProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [mousePos, setMousePos] = useState({ x: width / 2, y: height / 2 });
  const [time, setTime] = useState(0);
  const animationRef = useRef<number>();

  // Generate strands
  const strands = useMemo(() => {
    const strs: Strand[] = [];
    const rnd = (i: number) => {
      const x = Math.sin(i * 999.123) * 43758.5453;
      return x - Math.floor(x);
    };

    for (let i = 0; i < strandCount; i++) {
      const x1 = rnd(i + 1) * width;
      const y1 = rnd(i + 2) * height;
      const len = 15 + rnd(i + 3) * 35;
      const angle = rnd(i + 4) * Math.PI * 2;

      strs.push({
        id: i,
        x1,
        y1,
        x2: x1 + Math.cos(angle) * len,
        y2: y1 + Math.sin(angle) * len,
        phase: rnd(i + 5) * Math.PI * 2,
        speed: 0.3 + rnd(i + 6) * 0.7,
      });
    }
    return strs;
  }, [strandCount, width, height]);

  // Parse color to RGB
  const rgb = useMemo(() => {
    const hex = color.replace("#", "");
    return {
      r: parseInt(hex.substring(0, 2), 16),
      g: parseInt(hex.substring(2, 4), 16),
      b: parseInt(hex.substring(4, 6), 16),
    };
  }, [color]);

  // Handle mouse move
  const handleMouseMove = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    const rect = canvasRef.current?.getBoundingClientRect();
    if (!rect) return;
    setMousePos({
      x: e.clientX - rect.left,
      y: e.clientY - rect.top,
    });
  }, []);

  // Animation loop
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const animate = () => {
      setTime((t) => t + 0.016);

      ctx.clearRect(0, 0, width, height);

      strands.forEach((strand) => {
        // Calculate midpoint
        const midX = (strand.x1 + strand.x2) / 2;
        const midY = (strand.y1 + strand.y2) / 2;

        // Distance from mouse
        const dx = midX - mousePos.x;
        const dy = midY - mousePos.y;
        const dist = Math.sqrt(dx * dx + dy * dy);
        const nearMouse = Math.max(0, 1 - dist / influenceRadius);

        // Flow animation along strand
        const flowT = (time * strand.speed + strand.phase) % 1;

        // Calculate gradient points along the strand
        const segments = 8;
        
        for (let i = 0; i < segments; i++) {
          const t1 = i / segments;
          const t2 = (i + 1) / segments;
          
          // Interpolate positions
          const x1 = strand.x1 + (strand.x2 - strand.x1) * t1;
          const y1 = strand.y1 + (strand.y2 - strand.y1) * t1;
          const x2 = strand.x1 + (strand.x2 - strand.x1) * t2;
          const y2 = strand.y1 + (strand.y2 - strand.y1) * t2;

          // Pulse intensity based on flow
          const segmentCenter = (t1 + t2) / 2;
          const flowDist = Math.abs(segmentCenter - flowT);
          const pulse = Math.max(0, 1 - flowDist * 4);

          // Combined intensity
          const intensity = (0.15 + 0.85 * pulse) * (1 + nearMouse * 2);

          // Draw segment
          ctx.beginPath();
          ctx.moveTo(x1, y1);
          ctx.lineTo(x2, y2);

          const segmentOpacity = opacity * intensity * (0.3 + 0.7 * (1 - Math.abs(segmentCenter - 0.5) * 2));
          ctx.strokeStyle = `rgba(${rgb.r}, ${rgb.g}, ${rgb.b}, ${segmentOpacity})`;
          ctx.lineWidth = 1 + nearMouse;
          ctx.lineCap = "round";
          ctx.stroke();
        }

        // Draw bright pulse point
        const pulseX = strand.x1 + (strand.x2 - strand.x1) * flowT;
        const pulseY = strand.y1 + (strand.y2 - strand.y1) * flowT;

        const pulseSize = 1.5 + nearMouse * 2;
        const pulseOpacity = opacity * (0.5 + nearMouse * 0.5);

        // Glow
        ctx.beginPath();
        ctx.arc(pulseX, pulseY, pulseSize * 3, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(${rgb.r}, ${rgb.g}, ${rgb.b}, ${pulseOpacity * 0.15})`;
        ctx.fill();

        // Core
        ctx.beginPath();
        ctx.arc(pulseX, pulseY, pulseSize, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(${rgb.r}, ${rgb.g}, ${rgb.b}, ${pulseOpacity})`;
        ctx.fill();

        // Bright center
        ctx.beginPath();
        ctx.arc(pulseX, pulseY, pulseSize * 0.5, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(255, 255, 255, ${pulseOpacity * 0.6})`;
        ctx.fill();
      });

      // Draw mouse glow
      if (mousePos.x > 0 && mousePos.x < width && mousePos.y > 0 && mousePos.y < height) {
        const gradient = ctx.createRadialGradient(
          mousePos.x, mousePos.y, 0,
          mousePos.x, mousePos.y, influenceRadius
        );
        gradient.addColorStop(0, `rgba(${rgb.r}, ${rgb.g}, ${rgb.b}, 0.1)`);
        gradient.addColorStop(1, `rgba(${rgb.r}, ${rgb.g}, ${rgb.b}, 0)`);

        ctx.beginPath();
        ctx.arc(mousePos.x, mousePos.y, influenceRadius, 0, Math.PI * 2);
        ctx.fillStyle = gradient;
        ctx.fill();
      }

      animationRef.current = requestAnimationFrame(animate);
    };

    animate();

    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
    };
  }, [width, height, strands, rgb, opacity, mousePos, influenceRadius, time]);

  return (
    <canvas
      ref={canvasRef}
      width={width}
      height={height}
      onMouseMove={handleMouseMove}
      className={`${className}`}
    />
  );
}
