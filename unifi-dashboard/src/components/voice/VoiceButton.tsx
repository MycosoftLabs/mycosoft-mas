"use client";
/**
 * Voice Button Component
 * Floating voice activation button
 * Created: February 3, 2026
 */

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Mic, MicOff, Volume2 } from "lucide-react";
import { useVoice } from "./UnifiedVoiceProvider";

export function VoiceButton() {
  const { isListening, isSpeaking, startListening, stopListening, transcript, sendVoiceCommand, speak } = useVoice();
  const [processing, setProcessing] = useState(false);

  const handleClick = async () => {
    if (isListening) {
      stopListening();
      if (transcript) {
        setProcessing(true);
        const response = await sendVoiceCommand(transcript);
        speak(response);
        setProcessing(false);
      }
    } else {
      startListening();
    }
  };

  return (
    <div className="fixed bottom-6 right-6 z-50">
      <Button
        size="lg"
        className={`rounded-full w-14 h-14 ${isListening ? "bg-red-500 hover:bg-red-600 animate-pulse" : isSpeaking ? "bg-green-500 hover:bg-green-600" : ""}`}
        onClick={handleClick}
        disabled={processing}
      >
        {isSpeaking ? <Volume2 className="h-6 w-6" /> : isListening ? <MicOff className="h-6 w-6" /> : <Mic className="h-6 w-6" />}
      </Button>
      {isListening && transcript && (
        <div className="absolute bottom-16 right-0 bg-background border rounded-lg p-3 shadow-lg max-w-xs">
          <p className="text-sm">{transcript}</p>
        </div>
      )}
    </div>
  );
}
