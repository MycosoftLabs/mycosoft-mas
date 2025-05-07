import { render, screen, fireEvent } from '@testing-library/react'
import { MycaVoiceReplay } from '../myca-voice-replay'
import { MycaNotification } from '../types'
describe('MycaVoiceReplay', () => {
  const notification: MycaNotification = {
    id: '1',
    type: 'info',
    title: 'Info',
    message: 'Test',
    timestamp: new Date().toISOString(),
    isRead: false,
    ttsUrl: 'https://example.com/tts.mp3',
  }
  it('renders button if ttsUrl exists', () => {
    render(<MycaVoiceReplay notification={notification} onReplay={() => {}} />)
    expect(screen.getByTitle(/replay tts/i)).toBeInTheDocument()
  })
  it('does not render if ttsUrl is missing', () => {
    render(<MycaVoiceReplay notification={{ ...notification, ttsUrl: undefined }} onReplay={() => {}} />)
    expect(screen.queryByTitle(/replay tts/i)).not.toBeInTheDocument()
  })
  it('calls onReplay when clicked', () => {
    const onReplay = jest.fn()
    render(<MycaVoiceReplay notification={notification} onReplay={onReplay} />)
    fireEvent.click(screen.getByTitle(/replay tts/i))
    expect(onReplay).toHaveBeenCalled()
  })
}) 