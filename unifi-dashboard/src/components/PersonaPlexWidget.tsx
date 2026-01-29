"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Recorder from "opus-recorder";

interface PersonaPlexWidgetProps {
  serverUrl?: string;
  voicePrompt?: string;
  textPrompt?: string;
  onTranscript?: (text: string) => void;
  onConnectionChange?: (connected: boolean) => void;
  className?: string;
}

// PersonaPlex Full Duplex Voice Widget - MYCA's primary voice interface
// Connects to PersonaPlex server for real-time conversation
export function PersonaPlexWidget({
  serverUrl = "wss://localhost:8998",
  voicePrompt = "NATF2.pt",
  textPrompt = "You are MYCA, the Mycosoft Autonomous Cognitive Agent.",
  onTranscript,
  onConnectionChange,
  className = "",
}: PersonaPlexWidgetProps) {
  const [isConnected, setIsConnected] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  const [transcript, setTranscript] = useState("");
  const [error, setError] = useState<string | null>(null);
  
  const wsRef = useRef<WebSocket | null>(null);
  const recorderRef = useRef<any>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const decoderRef = useRef<Worker | null>(null);
  const sourceNodeRef = useRef<AudioBufferSourceNode | null>(null);
  const audioQueueRef = useRef<Float32Array[]>([]);
  const isPlayingRef = useRef(false);

  // Play audio queue
  const playNextAudio = useCallback(() => {
    if (!audioContextRef.current || audioQueueRef.current.length === 0) {
      isPlayingRef.current = false;
      return;
    }
    
    isPlayingRef.current = true;
    const audioData = audioQueueRef.current.shift();
    if (!audioData) {
      isPlayingRef.current = false;
      return;
    }
    
    const buffer = audioContextRef.current.createBuffer(1, audioData.length, 24000);
    buffer.copyToChannel(audioData, 0);
    
    const source = audioContextRef.current.createBufferSource();
    source.buffer = buffer;
    source.connect(audioContextRef.current.destination);
    source.onended = () => playNextAudio();
    source.start();
  }, []);

  // Handle incoming WebSocket messages
  const handleMessage = useCallback((event: MessageEvent) => {
    const data = new Uint8Array(event.data);
    const kind = data[0];
    
    if (kind === 0) {
      // Handshake
      console.log("PersonaPlex handshake received");
      setIsConnected(true);
      setIsConnecting(false);
      onConnectionChange?.(true);
    } else if (kind === 1) {
      // Audio - decode and queue
      // For simplicity, using raw PCM conversion here
      // In production, use proper Opus decoder
      const audioData = new Float32Array(data.slice(1).buffer);
      audioQueueRef.current.push(audioData);
      if (!isPlayingRef.current) {
        playNextAudio();
      }
    } else if (kind === 2) {
      // Text
      const text = new TextDecoder().decode(data.slice(1));
      setTranscript(prev => prev + text);
      onTranscript?.(text);
    }
  }, [onTranscript, onConnectionChange, playNextAudio]);

  // Connect to PersonaPlex
  const connect = useCallback(async () => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;
    
    setIsConnecting(true);
    setError(null);
    setTranscript("");
    
    try {
      // Create AudioContext
      if (!audioContextRef.current) {
        audioContextRef.current = new AudioContext({ sampleRate: 24000 });
      }
      await audioContextRef.current.resume();
      
      // Build WebSocket URL
      const wsProtocol = window.location.protocol === "https:" ? "wss" : "ws";
      const baseUrl = serverUrl.replace(/^wss?:\/\//, "");
      const url = new URL(\\://\/api/chat\);
      url.searchParams.set("voice_prompt", voicePrompt);
      url.searchParams.set("text_prompt", textPrompt);
      
      // Connect
      const ws = new WebSocket(url.toString());
      ws.binaryType = "arraybuffer";
      
      ws.onopen = () => console.log("WebSocket connected, waiting for handshake...");
      ws.onmessage = handleMessage;
      ws.onerror = (e) => {
        console.error("WebSocket error:", e);
        setError("Connection error");
        setIsConnecting(false);
      };
      ws.onclose = () => {
        setIsConnected(false);
        setIsConnecting(false);
        onConnectionChange?.(false);
        stopRecording();
      };
      
      wsRef.current = ws;
      
      // Start recording after a short delay
      setTimeout(() => {
        if (ws.readyState === WebSocket.OPEN) {
          startRecording();
        }
      }, 500);
      
    } catch (e: any) {
      console.error("Connection error:", e);
      setError(e.message || "Failed to connect");
      setIsConnecting(false);
    }
  }, [serverUrl, voicePrompt, textPrompt, handleMessage, onConnectionChange]);

  // Start microphone recording
  const startRecording = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      
      const recorderOptions = {
        encoderPath: "/opus-encoder/encoderWorker.min.js",
        bufferLength: 960,
        encoderFrameSize: 20,
        encoderSampleRate: 24000,
        numberOfChannels: 1,
        streamPages: true,
      };
      
      recorderRef.current = new (window as any).Recorder(recorderOptions);
      
      recorderRef.current.ondataavailable = (data: Uint8Array) => {
        if (wsRef.current?.readyState === WebSocket.OPEN) {
          const message = new Uint8Array(1 + data.length);
          message[0] = 1; // Audio kind
          message.set(data, 1);
          wsRef.current.send(message);
        }
      };
      
      recorderRef.current.start(stream);
      console.log("Recording started");
    } catch (e) {
      console.error("Failed to start recording:", e);
    }
  }, []);

  // Stop recording
  const stopRecording = useCallback(() => {
    if (recorderRef.current) {
      recorderRef.current.stop();
      recorderRef.current = null;
    }
  }, []);

  // Disconnect
  const disconnect = useCallback(() => {
    stopRecording();
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    setIsConnected(false);
    onConnectionChange?.(false);
  }, [stopRecording, onConnectionChange]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      disconnect();
      if (audioContextRef.current) {
        audioContextRef.current.close();
      }
    };
  }, [disconnect]);

  return (
    <div className={\personaplex-widget \\}>
      <div className="flex flex-col gap-4 p-4 bg-gray-900 rounded-lg">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className={\w-3 h-3 rounded-full \\} />
            <span className="text-white text-sm">
              {isConnected ? "Connected - Speak now" : isConnecting ? "Connecting..." : "Disconnected"}
            </span>
          </div>
          
          <button
            onClick={isConnected ? disconnect : connect}
            disabled={isConnecting}
            className={\px-4 py-2 rounded-lg font-medium transition-colors \\}
          >
            {isConnected ? "Disconnect" : isConnecting ? "Connecting..." : "Connect"}
          </button>
        </div>
        
        {error && (
          <div className="text-red-400 text-sm">{error}</div>
        )}
        
        {transcript && (
          <div className="bg-gray-800 rounded p-3 max-h-40 overflow-y-auto">
            <p className="text-gray-300 text-sm whitespace-pre-wrap">{transcript}</p>
          </div>
        )}
      </div>
    </div>
  );
}

