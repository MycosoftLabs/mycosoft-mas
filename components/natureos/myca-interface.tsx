"use client";

import { useState, useEffect, useRef } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Bot, Send, Trash2, Download, Loader2 } from "lucide-react";

interface MycaResponse {
  answer: string;
  confidence: number;
  timestamp: string;
  suggestedQuestions?: string[];
  sources?: string[];
}

interface MycaConversationItem {
  id: string;
  question: string;
  response: MycaResponse;
  timestamp: string;
}

interface MYCAInterfaceProps {
  userId?: string;
  className?: string;
  showHistory?: boolean;
  maxHeight?: number;
}

export function MYCAInterface({
  userId = "anonymous",
  className = "",
  showHistory = true,
  maxHeight = 500,
}: MYCAInterfaceProps) {
  const [question, setQuestion] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [conversation, setConversation] = useState<MycaConversationItem[]>([]);
  const [suggestedQuestions, setSuggestedQuestions] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [showSuggestions, setShowSuggestions] = useState(true);
  
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    loadSuggestedQuestions();
    // Load conversation history from localStorage
    const saved = localStorage.getItem("myca-conversation");
    if (saved) {
      try {
        setConversation(JSON.parse(saved));
      } catch (e) {
        console.error("Failed to load conversation:", e);
      }
    }
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [conversation]);

  const loadSuggestedQuestions = async () => {
    const commonQuestions = [
      "What's the current system health?",
      "Show me recent device activity",
      "What species have been detected today?",
      "Are there any system alerts?",
      "What are the trending compounds?",
      "How many devices are online?",
      "Show me network connectivity patterns",
      "What's the data quality score?",
      "Are there any anomalies detected?",
      "What's the current processing throughput?",
    ];
    const shuffled = commonQuestions.sort(() => 0.5 - Math.random());
    setSuggestedQuestions(shuffled.slice(0, 4));
  };

  const validateQuery = (q: string): { valid: boolean; message?: string } => {
    if (!q || q.trim().length === 0) {
      return { valid: false, message: "Question cannot be empty" };
    }
    if (q.length > 1000) {
      return { valid: false, message: "Question is too long (max 1000 characters)" };
    }
    if (q.length < 3) {
      return { valid: false, message: "Question is too short (min 3 characters)" };
    }
    return { valid: true };
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!question.trim()) return;

    const validation = validateQuery(question);
    if (!validation.valid) {
      setError(validation.message || "Invalid question");
      return;
    }

    setIsLoading(true);
    setError(null);
    setShowSuggestions(false);

    try {
      const response = await fetch("/api/natureos/myca/query", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          question,
          userId,
        }),
      });

      if (!response.ok) {
        throw new Error(`Query failed: ${response.statusText}`);
      }

      const mycaResponse: MycaResponse = await response.json();
      
      const newItem: MycaConversationItem = {
        id: Date.now().toString(36) + Math.random().toString(36).substr(2),
        question,
        response: mycaResponse,
        timestamp: new Date().toISOString(),
      };

      const updated = [...conversation, newItem];
      setConversation(updated);
      localStorage.setItem("myca-conversation", JSON.stringify(updated));
      
      setQuestion("");
      inputRef.current?.focus();
      
    } catch (err) {
      setError("Failed to get response from MYCA. Please try again.");
      console.error("MYCA query error:", err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSuggestionClick = (suggestion: string) => {
    setQuestion(suggestion);
    setShowSuggestions(false);
    inputRef.current?.focus();
  };

  const handleClearHistory = () => {
    setConversation([]);
    localStorage.removeItem("myca-conversation");
    setShowSuggestions(true);
  };

  const handleExportHistory = () => {
    const historyJson = JSON.stringify(conversation, null, 2);
    const blob = new Blob([historyJson], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `myca-conversation-${new Date().toISOString().split("T")[0]}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const formatConfidence = (confidence: number): string => {
    const percentage = Math.round(confidence * 100);
    if (percentage >= 90) return `${percentage}% (Excellent)`;
    if (percentage >= 70) return `${percentage}% (Good)`;
    if (percentage >= 50) return `${percentage}% (Moderate)`;
    return `${percentage}% (Low)`;
  };

  const getConfidenceColor = (confidence: number): string => {
    if (confidence >= 0.9) return "bg-green-500";
    if (confidence >= 0.7) return "bg-yellow-500";
    if (confidence >= 0.5) return "bg-orange-500";
    return "bg-red-500";
  };

  return (
    <Card className={`flex flex-col ${className}`} style={{ height: `${maxHeight}px` }}>
      <CardHeader className="flex-shrink-0 border-b">
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <Bot className="w-5 h-5" />
              MYCA AI Assistant
            </CardTitle>
            <p className="text-sm text-gray-500 mt-1">
              Ask questions about your NatureOS system and fungal network
            </p>
          </div>
          <div className="flex gap-2">
            {conversation.length > 0 && (
              <>
                <Button
                  onClick={handleExportHistory}
                  variant="ghost"
                  size="sm"
                  title="Export conversation"
                >
                  <Download className="w-4 h-4" />
                </Button>
                <Button
                  onClick={handleClearHistory}
                  variant="ghost"
                  size="sm"
                  title="Clear conversation"
                >
                  <Trash2 className="w-4 h-4" />
                </Button>
              </>
            )}
          </div>
        </div>
      </CardHeader>

      <ScrollArea className="flex-1 p-4">
        {conversation.length === 0 && showSuggestions ? (
          <div className="text-center py-8">
            <div className="mb-6">
              <h4 className="font-semibold mb-2">👋 Hello! I'm MYCA, your AI assistant</h4>
              <p className="text-sm text-gray-600">
                I can help you understand your NatureOS system, analyze data, and provide insights about your fungal network.
              </p>
            </div>
            
            <div className="mt-6">
              <h5 className="text-sm font-medium mb-3">Try asking me:</h5>
              <div className="grid gap-2 max-w-md mx-auto">
                {suggestedQuestions.map((suggestion, index) => (
                  <Button
                    key={index}
                    onClick={() => handleSuggestionClick(suggestion)}
                    variant="outline"
                    className="justify-start text-left h-auto py-2 px-4"
                  >
                    {suggestion}
                  </Button>
                ))}
              </div>
            </div>
          </div>
        ) : (
          <div className="space-y-6">
            {conversation.map((item) => (
              <div key={item.id} className="space-y-3">
                {/* User Question */}
                <div className="flex justify-end">
                  <div className="max-w-[80%] bg-blue-500 text-white rounded-lg px-4 py-2">
                    <p className="text-sm">{item.question}</p>
                    <p className="text-xs opacity-75 mt-1">
                      {new Date(item.timestamp).toLocaleTimeString()}
                    </p>
                  </div>
                </div>

                {/* MYCA Response */}
                <div className="flex justify-start">
                  <div className="max-w-[85%] bg-gray-100 rounded-lg px-4 py-2">
                    <p className="text-sm text-gray-900">{item.response.answer}</p>
                    
                    <div className="flex items-center gap-2 mt-2">
                      <Badge
                        className={`${getConfidenceColor(item.response.confidence)} text-white text-xs`}
                      >
                        {formatConfidence(item.response.confidence)}
                      </Badge>
                    </div>

                    {item.response.suggestedQuestions && item.response.suggestedQuestions.length > 0 && (
                      <div className="mt-3 pt-3 border-t border-gray-200">
                        <p className="text-xs text-gray-500 mb-2">You might also ask:</p>
                        <div className="flex flex-wrap gap-2">
                          {item.response.suggestedQuestions.map((suggestion, index) => (
                            <Button
                              key={index}
                              onClick={() => handleSuggestionClick(suggestion)}
                              variant="ghost"
                              size="sm"
                              className="text-xs h-auto py-1 px-2"
                            >
                              {suggestion}
                            </Button>
                          ))}
                        </div>
                      </div>
                    )}
                    
                    <p className="text-xs text-gray-500 mt-2">
                      {new Date(item.response.timestamp).toLocaleTimeString()}
                    </p>
                  </div>
                </div>
              </div>
            ))}
            
            {isLoading && (
              <div className="flex justify-start">
                <div className="bg-gray-100 rounded-lg px-4 py-2">
                  <div className="flex items-center gap-2">
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <p className="text-sm text-gray-600">MYCA is thinking...</p>
                  </div>
                </div>
              </div>
            )}
            
            <div ref={messagesEndRef} />
          </div>
        )}
      </ScrollArea>

      {error && (
        <div className="px-4 py-2 bg-red-50 border-t border-red-200 flex items-center justify-between">
          <span className="text-sm text-red-600">⚠️ {error}</span>
          <Button
            onClick={() => setError(null)}
            variant="ghost"
            size="sm"
            className="h-auto p-1"
          >
            ×
          </Button>
        </div>
      )}

      <form onSubmit={handleSubmit} className="flex-shrink-0 border-t p-4">
        <div className="flex gap-2">
          <Input
            ref={inputRef}
            type="text"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="Ask MYCA about your fungal network..."
            disabled={isLoading}
            maxLength={1000}
            className="flex-1"
          />
          <Button
            type="submit"
            disabled={isLoading || !question.trim()}
            size="icon"
          >
            {isLoading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Send className="w-4 h-4" />
            )}
          </Button>
        </div>
        <div className="flex justify-end mt-1">
          <span className="text-xs text-gray-400">{question.length}/1000</span>
        </div>
      </form>
    </Card>
  );
}

