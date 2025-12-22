"use client";

import { useEffect, useRef } from "react";

interface ElevenLabsWidgetProps {
  agentId?: string;
  className?: string;
}

// ElevenLabs ConvAI Widget - Arabella (MYCA's official voice)
// Agent ID: agent_2901kcpp3bk2fcjshrajb9fxvv3y
// Voice: Arabella (aEO01A4wXwd1O8GPgGlF)
// With Cursor integration tools for cloud agent management

export function ElevenLabsWidget({
  agentId = "agent_2901kcpp3bk2fcjshrajb9fxvv3y",
  className = "",
}: ElevenLabsWidgetProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const scriptLoaded = useRef(false);

  useEffect(() => {
    // Only load the script once
    if (scriptLoaded.current) return;

    // Check if script already exists
    const existingScript = document.querySelector(
      'script[src*="elevenlabs/convai-widget-embed"]'
    );

    if (!existingScript) {
      const script = document.createElement("script");
      script.src = "https://unpkg.com/@elevenlabs/convai-widget-embed@beta";
      script.async = true;
      script.type = "text/javascript";
      document.body.appendChild(script);
    }

    scriptLoaded.current = true;

    // Cleanup is not needed as the widget should persist
  }, []);

  return (
    <div ref={containerRef} className={className}>
      {/* @ts-expect-error - ElevenLabs custom element */}
      <elevenlabs-convai agent-id={agentId}></elevenlabs-convai>
    </div>
  );
}

// Alternative: Floating widget that can be positioned anywhere
export function ElevenLabsFloatingWidget({
  agentId = "agent_2901kcpp3bk2fcjshrajb9fxvv3y",
  position = "bottom-right",
}: {
  agentId?: string;
  position?: "bottom-right" | "bottom-left" | "top-right" | "top-left";
}) {
  const positionClasses = {
    "bottom-right": "bottom-6 right-6",
    "bottom-left": "bottom-6 left-6",
    "top-right": "top-6 right-6",
    "top-left": "top-6 left-6",
  };

  useEffect(() => {
    // Load the ElevenLabs script
    const existingScript = document.querySelector(
      'script[src*="elevenlabs/convai-widget-embed"]'
    );

    if (!existingScript) {
      const script = document.createElement("script");
      script.src = "https://unpkg.com/@elevenlabs/convai-widget-embed@beta";
      script.async = true;
      script.type = "text/javascript";
      document.body.appendChild(script);
    }
  }, []);

  return (
    <div className={`fixed ${positionClasses[position]} z-50`}>
      {/* @ts-expect-error - ElevenLabs custom element */}
      <elevenlabs-convai agent-id={agentId}></elevenlabs-convai>
    </div>
  );
}

// Declare the custom element for TypeScript
declare global {
  // eslint-disable-next-line @typescript-eslint/no-namespace
  namespace JSX {
    interface IntrinsicElements {
      "elevenlabs-convai": React.DetailedHTMLProps<
        React.HTMLAttributes<HTMLElement> & { "agent-id": string },
        HTMLElement
      >;
    }
  }
}
