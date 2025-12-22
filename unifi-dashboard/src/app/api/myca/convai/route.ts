import { NextResponse } from "next/server";

// ElevenLabs API for Conversational AI
const ELEVENLABS_API_KEY = process.env.ELEVENLABS_API_KEY || "";
const ELEVENLABS_AGENT_ID = process.env.ELEVENLABS_AGENT_ID || "agent_2901kcpp3bk2fcjshrajb9fxvv3y";

// Get signed URL for ElevenLabs Conversational AI
export async function GET() {
  try {
    if (!ELEVENLABS_API_KEY) {
      return NextResponse.json({ error: "ElevenLabs API key not configured" }, { status: 500 });
    }

    // Get signed URL from ElevenLabs
    const response = await fetch(
      `https://api.elevenlabs.io/v1/convai/conversation/get_signed_url?agent_id=${ELEVENLABS_AGENT_ID}`,
      {
        method: "GET",
        headers: {
          "xi-api-key": ELEVENLABS_API_KEY,
        },
      }
    );

    if (!response.ok) {
      console.error("ElevenLabs API error:", response.status, await response.text());
      return NextResponse.json({ error: "Failed to get signed URL" }, { status: response.status });
    }

    const data = await response.json();
    
    return NextResponse.json({
      signedUrl: data.signed_url,
      agentId: ELEVENLABS_AGENT_ID,
    });
  } catch (error) {
    console.error("ConvAI API error:", error);
    return NextResponse.json({
      error: error instanceof Error ? error.message : "Failed to initialize conversation",
    }, { status: 500 });
  }
}
