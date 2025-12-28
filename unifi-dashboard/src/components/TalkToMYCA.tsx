"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { X, Mic, MicOff, Volume2, VolumeX, Loader2, Send, Phone, PhoneOff } from "lucide-react";

interface TalkToMYCAProps {
  isOpen: boolean;
  onClose: () => void;
}

type ConnectionStatus = "idle" | "listening" | "processing" | "speaking" | "error";

// API endpoints (proxied through Next.js API routes)
const MYCA_API_ENDPOINT = "/api/myca/chat";
const TTS_API_ENDPOINT = "/api/myca/tts";

export function TalkToMYCA({ isOpen, onClose }: TalkToMYCAProps) {
  const [status, setStatus] = useState<ConnectionStatus>("idle");
  const [isMuted, setIsMuted] = useState(false);
  const [transcript, setTranscript] = useState("");
  const [inputText, setInputText] = useState("");
  const [response, setResponse] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [audioLevel, setAudioLevel] = useState(0);
  const [messages, setMessages] = useState<Array<{ role: "user" | "myca"; text: string }>>([]);
  
  const recognitionRef = useRef<SpeechRecognition | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const animationRef = useRef<number | null>(null);
  const audioPlayerRef = useRef<HTMLAudioElement | null>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const sessionIdRef = useRef<string>(`session_${Date.now()}`);

  // Initialize audio player
  useEffect(() => {
    audioPlayerRef.current = new Audio();
    audioPlayerRef.current.onended = () => {
      setStatus("idle");
    };
    audioPlayerRef.current.onerror = () => {
      console.error("Audio playback error");
      setStatus("idle");
    };
    
    return () => {
      if (audioPlayerRef.current) {
        audioPlayerRef.current.pause();
        audioPlayerRef.current = null;
      }
    };
  }, []);

  // Send message to MYCA - uses chat API + TTS API for efficiency
  const sendToMYCA = useCallback(async (message: string, wantAudio: boolean = true) => {
    if (!message.trim()) return;
    
    setStatus("processing");
    setMessages(prev => [...prev, { role: "user", text: message }]);
    setTranscript("");
    setInputText("");

    try {
      // Step 1: Get chat response
      const chatRes = await fetch(MYCA_API_ENDPOINT, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: message,
          session_id: sessionIdRef.current,
        }),
      });

      let responseText: string;
      
      if (chatRes.ok) {
        const data = await chatRes.json();
        responseText = data.response_text || data.response || data.message || "I understand.";
      } else {
        // Use fallback response if API fails
        responseText = generateLocalResponse(message);
      }
      
      setResponse(responseText);
      setMessages(prev => [...prev, { role: "myca", text: responseText }]);

      // Step 2: Get TTS audio (only if not muted and audio is wanted)
      if (wantAudio && !isMuted && audioPlayerRef.current) {
        setStatus("speaking");
        
        try {
          const ttsRes = await fetch(TTS_API_ENDPOINT, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              text: responseText,
              voice: "myca", // Uses Arabella via ElevenLabs proxy
            }),
          });

          if (ttsRes.ok) {
            const audioBlob = await ttsRes.blob();
            const audioUrl = URL.createObjectURL(audioBlob);
            audioPlayerRef.current.src = audioUrl;
            await audioPlayerRef.current.play();
          } else {
            // TTS failed, fall back to browser speech
            speakWithBrowser(responseText);
          }
        } catch (ttsErr) {
          console.error("TTS error, using browser fallback:", ttsErr);
          speakWithBrowser(responseText);
        }
      } else {
        setStatus("idle");
      }
    } catch (err) {
      console.error("MYCA request failed:", err);
      
      // Complete fallback - use local response + browser speech
      const fallbackText = generateLocalResponse(message);
      setMessages(prev => [...prev, { role: "myca", text: fallbackText }]);
      
      if (wantAudio && !isMuted) {
        setStatus("speaking");
        speakWithBrowser(fallbackText);
      } else {
        setStatus("idle");
      }
    }
  }, [isMuted]);

  // Generate local fallback responses
  const generateLocalResponse = (message: string): string => {
    const lower = message.toLowerCase();
    
    if (lower.includes("hello") || lower.includes("hi") || lower.includes("hey")) {
      return "Hello! I'm MYCA, pronounced 'my-kah'. I'm your Mycosoft Autonomous Cognitive Agent. How can I help you today?";
    }
    if (lower.includes("name") || lower.includes("who are you")) {
      return "I'm MYCA, that's M-Y-C-A, pronounced 'my-kah'. I'm the Mycosoft Autonomous Cognitive Agent, designed to help you manage systems and get things done.";
    }
    if (lower.includes("help") || lower.includes("what can you do")) {
      return "I can help with system management, agent coordination, network monitoring, and general assistance. I'm currently running in local mode with limited capabilities.";
    }
    if (lower.includes("thank")) {
      return "You're welcome! Is there anything else I can help you with?";
    }
    if (lower.includes("bye") || lower.includes("goodbye")) {
      return "Goodbye! Feel free to call on me whenever you need assistance. This is MYCA, signing off.";
    }
    
    return "I understand. I'm currently in local mode, so my capabilities are limited. Please try again when full services are available.";
  };

  // Browser speech synthesis fallback
  const speakWithBrowser = (text: string) => {
    if ('speechSynthesis' in window) {
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.rate = 1.0;
      utterance.pitch = 1.0;
      utterance.voice = window.speechSynthesis.getVoices().find(v => v.name.includes('Female')) || null;
      utterance.onend = () => setStatus("idle");
      utterance.onerror = () => setStatus("idle");
      window.speechSynthesis.speak(utterance);
    } else {
      setStatus("idle");
    }
  };

  // Convert base64 to Blob
  const base64ToBlob = (base64: string, mimeType: string): Blob => {
    const byteCharacters = atob(base64);
    const byteNumbers = new Array(byteCharacters.length);
    for (let i = 0; i < byteCharacters.length; i++) {
      byteNumbers[i] = byteCharacters.charCodeAt(i);
    }
    const byteArray = new Uint8Array(byteNumbers);
    return new Blob([byteArray], { type: mimeType });
  };

  // Start listening with Web Speech API
  const startListening = useCallback(async () => {
    try {
      setError(null);
      
      // Request microphone for visualization
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaStreamRef.current = stream;
      
      // Setup audio visualization
      audioContextRef.current = new AudioContext();
      analyserRef.current = audioContextRef.current.createAnalyser();
      const source = audioContextRef.current.createMediaStreamSource(stream);
      source.connect(analyserRef.current);
      analyserRef.current.fftSize = 256;
      
      const dataArray = new Uint8Array(analyserRef.current.frequencyBinCount);
      const updateLevel = () => {
        if (analyserRef.current && status === "listening") {
          analyserRef.current.getByteFrequencyData(dataArray);
          const average = dataArray.reduce((a, b) => a + b) / dataArray.length;
          setAudioLevel(average / 255);
        }
        animationRef.current = requestAnimationFrame(updateLevel);
      };
      updateLevel();

      // Setup Web Speech API
      const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
      if (!SpeechRecognition) {
        throw new Error("Speech recognition not supported in this browser");
      }

      const recognition = new SpeechRecognition();
      recognition.continuous = false;
      recognition.interimResults = true;
      recognition.lang = "en-US";

      recognition.onstart = () => {
        setStatus("listening");
      };

      recognition.onresult = (event: SpeechRecognitionEvent) => {
        const last = event.results.length - 1;
        const text = event.results[last][0].transcript;
        setTranscript(text);
        
        if (event.results[last].isFinal) {
          sendToMYCA(text);
          stopListening();
        }
      };

      recognition.onerror = (event: SpeechRecognitionErrorEvent) => {
        console.error("Speech recognition error:", event.error);
        if (event.error !== "aborted") {
          setError(`Recognition error: ${event.error}`);
        }
        stopListening();
      };

      recognition.onend = () => {
        if (status === "listening") {
          setStatus("idle");
        }
      };

      recognitionRef.current = recognition;
      recognition.start();
      
    } catch (err) {
      console.error("Failed to start listening:", err);
      setError(err instanceof Error ? err.message : "Microphone access denied");
      setStatus("error");
    }
  }, [sendToMYCA, status]);

  // Stop listening
  const stopListening = useCallback(() => {
    if (recognitionRef.current) {
      recognitionRef.current.stop();
      recognitionRef.current = null;
    }
    if (animationRef.current) {
      cancelAnimationFrame(animationRef.current);
    }
    if (audioContextRef.current) {
      audioContextRef.current.close();
    }
    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach(track => track.stop());
    }
    setAudioLevel(0);
    if (status === "listening") {
      setStatus("idle");
    }
  }, [status]);

  // Toggle listening
  const toggleListening = useCallback(() => {
    if (status === "listening") {
      stopListening();
    } else if (status === "idle") {
      startListening();
    }
  }, [status, startListening, stopListening]);

  // Handle text input submit
  const handleSubmit = useCallback((e: React.FormEvent) => {
    e.preventDefault();
    if (inputText.trim() && status !== "processing" && status !== "speaking") {
      sendToMYCA(inputText);
    }
  }, [inputText, status, sendToMYCA]);

  // Stop audio playback
  const stopSpeaking = useCallback(() => {
    if (audioPlayerRef.current) {
      audioPlayerRef.current.pause();
      audioPlayerRef.current.currentTime = 0;
    }
    setStatus("idle");
  }, []);

  // Cleanup on close
  useEffect(() => {
    if (!isOpen) {
      stopListening();
      stopSpeaking();
    }
  }, [isOpen, stopListening, stopSpeaking]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      stopListening();
      stopSpeaking();
    };
  }, [stopListening, stopSpeaking]);

  if (!isOpen) return null;

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/70 backdrop-blur-md z-40"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="fixed z-50 top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[95vw] max-w-lg bg-gradient-to-b from-gray-900 via-gray-900 to-gray-950 rounded-3xl shadow-2xl border border-purple-500/20 overflow-hidden flex flex-col max-h-[85vh]">
        
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-800 shrink-0">
          <div className="flex items-center gap-3">
            <div className="relative">
              <div className={`w-12 h-12 rounded-full bg-gradient-to-br from-purple-600 to-cyan-500 flex items-center justify-center ${
                status === "speaking" ? "animate-pulse" : ""
              }`}>
                <span className="text-xl">🍄</span>
              </div>
              <span className={`absolute -bottom-1 -right-1 w-4 h-4 rounded-full border-2 border-gray-900 ${
                status === "error" ? "bg-red-500" : "bg-green-500"
              }`} />
            </div>
            <div>
              <h2 className="text-lg font-bold text-white">MYCA</h2>
              <p className="text-xs text-gray-400">
                {status === "listening" && "Listening..."}
                {status === "processing" && "Thinking..."}
                {status === "speaking" && "Speaking..."}
                {status === "idle" && "Ready to help"}
                {status === "error" && "Error occurred"}
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-2 rounded-full bg-gray-800 hover:bg-red-600 text-gray-400 hover:text-white transition-all"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4 min-h-[200px]">
          {messages.length === 0 && (
            <div className="text-center text-gray-500 py-8">
              <p className="text-lg mb-2">Hello! I'm MYCA</p>
              <p className="text-sm">(pronounced "my-kah")</p>
              <p className="text-sm mt-4">Your Mycosoft Autonomous Cognitive Agent</p>
              <p className="text-xs mt-2">Tap the mic or type to start talking</p>
            </div>
          )}
          
          {messages.map((msg, idx) => (
            <div
              key={idx}
              className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
            >
              <div
                className={`max-w-[80%] rounded-2xl px-4 py-3 ${
                  msg.role === "user"
                    ? "bg-purple-600 text-white"
                    : "bg-gray-800 text-gray-100 border border-gray-700"
                }`}
              >
                <p className="text-sm">{msg.text}</p>
              </div>
            </div>
          ))}
          
          {transcript && status === "listening" && (
            <div className="flex justify-end">
              <div className="max-w-[80%] rounded-2xl px-4 py-3 bg-purple-600/50 text-white/80 border border-purple-500/30">
                <p className="text-sm italic">{transcript}...</p>
              </div>
            </div>
          )}
        </div>

        {/* Voice Visualization */}
        {status === "listening" && (
          <div className="px-4 py-3 flex justify-center">
            <div 
              className="w-20 h-20 rounded-full bg-gradient-to-br from-purple-600 to-cyan-500 flex items-center justify-center"
              style={{
                boxShadow: `0 0 ${20 + audioLevel * 60}px ${audioLevel * 30}px rgba(168, 85, 247, ${0.3 + audioLevel * 0.4})`,
                transform: `scale(${1 + audioLevel * 0.2})`
              }}
            >
              <Mic className="w-8 h-8 text-white" />
            </div>
          </div>
        )}

        {/* Error Display */}
        {error && (
          <div className="px-4 py-2 bg-red-500/20 border-t border-red-500/30">
            <p className="text-red-400 text-sm text-center">{error}</p>
          </div>
        )}

        {/* Input Area */}
        <div className="p-4 border-t border-gray-800 bg-gray-900/50 shrink-0">
          <form onSubmit={handleSubmit} className="flex items-center gap-3">
            {/* Mic Button */}
            <button
              type="button"
              onClick={toggleListening}
              disabled={status === "processing" || status === "speaking"}
              className={`p-3 rounded-full transition-all ${
                status === "listening"
                  ? "bg-red-500 text-white animate-pulse"
                  : "bg-gray-800 text-gray-400 hover:bg-purple-600 hover:text-white"
              } disabled:opacity-50 disabled:cursor-not-allowed`}
              title={status === "listening" ? "Stop listening" : "Start listening"}
            >
              {status === "listening" ? <MicOff className="w-5 h-5" /> : <Mic className="w-5 h-5" />}
            </button>

            {/* Text Input */}
            <input
              type="text"
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              placeholder="Type a message..."
              disabled={status === "processing" || status === "speaking"}
              className="flex-1 bg-gray-800 border border-gray-700 rounded-full px-4 py-2 text-white placeholder-gray-500 focus:outline-none focus:border-purple-500 disabled:opacity-50"
            />

            {/* Send Button */}
            <button
              type="submit"
              disabled={!inputText.trim() || status === "processing" || status === "speaking"}
              className="p-3 rounded-full bg-purple-600 text-white hover:bg-purple-500 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
              title="Send message"
            >
              {status === "processing" ? (
                <Loader2 className="w-5 h-5 animate-spin" />
              ) : (
                <Send className="w-5 h-5" />
              )}
            </button>

            {/* Mute/Stop Button */}
            {status === "speaking" ? (
              <button
                type="button"
                onClick={stopSpeaking}
                className="p-3 rounded-full bg-red-600 text-white hover:bg-red-500 transition-all"
                title="Stop speaking"
              >
                <PhoneOff className="w-5 h-5" />
              </button>
            ) : (
              <button
                type="button"
                onClick={() => setIsMuted(!isMuted)}
                className={`p-3 rounded-full transition-all ${
                  isMuted
                    ? "bg-red-500/20 text-red-400"
                    : "bg-gray-800 text-gray-400 hover:bg-gray-700"
                }`}
                title={isMuted ? "Unmute" : "Mute"}
              >
                {isMuted ? <VolumeX className="w-5 h-5" /> : <Volume2 className="w-5 h-5" />}
              </button>
            )}
          </form>
        </div>
      </div>
    </>
  );
}

// Floating Talk Button
export function TalkToMYCAButton({ onClick }: { onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className="fixed bottom-6 right-6 z-30 p-4 rounded-full bg-gradient-to-br from-purple-600 to-cyan-600 text-white shadow-lg hover:shadow-purple-500/25 hover:scale-105 transition-all"
      title="Talk to MYCA"
    >
      <Mic className="w-6 h-6" />
      <span className="absolute -top-1 -right-1 w-3 h-3 rounded-full bg-green-500 animate-pulse" />
    </button>
  );
}

// Web Speech API types
declare global {
  interface Window {
    SpeechRecognition: typeof SpeechRecognition;
    webkitSpeechRecognition: typeof SpeechRecognition;
  }
}
