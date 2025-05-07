// MYCA Notification Types
export interface MycaNotification {
  id: string
  type: 'info' | 'warning' | 'critical'
  title: string
  message: string
  timestamp: string
  isRead: boolean
  ttsUrl?: string
  agentId?: string
  agentName?: string
  channel?: string
  eventType?: string
  context?: Record<string, unknown>
  batchId?: string
}

export interface NotificationFilter {
  type?: 'info' | 'warning' | 'critical'
  isRead?: boolean
  search?: string
}

export interface MycaChatMessage {
  id: string
  sender: 'user' | 'myca'
  message: string
  timestamp: string
  ttsUrl?: string
} 