// Floating version for global access
export function PersonaPlexFloatingWidget({
  serverUrl = "wss://localhost:8998",
  voicePrompt = "NATF2.pt",
  textPrompt = "You are MYCA, the Mycosoft Autonomous Cognitive Agent.",
  position = "bottom-right",
}: PersonaPlexWidgetProps & {
  position?: "bottom-right" | "bottom-left" | "top-right" | "top-left";
}) {
  const [isExpanded, setIsExpanded] = useState(false);
  
  const positionClasses = {
    "bottom-right": "bottom-6 right-6",
    "bottom-left": "bottom-6 left-6",
    "top-right": "top-6 right-6",
    "top-left": "top-6 left-6",
  };

  return (
    <div className={\ixed \ z-50\}>
      {isExpanded ? (
        <div className="relative">
          <button
            onClick={() => setIsExpanded(false)}
            className="absolute -top-2 -right-2 w-6 h-6 bg-gray-700 hover:bg-gray-600 rounded-full flex items-center justify-center text-white text-sm z-10"
          >
            X
          </button>
          <PersonaPlexWidget
            serverUrl={serverUrl}
            voicePrompt={voicePrompt}
            textPrompt={textPrompt}
          />
        </div>
      ) : (
        <button
          onClick={() => setIsExpanded(true)}
          className="w-14 h-14 bg-gradient-to-br from-green-600 to-emerald-700 hover:from-green-500 hover:to-emerald-600 rounded-full flex items-center justify-center text-white shadow-lg transition-transform hover:scale-105"
          title="Talk to MYCA"
        >
          <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
          </svg>
        </button>
      )}
    </div>
  );
}
