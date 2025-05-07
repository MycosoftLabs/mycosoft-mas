import { render, screen, fireEvent } from '@testing-library/react'
import { MycaNotificationPanel } from '../myca-notification-panel'
import { MycaNotification } from '../types'

describe('MycaNotificationPanel', () => {
  const notifications: MycaNotification[] = [
    {
      id: '1',
      type: 'critical',
      title: 'Critical Alert',
      message: 'System failure imminent',
      timestamp: new Date().toISOString(),
      isRead: false,
      agentName: 'TestAgent',
      ttsUrl: '/test.mp3',
    },
    {
      id: '2',
      type: 'info',
      title: 'Info',
      message: 'All systems nominal',
      timestamp: new Date().toISOString(),
      isRead: false,
    },
  ]

  it('renders notifications and handles select', () => {
    const handleSelect = jest.fn()
    render(
      <MycaNotificationPanel
        notifications={notifications}
        onSelect={handleSelect}
        filter={{}}
        onFilterChange={() => {}}
      />
    )
    expect(screen.getByText('Critical Alert - System failure imminent')).toBeInTheDocument()
    fireEvent.click(screen.getByText('Critical Alert - System failure imminent'))
    expect(handleSelect).toHaveBeenCalled()
  })

  it('shows TTS replay button if ttsUrl present', () => {
    const handleReplay = jest.fn()
    render(
      <MycaNotificationPanel
        notifications={notifications}
        onSelect={() => {}}
        onReplayTTS={handleReplay}
        filter={{}}
        onFilterChange={() => {}}
      />
    )
    expect(screen.getAllByRole('button', { name: '🔊' })[0]).toBeInTheDocument()
    fireEvent.click(screen.getAllByRole('button', { name: '🔊' })[0])
    expect(handleReplay).toHaveBeenCalled()
  })

  it('filters by type', () => {
    render(
      <MycaNotificationPanel
        notifications={notifications}
        onSelect={() => {}}
        filter={{ type: 'critical' }}
        onFilterChange={() => {}}
      />
    )
    expect(screen.getByText('Critical Alert - System failure imminent')).toBeInTheDocument()
    expect(screen.queryByText('Info - All systems nominal')).not.toBeInTheDocument()
  })

  it('shows escalation style for critical notifications', () => {
    render(
      <MycaNotificationPanel
        notifications={notifications}
        onSelect={() => {}}
        filter={{}}
        onFilterChange={() => {}}
      />
    )
    const critical = screen.getByText('Critical Alert - System failure imminent').closest('div')
    expect(critical).toHaveClass('bg-red-100')
  })
}) 