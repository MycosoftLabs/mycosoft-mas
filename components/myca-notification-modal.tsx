import * as React from "react"
import { Dialog, DialogContent, DialogTitle } from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { MycaNotification } from "./types"

interface MycaNotificationModalProps {
  notification: MycaNotification | null
  onClose: () => void
  onEscalate?: (notification: MycaNotification) => void
  onReplayTTS?: (notification: MycaNotification) => void
}

export function MycaNotificationModal({ notification, onClose, onEscalate, onReplayTTS }: MycaNotificationModalProps) {
  return (
    <Dialog open={!!notification} onOpenChange={onClose}>
      <DialogContent>
        <DialogTitle>Notification Details</DialogTitle>
        {notification && (
          <div className="space-y-2">
            <div><b>Title:</b> {notification.title}</div>
            <div><b>Message:</b> {notification.message}</div>
            <div><b>Agent:</b> {notification.agentName || notification.agentId}</div>
            <div><b>Channel:</b> {notification.channel}</div>
            <div><b>Type:</b> {notification.type}</div>
            <div><b>Event Type:</b> {notification.eventType}</div>
            <div><b>Time:</b> {new Date(notification.timestamp).toLocaleString()}</div>
            <div><b>Context:</b> <pre className="whitespace-pre-wrap text-xs">{JSON.stringify(notification.context, null, 2)}</pre></div>
            <div className="flex gap-2 mt-2">
              {notification.ttsUrl && onReplayTTS && (
                <Button size="sm" variant="outline" onClick={() => onReplayTTS(notification)}>🔊 Replay TTS</Button>
              )}
              {onEscalate && (
                <Button size="sm" variant="destructive" onClick={() => onEscalate(notification)}>Escalate</Button>
              )}
              <Button size="sm" variant="secondary" onClick={onClose}>Close</Button>
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  )
} 