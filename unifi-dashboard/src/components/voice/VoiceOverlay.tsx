"use client";
/**
 * Voice Overlay Component
 * Full-screen voice interaction overlay
 * Created: February 3, 2026
 */

import { useEffect } from "react";
import { useVoice } from "./UnifiedVoiceProvider";
import { X, Mic, Volume2 } from "lucide-react";
import { Button } from "@/components/ui/button";

interface VoiceOverlayProps {
  isOpen: boolean;
  onClose: () => void;
}

export function VoiceOverlay({ isOpen, onClose }: VoiceOverlayProps) {
  const { isListening, isSpeaking, transcript, startListening, stopListening } = useVoice();

  useEffect(() => {
    if (isOpen && !isListening) {
      startListening();
    }
    return () => {
      if (isListening) {
        stopListening();
      }
    };
  }, [isOpen, isListening, startListening, stopListening]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 bg-background/95 backdrop-blur-sm flex flex-col items-center justify-center">
      <Button variant="ghost" className="absolute top-4 right-4" onClick={onClose}>
        <X className="h-6 w-6" />
      </Button>

      <div className="flex flex-col items-center gap-8">
        <div className={`w-32 h-32 rounded-full flex items-center justify-center ${isListening ? "bg-red-500 animate-pulse" : isSpeaking ? "bg-green-500" : "bg-primary"}`}>
          {isSpeaking ? <Volume2 className="h-16 w-16 text-white" /> : <Mic className="h-16 w-16 text-white" />}
        </div>

        <div className="text-center max-w-lg">
          <p className="text-xl font-medium mb-2">
            {isListening ? "Listening..." : isSpeaking ? "Speaking..." : "Ready"}
          </p>
          {transcript && (
            <p className="text-muted-foreground">{transcript}</p>
          )}
        </div>

        <p className="text-sm text-muted-foreground">
          Say "Hey MYCA" or tap the microphone to start
        </p>
      </div>
    </div>
  );
}
