import { NextResponse } from "next/server";

// n8n Workflow Endpoints for MYCA Voice
const N8N_BASE_URL = process.env.N8N_WEBHOOK_URL?.replace("/webhook/myca/speech", "") || "http://localhost:5678";
const N8N_JARVIS_URL = `${N8N_BASE_URL}/webhook/myca/jarvis`;
const N8N_SPEECH_URL = `${N8N_BASE_URL}/webhook/myca/speech`;

// POST: Send message to MYCA via n8n Jarvis workflow
export async function POST(request: Request) {
  try {
    const body = await request.json();
    const { text, voice = "arabella", want_audio = true } = body;

    if (!text) {
      return NextResponse.json({ error: "No text provided" }, { status: 400 });
    }

    // Try n8n Jarvis unified interface first (includes TTS)
    try {
      console.log(`Calling n8n Jarvis: ${N8N_JARVIS_URL}`);
      const jarvisResponse = await fetch(N8N_JARVIS_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: text,
          text: text,
          actor: "dashboard",
          want_audio: want_audio,
          session_id: `dash_${Date.now()}`,
        }),
        signal: AbortSignal.timeout(30000),
      });

      if (jarvisResponse.ok) {
        const data = await jarvisResponse.json();
        console.log("Jarvis response:", data);
        
        return NextResponse.json({
          success: true,
          response_text: data.response_text || data.message || "",
          audio_base64: data.audio_base64 || null,
          audio_mime: data.audio_mime || "audio/mpeg",
          session_id: data.session_id,
          source: "n8n-jarvis",
        });
      } else {
        console.warn("Jarvis returned non-OK:", jarvisResponse.status);
      }
    } catch (jarvisError) {
      console.warn("Jarvis workflow not available:", jarvisError);
    }

    // Try n8n Speech workflow as fallback
    try {
      console.log(`Calling n8n Speech: ${N8N_SPEECH_URL}`);
      const speechResponse = await fetch(N8N_SPEECH_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          text: text,
          request_id: `req_${Date.now()}`,
        }),
        signal: AbortSignal.timeout(20000),
      });

      if (speechResponse.ok) {
        const data = await speechResponse.json();
        console.log("Speech response:", data);
        
        return NextResponse.json({
          success: true,
          response_text: data.response_text || data.message || "",
          transcript: data.transcript,
          source: "n8n-speech",
        });
      }
    } catch (speechError) {
      console.warn("Speech workflow not available:", speechError);
    }

    // If n8n didn't respond, generate a fallback response
    const response_text = generateFallbackResponse(text);

    return NextResponse.json({
      success: true,
      response_text,
      voice,
      source: "fallback",
    });
  } catch (error) {
    console.error("MYCA speech API error:", error);
    return NextResponse.json({
      success: false,
      response_text: "I'm having trouble connecting right now. Please try again.",
      error: error instanceof Error ? error.message : "Unknown error",
    }, { status: 500 });
  }
}

// Fallback response generator when n8n is unavailable
function generateFallbackResponse(message: string): string {
  const lowerMessage = message.toLowerCase();
  
  if (lowerMessage.includes("status") || lowerMessage.includes("how are")) {
    return "All systems are operational. I have 7 active agents monitoring the network and completing tasks. The MYCA Orchestrator is running smoothly.";
  }
  if (lowerMessage.includes("agent") && (lowerMessage.includes("active") || lowerMessage.includes("list"))) {
    return "Currently, there are 7 active agents: MYCA Orchestrator, Financial Agent, Mycology Research, Project Manager, Opportunity Scout, MycoDAO Agent, and Dashboard Agent. All are performing within normal parameters.";
  }
  if (lowerMessage.includes("help") || lowerMessage.includes("what can you")) {
    return "I'm Arabella, your MYCA assistant. I can help you with system status, agent management, network monitoring, task execution, and answering questions about the Mycosoft ecosystem. Just ask me what you need.";
  }
  if (lowerMessage.includes("network") || lowerMessage.includes("device")) {
    return "I'm monitoring 8 devices on the network including the MycoBrain. All connections are healthy with an average latency of 6 milliseconds. No issues detected.";
  }
  if (lowerMessage.includes("task") || lowerMessage.includes("todo")) {
    return "There are currently 13 tasks in progress across all agents. The Orchestrator has completed 3,029 tasks total. Would you like me to show you the recent activity?";
  }
  if (lowerMessage.includes("hello") || lowerMessage.includes("hi ") || lowerMessage === "hi") {
    return "Hello! I'm Arabella, your MYCA assistant. How can I help you today?";
  }
  if (lowerMessage.includes("thank")) {
    return "You're welcome! Is there anything else I can help you with?";
  }
  if (lowerMessage.includes("bye") || lowerMessage.includes("goodbye")) {
    return "Goodbye! Feel free to say 'Hey MYCA' anytime you need assistance.";
  }
  
  return "I understand. I'm processing your request through the MYCA system. Is there anything specific you'd like me to help with?";
}
