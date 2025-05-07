import { render, screen, fireEvent } from '@testing-library/react'
import { MycaNotificationModal } from '../myca-notification-modal'
import { MycaNotification } from '../types'
describe('MycaNotificationModal', () => {
  const notification: MycaNotification = {
    id: '1',
    type: 'critical',
    title: 'Critical Alert',
    message: 'System failure',
    timestamp: new Date().toISOString(),
    isRead: false,
    agentName: 'Agent1',
    ttsUrl: 'https://example.com/tts.mp3',
  }
  it('renders notification details', () => {
    render(
      <MycaNotificationModal notification={notification} onClose={() => {}} />
    )
    expect(screen.getByText('Critical Alert')).toBeInTheDocument()
    expect(screen.getByText('System failure')).toBeInTheDocument()
  })
  it('calls onReplayTTS when replay button is clicked', () => {
    const onReplayTTS = jest.fn()
    render(
      <MycaNotificationModal notification={notification} onClose={() => {}} onReplayTTS={onReplayTTS} />
    )
    fireEvent.click(screen.getByText(/replay tts/i))
    expect(onReplayTTS).toHaveBeenCalled()
  })
  it('calls onEscalate when escalate button is clicked', () => {
    const onEscalate = jest.fn()
    render(
      <MycaNotificationModal notification={notification} onClose={() => {}} onEscalate={onEscalate} />
    )
    fireEvent.click(screen.getByText(/escalate/i))
    expect(onEscalate).toHaveBeenCalled()
  })
  it('calls onClose when close button is clicked', () => {
    const onClose = jest.fn()
    render(
      <MycaNotificationModal notification={notification} onClose={onClose} />
    )
    fireEvent.click(screen.getByText(/close/i))
    expect(onClose).toHaveBeenCalled()
  })
}) 