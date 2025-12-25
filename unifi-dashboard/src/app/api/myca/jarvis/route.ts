import { NextRequest, NextResponse } from "next/server";

// n8n Jarvis Unified endpoint - handles LLM + TTS internally
const N8N_JARVIS_URL = process.env.N8N_JARVIS_URL || "http://localhost:5678/webhook/myca/jarvis";

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    
    // Forward request to n8n Jarvis workflow
    const response = await fetch(N8N_JARVIS_URL, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        message: body.message || body.text || "",
        actor: body.actor || "user",
        session_id: body.session_id || `web_${Date.now()}`,
        want_audio: body.want_audio !== false,
        context: body.context || {},
      }),
    });

    if (!response.ok) {
      console.error("n8n Jarvis error:", response.status);
      
      // Return fallback response
      return NextResponse.json({
        status: "fallback",
        response_text: generateFallbackResponse(body.message || ""),
        audio_base64: null,
        audio_mime: null,
        error: `n8n returned ${response.status}`,
      });
    }

    const data = await response.json();
    
    return NextResponse.json({
      status: data.status || "success",
      session_id: data.session_id,
      response_text: data.response_text || data.response || "I understand.",
      intent: data.intent,
      data: data.data,
      audio_base64: data.audio_base64 || null,
      audio_mime: data.audio_mime || "audio/mpeg",
      timestamp: data.timestamp || new Date().toISOString(),
    });
    
  } catch (error) {
    console.error("Jarvis API error:", error);
    
    return NextResponse.json({
      status: "error",
      response_text: "I apologize, I'm experiencing technical difficulties. Please try again shortly.",
      audio_base64: null,
      audio_mime: null,
      error: error instanceof Error ? error.message : "Connection failed",
    }, { status: 500 });
  }
}

// Fallback responses when n8n is unavailable
function generateFallbackResponse(message: string): string {
  const lowerMessage = message.toLowerCase();
  
  if (lowerMessage.includes("hello") || lowerMessage.includes("hi") || lowerMessage.includes("hey")) {
    return "Hello! I'm MYCA, your Mycosoft Autonomous Cognitive Agent. I'm currently running in fallback mode, but I'm still here to help. What can I assist you with?";
  }
  
  if (lowerMessage.includes("name") || lowerMessage.includes("who are you")) {
    return "I'm MYCA, pronounced 'my-kah'. I'm the Mycosoft Autonomous Cognitive Agent, designed to help you manage systems, access information, and get things done.";
  }
  
  if (lowerMessage.includes("help") || lowerMessage.includes("what can you do")) {
    return "I can help with many things including system management, agent coordination, network monitoring, and general assistance. However, I'm currently in fallback mode with limited capabilities.";
  }
  
  if (lowerMessage.includes("status") || lowerMessage.includes("system")) {
    return "I'm currently operating in fallback mode. Some services may be temporarily unavailable. Please try again in a moment for full functionality.";
  }
  
  return "I understand you said: \"" + message + "\". I'm currently in fallback mode, but I've noted your request. Please try again when full services are available.";
}

// Health check endpoint
export async function GET() {
  try {
    // Test n8n connection
    const response = await fetch(N8N_JARVIS_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ health_check: true }),
    });
    
    const n8nStatus = response.ok ? "connected" : "unavailable";
    
    return NextResponse.json({
      status: "ok",
      n8n: n8nStatus,
      endpoint: N8N_JARVIS_URL,
      timestamp: new Date().toISOString(),
    });
  } catch {
    return NextResponse.json({
      status: "ok",
      n8n: "unreachable",
      endpoint: N8N_JARVIS_URL,
      timestamp: new Date().toISOString(),
    });
  }
}
