import { NextRequest, NextResponse } from 'next/server';

// PersonaPlex API endpoint for configuration and session management
export async function GET(request: NextRequest) {
  return NextResponse.json({
    status: 'ok',
    serverUrl: process.env.PERSONAPLEX_URL || 'ws://localhost:8998',
    defaultVoice: 'NATF2.pt',
    defaultPrompt: 'You are MYCA, the Mycosoft Autonomous Cognitive Agent.',
    features: {
      fullDuplex: true,
      voiceSelection: true,
      customPrompts: true,
    },
    voices: [
      { id: 'NATF2.pt', name: 'MYCA (Female)', description: 'Default MYCA voice' },
      { id: 'NATF0.pt', name: 'Natural Female 0', description: 'Alternative female' },
      { id: 'NATF1.pt', name: 'Natural Female 1', description: 'Alternative female' },
      { id: 'NATF3.pt', name: 'Natural Female 3', description: 'Alternative female' },
      { id: 'NATM0.pt', name: 'Natural Male 0', description: 'Male voice' },
      { id: 'NATM1.pt', name: 'Natural Male 1', description: 'Male voice' },
    ],
  });
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { action, sessionId, message } = body;
    
    // Forward to MAS orchestrator
    const masUrl = process.env.MAS_ORCHESTRATOR_URL || 'http://192.168.0.188:8001';
    
    if (action === 'start_session') {
      const response = await fetch(\\/voice/personaplex/session\, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          voice_prompt: body.voicePrompt || 'NATF2.pt',
          text_prompt: body.textPrompt || 'You are MYCA',
        }),
      });
      
      if (response.ok) {
        const data = await response.json();
        return NextResponse.json(data);
      }
    }
    
    if (action === 'send_message' && sessionId) {
      const response = await fetch(\\/voice/orchestrator/chat\, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message,
          conversation_id: sessionId,
          source: 'personaplex',
        }),
      });
      
      if (response.ok) {
        const data = await response.json();
        return NextResponse.json(data);
      }
    }
    
    return NextResponse.json({ error: 'Unknown action' }, { status: 400 });
  } catch (error) {
    console.error('PersonaPlex API error:', error);
    return NextResponse.json({ error: 'Internal error' }, { status: 500 });
  }
}
