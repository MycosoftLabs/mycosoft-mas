import * as React from "react"
import { Button } from "@/components/ui/button"
import { MycaNotification } from "./types"

interface MycaVoiceReplayProps {
  notification: MycaNotification
  onReplay: (notification: MycaNotification) => void
}

export function MycaVoiceReplay({ notification, onReplay }: MycaVoiceReplayProps) {
  if (!notification.ttsUrl) return null
  return (
    <Button size="icon" variant="ghost" onClick={() => onReplay(notification)} title="Replay TTS">
      🔊
    </Button>
  )
} 