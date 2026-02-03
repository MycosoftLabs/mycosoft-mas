"use client";
/**
 * Unified Voice Provider
 * Provides voice capabilities across the dashboard
 * Created: February 3, 2026
 */

import React, { createContext, useContext, useState, useCallback, ReactNode } from "react";

interface VoiceContextType {
  isListening: boolean;
  isSpeaking: boolean;
  transcript: string;
  startListening: () => void;
  stopListening: () => void;
  speak: (text: string) => void;
  stopSpeaking: () => void;
  sendVoiceCommand: (command: string) => Promise<string>;
}

const VoiceContext = createContext<VoiceContextType | null>(null);

export function useVoice() {
  const context = useContext(VoiceContext);
  if (!context) {
    throw new Error("useVoice must be used within a UnifiedVoiceProvider");
  }
  return context;
}

interface Props {
  children: ReactNode;
}

export function UnifiedVoiceProvider({ children }: Props) {
  const [isListening, setIsListening] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [transcript, setTranscript] = useState("");

  const startListening = useCallback(() => {
    setIsListening(true);
    // Web Speech API integration would go here
    if ("webkitSpeechRecognition" in window || "SpeechRecognition" in window) {
      const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
      const recognition = new SpeechRecognition();
      recognition.continuous = true;
      recognition.interimResults = true;
      recognition.onresult = (event: any) => {
        const result = event.results[event.results.length - 1];
        setTranscript(result[0].transcript);
      };
      recognition.start();
    }
  }, []);

  const stopListening = useCallback(() => {
    setIsListening(false);
  }, []);

  const speak = useCallback((text: string) => {
    setIsSpeaking(true);
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.onend = () => setIsSpeaking(false);
    speechSynthesis.speak(utterance);
  }, []);

  const stopSpeaking = useCallback(() => {
    speechSynthesis.cancel();
    setIsSpeaking(false);
  }, []);

  const sendVoiceCommand = useCallback(async (command: string): Promise<string> => {
    try {
      const response = await fetch("/api/mas/voice/orchestrator", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ command, source: "dashboard" }),
      });
      if (response.ok) {
        const data = await response.json();
        return data.response || "Command received";
      }
      return "Failed to process command";
    } catch (error) {
      console.error("Voice command error:", error);
      return "Error processing command";
    }
  }, []);

  return (
    <VoiceContext.Provider value={{ isListening, isSpeaking, transcript, startListening, stopListening, speak, stopSpeaking, sendVoiceCommand }}>
      {children}
    </VoiceContext.Provider>
  );
}
