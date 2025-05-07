import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import DashboardPage from '../page'

jest.mock('@/components/agent-manager', () => ({ AgentManager: () => <div>AgentManager</div> }))
jest.mock('@/components/system-metrics', () => ({ SystemMetrics: () => <div>SystemMetrics</div> }))
jest.mock('@/components/knowledge-graph', () => ({ KnowledgeGraph: () => <div>KnowledgeGraph</div> }))

// Mock fetch for improvements and logs
beforeAll(() => {
  global.fetch = jest.fn((url) => {
    if (url === '/api/improvements') {
      return Promise.resolve({ json: () => Promise.resolve({ improvements: [{ name: 'Upgrade', description: 'Do X', source_url: 'http://example.com' }] }) })
    }
    if (url === '/api/logs') {
      return Promise.resolve({ json: () => Promise.resolve({ logs: ['Log entry 1', 'Log entry 2'] }) })
    }
    return Promise.resolve({ json: () => Promise.resolve({}) })
  }) as any
})

afterAll(() => {
  jest.resetAllMocks()
})

describe('DashboardPage', () => {
  it('renders all main widgets and panels', async () => {
    render(<DashboardPage />)
    expect(screen.getByText('MYCA Notifications')).toBeInTheDocument()
    expect(screen.getByText('AgentManager')).toBeInTheDocument()
    expect(screen.getByText('SystemMetrics')).toBeInTheDocument()
    expect(screen.getByText('KnowledgeGraph')).toBeInTheDocument()
    await waitFor(() => expect(screen.getByText('MYCA Self-Improvement Suggestions')).toBeInTheDocument())
    expect(screen.getByText('Upgrade')).toBeInTheDocument()
    expect(screen.getByText('System Logs')).toBeInTheDocument()
    expect(screen.getByText('Log entry 1')).toBeInTheDocument()
  })

  it('renders chat input and sends message', async () => {
    render(<DashboardPage />)
    const input = screen.getByPlaceholderText('Type a message or command for MYCA...')
    fireEvent.change(input, { target: { value: 'Hello MYCA' } })
    fireEvent.click(screen.getByRole('button', { name: /send/i }))
    await waitFor(() => expect(screen.getByText('Hello MYCA')).toBeInTheDocument())
  })
}) 