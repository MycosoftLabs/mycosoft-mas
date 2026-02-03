"use client";
import { useRef, useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Slider } from "@/components/ui/slider";

interface Node {
  id: string;
  x: number;
  y: number;
  signal: number;
}

interface Edge {
  source: string;
  target: string;
}

interface MyceliumNetworkVizProps {
  nodes?: Node[];
  edges?: Edge[];
  width?: number;
  height?: number;
}

export function MyceliumNetworkViz({ width = 600, height = 400 }: MyceliumNetworkVizProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [isSimulating, setIsSimulating] = useState(false);
  const [speed, setSpeed] = useState([50]);
  const nodesRef = useRef<Node[]>([]);
  const edgesRef = useRef<Edge[]>([]);
  const animationRef = useRef<number>();

  useEffect(() => {
    initializeNetwork();
    return () => { if (animationRef.current) cancelAnimationFrame(animationRef.current); };
  }, []);

  useEffect(() => {
    if (isSimulating) {
      const animate = () => {
        updateNetwork();
        drawNetwork();
        animationRef.current = requestAnimationFrame(animate);
      };
      animate();
    } else {
      if (animationRef.current) cancelAnimationFrame(animationRef.current);
      drawNetwork();
    }
  }, [isSimulating]);

  const initializeNetwork = () => {
    const centerX = width / 2;
    const centerY = height / 2;
    nodesRef.current = [{ id: "0", x: centerX, y: centerY, signal: 1 }];
    edgesRef.current = [];
    for (let i = 1; i <= 20; i++) {
      const angle = Math.random() * Math.PI * 2;
      const distance = 50 + Math.random() * 150;
      nodesRef.current.push({
        id: i.toString(),
        x: centerX + Math.cos(angle) * distance,
        y: centerY + Math.sin(angle) * distance,
        signal: Math.random(),
      });
      const parent = Math.floor(Math.random() * i);
      edgesRef.current.push({ source: parent.toString(), target: i.toString() });
    }
    drawNetwork();
  };

  const updateNetwork = () => {
    const speedFactor = speed[0] / 100;
    if (Math.random() < 0.05 * speedFactor && nodesRef.current.length < 100) {
      const parentIdx = Math.floor(Math.random() * nodesRef.current.length);
      const parent = nodesRef.current[parentIdx];
      const angle = Math.random() * Math.PI * 2;
      const distance = 20 + Math.random() * 30;
      const newNode: Node = {
        id: nodesRef.current.length.toString(),
        x: Math.max(20, Math.min(width - 20, parent.x + Math.cos(angle) * distance)),
        y: Math.max(20, Math.min(height - 20, parent.y + Math.sin(angle) * distance)),
        signal: Math.random() * 0.5,
      };
      nodesRef.current.push(newNode);
      edgesRef.current.push({ source: parent.id, target: newNode.id });
    }
    nodesRef.current.forEach((node) => {
      node.signal = Math.max(0, Math.min(1, node.signal + (Math.random() - 0.5) * 0.1));
    });
  };

  const drawNetwork = () => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    ctx.fillStyle = "hsl(var(--background))";
    ctx.fillRect(0, 0, width, height);

    ctx.strokeStyle = "hsl(var(--muted-foreground))";
    ctx.lineWidth = 1;
    edgesRef.current.forEach((edge) => {
      const source = nodesRef.current.find((n) => n.id === edge.source);
      const target = nodesRef.current.find((n) => n.id === edge.target);
      if (source && target) {
        ctx.beginPath();
        ctx.moveTo(source.x, source.y);
        ctx.lineTo(target.x, target.y);
        ctx.stroke();
      }
    });

    nodesRef.current.forEach((node) => {
      const hue = 120 - node.signal * 120;
      ctx.fillStyle = `hsl(${hue}, 70%, 50%)`;
      ctx.beginPath();
      ctx.arc(node.x, node.y, 4 + node.signal * 4, 0, Math.PI * 2);
      ctx.fill();
    });
  };

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle>Mycelium Network Visualization</CardTitle>
          <div className="flex gap-2">
            <Button size="sm" variant="outline" onClick={initializeNetwork}>Reset</Button>
            <Button size="sm" onClick={() => setIsSimulating(!isSimulating)}>{isSimulating ? "Pause" : "Simulate"}</Button>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <canvas ref={canvasRef} width={width} height={height} className="w-full rounded border" />
        <div className="flex items-center gap-4 mt-4">
          <span className="text-sm">Speed:</span>
          <Slider value={speed} onValueChange={setSpeed} max={100} step={1} className="flex-1" />
          <span className="text-sm">{speed}%</span>
        </div>
        <div className="flex justify-between text-xs text-muted-foreground mt-2">
          <span>Nodes: {nodesRef.current.length}</span>
          <span>Edges: {edgesRef.current.length}</span>
          <span>{isSimulating ? "ðŸŸ¢ Growing" : "â¸ Paused"}</span>
        </div>
      </CardContent>
    </Card>
  );
}
