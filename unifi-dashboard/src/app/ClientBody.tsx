"use client";

import { useEffect, useState } from "react";
import { PersonaPlexFloatingWidget } from "@/components/PersonaPlexWidget";

export default function ClientBody({
  children,
}: {
  children: React.ReactNode;
}) {
  const [showVoiceWidget, setShowVoiceWidget] = useState(false);

  // Remove any extension-added classes during hydration
  useEffect(() => {
    // This runs only on the client after hydration
    document.body.className = "antialiased";
    
    // Enable voice widget after a short delay
    const timer = setTimeout(() => setShowVoiceWidget(true), 1000);
    return () => clearTimeout(timer);
  }, []);

  return (
    <div className="antialiased">
      {children}
      {showVoiceWidget && (
        <PersonaPlexFloatingWidget
          serverUrl={process.env.NEXT_PUBLIC_PERSONAPLEX_URL || "ws://localhost:8998"}
          voicePrompt="NATF2.pt"
          textPrompt="You are MYCA, the Mycosoft Autonomous Cognitive Agent. You are a helpful AI assistant with expertise in mycology, biology, chemistry, physics, and all Mycosoft products and services."
          position="bottom-right"
        />
      )}
    </div>
  );
}
