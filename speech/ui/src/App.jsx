import React, { useState, useRef, useEffect, useCallback } from 'react'
import './App.css'

const GATEWAY_URL = import.meta.env.VITE_GATEWAY_URL || 'http://localhost:8002'

function App() {
  const [isRecording, setIsRecording] = useState(false)
  const [isProcessing, setIsProcessing] = useState(false)
  const [transcript, setTranscript] = useState('')
  const [mycaResponse, setMycaResponse] = useState('')
  const [conversation, setConversation] = useState([])
  const [micLevel, setMicLevel] = useState(0)
  const [settings, setSettings] = useState({
    voiceEnabled: true,
    voice: 'alloy',
    storeAudio: false,
    wakeWordEnabled: false,
    provider: 'openai'
  })
  const [availableVoices, setAvailableVoices] = useState([])
  const [error, setError] = useState(null)

  const mediaRecorderRef = useRef(null)
  const audioChunksRef = useRef([])
  const audioContextRef = useRef(null)
  const analyserRef = useRef(null)
  const animationFrameRef = useRef(null)
  const spacePressedRef = useRef(false)

  // Load available voices
  useEffect(() => {
    fetch(`${GATEWAY_URL}/voices`)
      .then(res => res.json())
      .then(data => setAvailableVoices(data.voices || []))
      .catch(err => console.error('Failed to load voices:', err))
  }, [])

  // Keyboard handler for Spacebar
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.code === 'Space' && !spacePressedRef.current && !isProcessing) {
        e.preventDefault()
        spacePressedRef.current = true
        startRecording()
      }
    }

    const handleKeyUp = (e) => {
      if (e.code === 'Space' && spacePressedRef.current) {
        e.preventDefault()
        spacePressedRef.current = false
        stopRecording()
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    window.addEventListener('keyup', handleKeyUp)

    return () => {
      window.removeEventListener('keydown', handleKeyDown)
      window.removeEventListener('keyup', handleKeyUp)
    }
  }, [isProcessing])

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current)
      }
      if (audioContextRef.current) {
        audioContextRef.current.close()
      }
    }
  }, [])

  const startRecording = async () => {
    try {
      setError(null)
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      
      // Setup audio analysis for mic level
      audioContextRef.current = new AudioContext()
      const source = audioContextRef.current.createMediaStreamSource(stream)
      analyserRef.current = audioContextRef.current.createAnalyser()
      analyserRef.current.fftSize = 256
      source.connect(analyserRef.current)

      // Start mic level monitoring
      const updateMicLevel = () => {
        if (!analyserRef.current) return
        
        const dataArray = new Uint8Array(analyserRef.current.frequencyBinCount)
        analyserRef.current.getByteFrequencyData(dataArray)
        const average = dataArray.reduce((a, b) => a + b) / dataArray.length
        setMicLevel(Math.min(100, (average / 255) * 100))
        
        if (isRecording) {
          animationFrameRef.current = requestAnimationFrame(updateMicLevel)
        }
      }
      updateMicLevel()

      // Setup MediaRecorder
      const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
        ? 'audio/webm;codecs=opus'
        : MediaRecorder.isTypeSupported('audio/webm')
        ? 'audio/webm'
        : 'audio/ogg;codecs=opus'

      const mediaRecorder = new MediaRecorder(stream, { mimeType })
      mediaRecorderRef.current = mediaRecorder
      audioChunksRef.current = []

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data)
        }
      }

      mediaRecorder.onstop = () => {
        stream.getTracks().forEach(track => track.stop())
        processAudio()
      }

      mediaRecorder.start()
      setIsRecording(true)
    } catch (err) {
      setError(`Failed to start recording: ${err.message}`)
      console.error('Recording error:', err)
    }
  }

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop()
      setIsRecording(false)
      setMicLevel(0)
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current)
      }
    }
  }

  const processAudio = async () => {
    setIsProcessing(true)
    setError(null)

    try {
      const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' })
      const formData = new FormData()
      formData.append('audio', audioBlob, 'audio.webm')
      formData.append('store_audio', settings.storeAudio.toString())
      formData.append('wake_word_enabled', settings.wakeWordEnabled.toString())
      formData.append('provider', settings.provider)
      formData.append('voice', settings.voice)

      const response = await fetch(`${GATEWAY_URL}/speech/turn`, {
        method: 'POST',
        body: formData
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }))
        throw new Error(errorData.detail || `HTTP ${response.status}`)
      }

      const data = await response.json()

      // Update transcript and response
      const userTurn = { role: 'user', text: data.transcript, timestamp: new Date() }
      const mycaTurn = { role: 'myca', text: data.myca_text, timestamp: new Date() }

      setTranscript(data.transcript)
      setMycaResponse(data.myca_text)
      setConversation(prev => [...prev, userTurn, mycaTurn])

      // Play TTS audio if available
      if (data.tts_audio_base64 && settings.voiceEnabled) {
        const audioData = Uint8Array.from(atob(data.tts_audio_base64), c => c.charCodeAt(0))
        const audioBlob = new Blob([audioData], { type: 'audio/mpeg' })
        const audioUrl = URL.createObjectURL(audioBlob)
        const audio = new Audio(audioUrl)
        audio.play().catch(err => console.error('Audio play failed:', err))
        audio.onended = () => URL.revokeObjectURL(audioUrl)
      }

      // Handle confirmation requirement
      if (data.require_confirm) {
        setError(`⚠️ Destructive action detected. Please confirm: "Confirm action request_id ${data.request_id}"`)
      }
    } catch (err) {
      setError(`Processing failed: ${err.message}`)
      console.error('Processing error:', err)
    } finally {
      setIsProcessing(false)
      audioChunksRef.current = []
    }
  }

  const handleMouseDown = () => {
    if (!isProcessing && !isRecording) {
      startRecording()
    }
  }

  const handleMouseUp = () => {
    if (isRecording) {
      stopRecording()
    }
  }

  return (
    <div className="app">
      <div className="container">
        <header>
          <h1>🎤 MYCA Speech Interface</h1>
          <p className="subtitle">Push-to-Talk Voice Assistant</p>
        </header>

        <div className="main-content">
          {/* Status Panel */}
          <div className="status-panel">
            <div className="status-item">
              <span className="status-label">Status:</span>
              <span className={`status-value ${isRecording ? 'recording' : isProcessing ? 'processing' : 'idle'}`}>
                {isRecording ? '🎤 Recording...' : isProcessing ? '⚙️ Processing...' : '✅ Ready'}
              </span>
            </div>
            <div className="status-item">
              <span className="status-label">Mic Level:</span>
              <div className="mic-level-bar">
                <div 
                  className="mic-level-fill" 
                  style={{ width: `${micLevel}%` }}
                />
              </div>
            </div>
          </div>

          {/* Push-to-Talk Button */}
          <div className="ptt-section">
            <button
              className={`ptt-button ${isRecording ? 'recording' : ''} ${isProcessing ? 'processing' : ''}`}
              onMouseDown={handleMouseDown}
              onMouseUp={handleMouseUp}
              onMouseLeave={handleMouseUp}
              disabled={isProcessing}
            >
              {isRecording ? '🎤 Recording...' : isProcessing ? '⚙️ Processing...' : '🎤 Hold to Talk'}
            </button>
            <p className="ptt-hint">Hold button or press <kbd>Spacebar</kbd> to talk</p>
          </div>

          {/* Error Display */}
          {error && (
            <div className="error-message">
              {error}
            </div>
          )}

          {/* Conversation Transcript */}
          <div className="transcript-section">
            <h2>Conversation</h2>
            <div className="transcript-container">
              {conversation.length === 0 ? (
                <p className="empty-transcript">No conversation yet. Start talking!</p>
              ) : (
                conversation.map((turn, idx) => (
                  <div key={idx} className={`transcript-turn ${turn.role}`}>
                    <span className="turn-role">{turn.role === 'user' ? '👤 You' : '🤖 MYCA'}</span>
                    <span className="turn-text">{turn.text}</span>
                    <span className="turn-time">{turn.timestamp.toLocaleTimeString()}</span>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Settings Panel */}
          <div className="settings-panel">
            <h2>Settings</h2>
            <div className="settings-grid">
              <label>
                <input
                  type="checkbox"
                  checked={settings.voiceEnabled}
                  onChange={(e) => setSettings({ ...settings, voiceEnabled: e.target.checked })}
                />
                Voice Enabled
              </label>
              <label>
                <input
                  type="checkbox"
                  checked={settings.storeAudio}
                  onChange={(e) => setSettings({ ...settings, storeAudio: e.target.checked })}
                />
                Store Raw Audio
              </label>
              <label>
                <input
                  type="checkbox"
                  checked={settings.wakeWordEnabled}
                  onChange={(e) => setSettings({ ...settings, wakeWordEnabled: e.target.checked })}
                />
                Wake Word Required ("Myca")
              </label>
              <label>
                Voice:
                <select
                  value={settings.voice}
                  onChange={(e) => setSettings({ ...settings, voice: e.target.value })}
                >
                  {availableVoices.map(v => (
                    <option key={v.id} value={v.id}>{v.name}</option>
                  ))}
                </select>
              </label>
              <label>
                Provider:
                <select
                  value={settings.provider}
                  onChange={(e) => setSettings({ ...settings, provider: e.target.value })}
                >
                  <option value="openai">OpenAI (Whisper + TTS)</option>
                  <option value="browser" disabled>Browser (Coming Soon)</option>
                </select>
              </label>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default App
