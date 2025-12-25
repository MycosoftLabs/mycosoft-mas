import { NextRequest, NextResponse } from "next/server";

// API endpoints - tries multiple backends in order
const N8N_JARVIS_URL = process.env.N8N_JARVIS_URL || "http://localhost:5678/webhook/myca/jarvis";
const N8N_SPEECH_URL = process.env.N8N_WEBHOOK_URL || "http://localhost:5678/webhook/myca/speech";
const LITELLM_URL = process.env.LITELLM_URL || "http://localhost:4000/v1/chat/completions";

// MYCA System Prompt - always identifies as MYCA (my-kah)
const MYCA_SYSTEM_PROMPT = `You are MYCA (pronounced "my-kah"), the Mycosoft Autonomous Cognitive Agent. 
Your name is MYCA - always introduce yourself as MYCA when asked your name.
You help users manage systems, coordinate agents, access information, and get things done.
Be concise and helpful. For voice responses, keep answers brief but informative.
You have access to various agents and integrations for system management, monitoring, and automation.`;

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const message = body.message || body.text || "";
    const sessionId = body.session_id || `chat_${Date.now()}`;

    if (!message.trim()) {
      return NextResponse.json({ 
        status: "error",
        response_text: "Please provide a message.",
      }, { status: 400 });
    }

    // Try n8n Jarvis first (has all integrations)
    try {
      const jarvisRes = await fetch(N8N_JARVIS_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message,
          actor: "user",
          session_id: sessionId,
          want_audio: false, // We handle TTS separately for efficiency
        }),
      });

      if (jarvisRes.ok) {
        const data = await jarvisRes.json();
        return NextResponse.json({
          status: "success",
          source: "n8n_jarvis",
          session_id: sessionId,
          response_text: data.response_text || data.response || "I understand.",
          intent: data.intent,
          data: data.data,
        });
      }
    } catch (e) {
      console.log("n8n Jarvis unavailable, trying fallback...", e);
    }

    // Try n8n Speech endpoint
    try {
      const speechRes = await fetch(N8N_SPEECH_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: message, message }),
      });

      if (speechRes.ok) {
        const data = await speechRes.json();
        return NextResponse.json({
          status: "success",
          source: "n8n_speech",
          session_id: sessionId,
          response_text: data.response_text || data.response || "I understand.",
        });
      }
    } catch (e) {
      console.log("n8n Speech unavailable, trying LiteLLM...", e);
    }

    // Try LiteLLM (local LLM)
    try {
      const llmRes = await fetch(LITELLM_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          model: "gpt-4o-mini",
          messages: [
            { role: "system", content: MYCA_SYSTEM_PROMPT },
            { role: "user", content: message },
          ],
          max_tokens: 300,
          temperature: 0.7,
        }),
      });

      if (llmRes.ok) {
        const data = await llmRes.json();
        const responseText = data.choices?.[0]?.message?.content || "I understand.";
        return NextResponse.json({
          status: "success",
          source: "litellm",
          session_id: sessionId,
          response_text: responseText,
        });
      }
    } catch (e) {
      console.log("LiteLLM unavailable, using local fallback...", e);
    }

    // Final fallback - local response
    const fallbackResponse = generateFallbackResponse(message);
    return NextResponse.json({
      status: "fallback",
      source: "local",
      session_id: sessionId,
      response_text: fallbackResponse,
    });

  } catch (error) {
    console.error("Chat API error:", error);
    return NextResponse.json({
      status: "error",
      response_text: "I apologize, I'm experiencing technical difficulties. Please try again.",
      error: error instanceof Error ? error.message : "Unknown error",
    }, { status: 500 });
  }
}

// Generate fallback responses when all backends are unavailable
function generateFallbackResponse(message: string): string {
  const lower = message.toLowerCase();
  
  if (lower.includes("hello") || lower.includes("hi") || lower.includes("hey")) {
    return "Hello! I'm MYCA, pronounced 'my-kah'. I'm your Mycosoft Autonomous Cognitive Agent. I'm currently running in local mode, but I'm still here to help. What can I assist you with?";
  }
  
  if (lower.includes("name") || lower.includes("who are you")) {
    return "I'm MYCA, that's M-Y-C-A, pronounced 'my-kah'. I'm the Mycosoft Autonomous Cognitive Agent, designed to help you manage systems and get things done.";
  }
  
  if (lower.includes("help") || lower.includes("what can you do")) {
    return "I can help with system management, agent coordination, network monitoring, and general assistance. I'm currently in local mode with limited capabilities.";
  }
  
  if (lower.includes("status") || lower.includes("system")) {
    return "I'm currently operating in local mode. Some services may be temporarily unavailable. Please try again in a moment for full functionality.";
  }

  if (lower.includes("thank")) {
    return "You're welcome! Is there anything else I can help you with?";
  }

  if (lower.includes("bye") || lower.includes("goodbye")) {
    return "Goodbye! Feel free to call on me whenever you need assistance. This is MYCA, signing off.";
  }
  
  return `I understand you said: "${message}". I'm currently in local mode, but I've noted your request. Please try again when full services are available.`;
}

// Health check
export async function GET() {
  const checks = {
    n8n_jarvis: false,
    n8n_speech: false,
    litellm: false,
  };

  // Check n8n Jarvis
  try {
    const res = await fetch(N8N_JARVIS_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ health_check: true }),
    });
    checks.n8n_jarvis = res.ok;
  } catch { /* ignore */ }

  // Check n8n Speech
  try {
    const res = await fetch(N8N_SPEECH_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ health_check: true }),
    });
    checks.n8n_speech = res.ok;
  } catch { /* ignore */ }

  // Check LiteLLM
  try {
    const res = await fetch(LITELLM_URL.replace("/chat/completions", "/health"), {
      method: "GET",
    });
    checks.litellm = res.ok;
  } catch { /* ignore */ }

  return NextResponse.json({
    status: "ok",
    services: checks,
    timestamp: new Date().toISOString(),
  });
}
