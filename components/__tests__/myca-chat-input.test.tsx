import { render, screen, fireEvent } from '@testing-library/react'
import { MycaChatInput } from '../myca-chat-input'

describe('MycaChatInput', () => {
  it('renders input and send button', () => {
    render(<MycaChatInput onSend={() => {}} />)
    expect(screen.getByPlaceholderText('Type a message or command for MYCA...')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /send/i })).toBeInTheDocument()
  })

  it('calls onSend when form is submitted', () => {
    const handleSend = jest.fn()
    render(<MycaChatInput onSend={handleSend} />)
    fireEvent.change(screen.getByPlaceholderText('Type a message or command for MYCA...'), { target: { value: 'Hello' } })
    fireEvent.click(screen.getByRole('button', { name: /send/i }))
    expect(handleSend).toHaveBeenCalledWith('Hello')
  })

  it('disables input and button when loading', () => {
    render(<MycaChatInput onSend={() => {}} isLoading />)
    expect(screen.getByPlaceholderText('Type a message or command for MYCA...')).toBeDisabled()
    expect(screen.getByRole('button', { name: /send/i })).toBeDisabled()
  })
}) 