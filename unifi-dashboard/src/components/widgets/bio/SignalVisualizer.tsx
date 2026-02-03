"use client";
import { useState, useEffect, useRef } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

interface SignalVisualizerProps {
  sessionId?: string;
  channels?: number;
  sampleRate?: number;
}

export function SignalVisualizer({ sessionId, channels = 4, sampleRate = 1000 }: SignalVisualizerProps) {
  const [isRecording, setIsRecording] = useState(false);
  const [selectedChannel, setSelectedChannel] = useState("all");
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animationRef = useRef<number>();
  const signalData = useRef<number[][]>(Array.from({ length: channels }, () => []));

  useEffect(() => {
    if (isRecording) {
      const animate = () => {
        updateSignals();
        drawSignals();
        animationRef.current = requestAnimationFrame(animate);
      };
      animate();
    } else if (animationRef.current) {
      cancelAnimationFrame(animationRef.current);
    }
    return () => {
      if (animationRef.current) cancelAnimationFrame(animationRef.current);
    };
  }, [isRecording]);

  const updateSignals = () => {
    for (let ch = 0; ch < channels; ch++) {
      const noise = (Math.random() - 0.5) * 20;
      const spike = Math.random() > 0.98 ? (Math.random() - 0.5) * 100 : 0;
      const signal = Math.sin(Date.now() / (200 + ch * 50)) * 30 + noise + spike;
      signalData.current[ch].push(signal);
      if (signalData.current[ch].length > 500) signalData.current[ch].shift();
    }
  };

  const drawSignals = () => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const width = canvas.width;
    const height = canvas.height;
    ctx.fillStyle = "hsl(var(--background))";
    ctx.fillRect(0, 0, width, height);

    const colors = ["#ef4444", "#3b82f6", "#22c55e", "#eab308"];
    const channelsToShow = selectedChannel === "all" ? Array.from({ length: channels }, (_, i) => i) : [parseInt(selectedChannel)];
    const channelHeight = height / channelsToShow.length;

    channelsToShow.forEach((ch, idx) => {
      const data = signalData.current[ch];
      if (data.length < 2) return;

      const yOffset = idx * channelHeight + channelHeight / 2;
      ctx.strokeStyle = colors[ch % colors.length];
      ctx.lineWidth = 1.5;
      ctx.beginPath();

      data.forEach((value, i) => {
        const x = (i / data.length) * width;
        const y = yOffset - (value / 100) * (channelHeight / 2);
        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      });

      ctx.stroke();

      ctx.fillStyle = "hsl(var(--muted-foreground))";
      ctx.font = "12px sans-serif";
      ctx.fillText(`CH ${ch + 1}`, 5, idx * channelHeight + 15);
    });
  };

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle>Signal Visualizer</CardTitle>
          <div className="flex gap-2">
            <Select value={selectedChannel} onValueChange={setSelectedChannel}>
              <SelectTrigger className="w-28">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Channels</SelectItem>
                {Array.from({ length: channels }, (_, i) => (
                  <SelectItem key={i} value={i.toString()}>Channel {i + 1}</SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Button size="sm" variant={isRecording ? "destructive" : "default"} onClick={() => setIsRecording(!isRecording)}>
              {isRecording ? "Stop" : "Start"}
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <canvas ref={canvasRef} width={600} height={200} className="w-full rounded border" />
        <div className="flex justify-between text-xs text-muted-foreground mt-2">
          <span>Sample Rate: {sampleRate} Hz</span>
          <span>Channels: {channels}</span>
          <span>{isRecording ? "ðŸ”´ Recording" : "â¸ Paused"}</span>
        </div>
      </CardContent>
    </Card>
  );
}
