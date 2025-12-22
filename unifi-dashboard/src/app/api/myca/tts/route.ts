import { NextRequest, NextResponse } from "next/server";

// TTS Service URLs - in order of preference
const ELEVENLABS_PROXY_URL = process.env.ELEVENLABS_PROXY_URL || "http://localhost:5501/v1/audio/speech";
const N8N_TTS_URL = process.env.N8N_TTS_URL || "http://localhost:5678/webhook/myca/speech/tts";
const OPENEDAI_SPEECH_URL = process.env.OPENEDAI_SPEECH_URL || "http://localhost:5500/v1/audio/speech";

// ElevenLabs direct API (fallback if proxy is down)
const ELEVENLABS_API_URL = "https://api.elevenlabs.io/v1/text-to-speech";
const ELEVENLABS_API_KEY = process.env.ELEVENLABS_API_KEY || "";
const ELEVENLABS_VOICE_ID = process.env.ELEVENLABS_VOICE_ID || "aEO01A4wXwd1O8GPgGlF"; // Arabella

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const text = body.text || body.input || "";
    const voice = body.voice || "myca";

    if (!text.trim()) {
      return NextResponse.json({ error: "No text provided" }, { status: 400 });
    }

    // Clean text for TTS (remove markdown, etc.)
    const cleanText = cleanTextForTTS(text);

    // Try ElevenLabs Proxy first (most efficient - caches responses)
    try {
      const proxyRes = await fetch(ELEVENLABS_PROXY_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          model: "tts-1-hd",
          voice: voice,
          input: cleanText,
        }),
      });

      if (proxyRes.ok) {
        const audioBuffer = await proxyRes.arrayBuffer();
        return new NextResponse(audioBuffer, {
          status: 200,
          headers: {
            "Content-Type": "audio/mpeg",
            "X-TTS-Source": "elevenlabs-proxy",
          },
        });
      }
    } catch (e) {
      console.log("ElevenLabs proxy unavailable:", e);
    }

    // Try n8n TTS workflow
    try {
      const n8nRes = await fetch(N8N_TTS_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: cleanText, voice }),
      });

      if (n8nRes.ok) {
        const audioBuffer = await n8nRes.arrayBuffer();
        return new NextResponse(audioBuffer, {
          status: 200,
          headers: {
            "Content-Type": "audio/mpeg",
            "X-TTS-Source": "n8n",
          },
        });
      }
    } catch (e) {
      console.log("n8n TTS unavailable:", e);
    }

    // Try ElevenLabs API directly (use sparingly - costs credits)
    if (ELEVENLABS_API_KEY) {
      try {
        const elevenRes = await fetch(`${ELEVENLABS_API_URL}/${ELEVENLABS_VOICE_ID}`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "xi-api-key": ELEVENLABS_API_KEY,
          },
          body: JSON.stringify({
            text: cleanText,
            model_id: "eleven_multilingual_v2",
            voice_settings: {
              stability: 0.5,
              similarity_boost: 0.75,
            },
          }),
        });

        if (elevenRes.ok) {
          const audioBuffer = await elevenRes.arrayBuffer();
          return new NextResponse(audioBuffer, {
            status: 200,
            headers: {
              "Content-Type": "audio/mpeg",
              "X-TTS-Source": "elevenlabs-direct",
            },
          });
        }
      } catch (e) {
        console.log("ElevenLabs direct API unavailable:", e);
      }
    }

    // Try OpenedAI Speech (local fallback)
    try {
      const openedaiRes = await fetch(OPENEDAI_SPEECH_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          model: "tts-1",
          voice: "alloy",
          input: cleanText,
        }),
      });

      if (openedaiRes.ok) {
        const audioBuffer = await openedaiRes.arrayBuffer();
        return new NextResponse(audioBuffer, {
          status: 200,
          headers: {
            "Content-Type": "audio/mpeg",
            "X-TTS-Source": "openedai-speech",
          },
        });
      }
    } catch (e) {
      console.log("OpenedAI Speech unavailable:", e);
    }

    // All TTS services failed
    return NextResponse.json({
      error: "All TTS services unavailable",
      hint: "Browser speech synthesis will be used as fallback",
    }, { status: 503 });

  } catch (error) {
    console.error("TTS API error:", error);
    return NextResponse.json({
      error: error instanceof Error ? error.message : "TTS failed",
    }, { status: 500 });
  }
}

// Clean text for TTS (remove markdown, special chars, etc.)
function cleanTextForTTS(text: string): string {
  return text
    // Remove markdown formatting
    .replace(/\*\*(.*?)\*\*/g, "$1")
    .replace(/\*(.*?)\*/g, "$1")
    .replace(/`(.*?)`/g, "$1")
    .replace(/```[\s\S]*?```/g, "")
    // Remove URLs
    .replace(/https?:\/\/[^\s]+/g, "link")
    // Clean up whitespace
    .replace(/\n+/g, ". ")
    .replace(/\s+/g, " ")
    .trim();
}

// Health check
export async function GET() {
  const checks = {
    elevenlabs_proxy: false,
    n8n_tts: false,
    elevenlabs_direct: !!ELEVENLABS_API_KEY,
    openedai_speech: false,
  };

  // Quick health checks
  try {
    const res = await fetch(ELEVENLABS_PROXY_URL.replace("/v1/audio/speech", "/health"));
    checks.elevenlabs_proxy = res.ok;
  } catch { /* ignore */ }

  try {
    const res = await fetch(OPENEDAI_SPEECH_URL.replace("/v1/audio/speech", "/health"));
    checks.openedai_speech = res.ok;
  } catch { /* ignore */ }

  return NextResponse.json({
    status: "ok",
    services: checks,
    voice_id: ELEVENLABS_VOICE_ID,
    timestamp: new Date().toISOString(),
  });
}
