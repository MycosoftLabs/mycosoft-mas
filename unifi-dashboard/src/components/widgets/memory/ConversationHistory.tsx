"use client";
import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";

interface Message {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  timestamp: string;
}

interface Conversation {
  id: string;
  title: string;
  messages: Message[];
  lastActive: string;
}

export function ConversationHistory() {
  const [conversations, setConversations] = useState<Conversation[]>([
    {
      id: "1",
      title: "Protein Structure Query",
      lastActive: "10 min ago",
      messages: [
        { id: "1", role: "user", content: "What is the structure of psilocybin synthase?", timestamp: "10:30 AM" },
        { id: "2", role: "assistant", content: "Psilocybin synthase is a multidomain enzyme...", timestamp: "10:30 AM" },
      ],
    },
    {
      id: "2",
      title: "Experiment Design",
      lastActive: "1 hour ago",
      messages: [
        { id: "1", role: "user", content: "Design an experiment to test mycelium conductivity", timestamp: "9:15 AM" },
        { id: "2", role: "assistant", content: "I recommend using a 4-electrode impedance setup...", timestamp: "9:16 AM" },
      ],
    },
  ]);
  const [selectedConversation, setSelectedConversation] = useState<string | null>(null);

  const selected = conversations.find((c) => c.id === selectedConversation);

  return (
    <div className="grid gap-4 md:grid-cols-3">
      <Card className="md:col-span-1">
        <CardHeader>
          <CardTitle>Conversations</CardTitle>
        </CardHeader>
        <CardContent>
          <ScrollArea className="h-64">
            <div className="space-y-2">
              {conversations.map((conv) => (
                <div
                  key={conv.id}
                  className={`p-3 border rounded-lg cursor-pointer hover:bg-accent ${selectedConversation === conv.id ? "bg-accent" : ""}`}
                  onClick={() => setSelectedConversation(conv.id)}
                >
                  <p className="font-medium truncate">{conv.title}</p>
                  <p className="text-xs text-muted-foreground">{conv.lastActive}</p>
                </div>
              ))}
            </div>
          </ScrollArea>
        </CardContent>
      </Card>

      <Card className="md:col-span-2">
        <CardHeader>
          <CardTitle>{selected?.title || "Select a conversation"}</CardTitle>
        </CardHeader>
        <CardContent>
          {selected ? (
            <ScrollArea className="h-64">
              <div className="space-y-4">
                {selected.messages.map((msg) => (
                  <div key={msg.id} className={`flex gap-3 ${msg.role === "user" ? "flex-row-reverse" : ""}`}>
                    <Avatar className="h-8 w-8">
                      <AvatarFallback>{msg.role === "user" ? "U" : "M"}</AvatarFallback>
                    </Avatar>
                    <div className={`max-w-[80%] p-3 rounded-lg ${msg.role === "user" ? "bg-primary text-primary-foreground" : "bg-muted"}`}>
                      <p className="text-sm">{msg.content}</p>
                      <p className="text-xs opacity-70 mt-1">{msg.timestamp}</p>
                    </div>
                  </div>
                ))}
              </div>
            </ScrollArea>
          ) : (
            <p className="text-muted-foreground text-center py-8">Select a conversation to view messages</p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
