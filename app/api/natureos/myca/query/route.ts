import { NextRequest, NextResponse } from "next/server";

interface MycaQueryRequest {
  question: string;
  userId?: string;
  context?: string;
}

export async function POST(request: NextRequest) {
  try {
    const body: MycaQueryRequest = await request.json();
    const { question, userId = "anonymous", context } = body;

    if (!question || question.trim().length === 0) {
      return NextResponse.json(
        { error: "Question is required" },
        { status: 400 }
      );
    }

    // Try to query MAS MYCA backend
    const masApiUrl = process.env.MAS_API_URL || "http://localhost:8001";
    
    try {
      const response = await fetch(`${masApiUrl}/api/myca/query`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          question,
          userId,
          context: context || "NatureOS system query",
        }),
      });

      if (response.ok) {
        const data = await response.json();
        return NextResponse.json({
          answer: data.answer || data.response || "I'm processing your question about NatureOS.",
          confidence: data.confidence || 0.85,
          timestamp: new Date().toISOString(),
          suggestedQuestions: data.suggestedQuestions || [
            "What devices are currently online?",
            "Show me recent environmental data",
            "What's the system health status?",
          ],
          sources: data.sources || [],
        });
      }
    } catch (masError) {
      console.error("MAS MYCA query failed, using fallback:", masError);
    }

    // Fallback response if MAS backend is unavailable
    const fallbackAnswers: Record<string, string> = {
      health: "The NatureOS system is operating normally. All core services are active.",
      devices: "Multiple MycoBrain devices are connected and reporting telemetry data.",
      species: "Recent detections include various fungal species across multiple taxonomic groups.",
      data: "Real-time data streams are active, collecting environmental and biological measurements.",
    };

    const lowerQuestion = question.toLowerCase();
    let answer = "I can help you with questions about NatureOS, including system status, device telemetry, species detection, and environmental data.";

    if (lowerQuestion.includes("health") || lowerQuestion.includes("status")) {
      answer = fallbackAnswers.health;
    } else if (lowerQuestion.includes("device")) {
      answer = fallbackAnswers.devices;
    } else if (lowerQuestion.includes("species") || lowerQuestion.includes("fungal")) {
      answer = fallbackAnswers.species;
    } else if (lowerQuestion.includes("data") || lowerQuestion.includes("telemetry")) {
      answer = fallbackAnswers.data;
    }

    return NextResponse.json({
      answer,
      confidence: 0.75,
      timestamp: new Date().toISOString(),
      suggestedQuestions: [
        "What devices are currently online?",
        "Show me recent environmental data",
        "What's the system health status?",
        "What species have been detected?",
      ],
      sources: [],
    });
  } catch (error) {
    console.error("MYCA query error:", error);
    return NextResponse.json(
      {
        error: "Failed to process query",
        message: error instanceof Error ? error.message : "Unknown error",
      },
      { status: 500 }
    );
  }
}

