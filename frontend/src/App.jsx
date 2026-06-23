import { useState, useEffect, useRef, useCallback } from 'react'
import ReactMarkdown from 'react-markdown'

const API_BASE = '/api'

const LANGUAGES = [
  { code: 'zh-CN', name: '中文(普通话)', dialect: false },
  { code: 'zh-TW', name: '中文(繁体)', dialect: false },
  { code: 'zh-HK', name: '中文(粤语)', dialect: true },
  { code: 'zh-Sichuan', name: '中文(四川话)', dialect: true },
  { code: 'en-US', name: 'English', dialect: false },
  { code: 'ja-JP', name: '日本語', dialect: false },
  { code: 'es-ES', name: 'Español', dialect: false },
  { code: 'fr-FR', name: 'Français', dialect: false },
]

const TTS_VOICES = {
  'zh-CN': 'zh-CN-XiaoxiaoNeural',
  'zh-TW': 'zh-TW-YatingNeural',
  'zh-HK': 'zh-HK-HiuGaaiNeural',
  'zh-Sichuan': 'zh-CN-YunxiNeural',
  'en-US': 'en-US-JennyNeural',
  'ja-JP': 'ja-JP-NanamiNeural',
  'es-ES': 'es-ES-ElviraNeural',
  'fr-FR': 'fr-FR-DeniseNeural',
}

function App() {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [connectionStatus, setConnectionStatus] = useState('connecting')
  const [models, setModels] = useState([])
  const [currentModel, setCurrentModel] = useState('')
  
  const [isListening, setIsListening] = useState(false)
  const [isSpeaking, setIsSpeaking] = useState(false)
  const [voiceLanguage, setVoiceLanguage] = useState('zh-CN')
  const [ttsEnabled, setTtsEnabled] = useState(true)
  const [ttsSpeed, setTtsSpeed] = useState(1)
  const [ttsVolume, setTtsVolume] = useState(1)
  const [ttsPitch, setTtsPitch] = useState(1)
  const [mouthOpen, setMouthOpen] = useState(0)
  const [showSettings, setShowSettings] = useState(false)
  
  const messagesEndRef = useRef(null)
  const recognitionRef = useRef(null)
  const speechSynthesisRef = useRef(null)
  const animationRef = useRef(null)

  useEffect(() => {
    checkHealth()
    fetchModels()
    initSpeechRecognition()
    const interval = setInterval(checkHealth, 30000)
    return () => {
      clearInterval(interval)
      if (recognitionRef.current) {
        recognitionRef.current.stop()
      }
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current)
      }
      window.speechSynthesis.cancel()
    }
  }, [])

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const initSpeechRecognition = () => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition
    if (!SpeechRecognition) {
      console.warn('Speech recognition not supported')
      return
    }
    
    recognitionRef.current = new SpeechRecognition()
    recognitionRef.current.continuous = false
    recognitionRef.current.interimResults = true
    recognitionRef.current.lang = voiceLanguage
    
    recognitionRef.current.onresult = (event) => {
      const transcript = Array.from(event.results)
        .map(result => result[0].transcript)
        .join('')
      
      if (event.results[0].isFinal) {
        setInput(transcript)
      }
    }
    
    recognitionRef.current.onstart = () => {
      setIsListening(true)
    }
    
    recognitionRef.current.onend = () => {
      setIsListening(false)
    }
    
    recognitionRef.current.onerror = (event) => {
      console.error('Speech recognition error:', event.error)
      setIsListening(false)
    }
  }

  const checkHealth = async () => {
    try {
      const res = await fetch(`${API_BASE}/health`)
      const data = await res.json()
      setConnectionStatus(data.ollama === 'connected' ? 'connected' : 'disconnected')
    } catch {
      setConnectionStatus('disconnected')
    }
  }

  const fetchModels = async () => {
    try {
      const res = await fetch(`${API_BASE}/models`)
      const data = await res.json()
      if (data.models && data.models.length > 0) {
        setModels(data.models)
        if (!currentModel) setCurrentModel(data.models[0])
      }
    } catch (err) {
      console.error('Failed to fetch models:', err)
    }
  }

  const switchModel = async (modelName) => {
    setCurrentModel(modelName)
    setMessages([])
    try {
      await fetch(`${API_BASE}/clear`, { method: 'POST' })
    } catch (err) {
      console.error('Clear failed:', err)
    }
  }

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  const startListening = () => {
    if (recognitionRef.current) {
      recognitionRef.current.lang = voiceLanguage
      try {
        recognitionRef.current.start()
      } catch (e) {
        console.error('Start recognition failed:', e)
      }
    }
  }

  const stopListening = () => {
    if (recognitionRef.current && isListening) {
      recognitionRef.current.stop()
    }
  }

  const speak = (text) => {
    if (!ttsEnabled || !text) return
    
    window.speechSynthesis.cancel()
    
    const utterance = new SpeechSynthesisUtterance(text)
    utterance.lang = voiceLanguage
    utterance.rate = ttsSpeed
    utterance.volume = ttsVolume
    utterance.pitch = ttsPitch
    
    const lipSyncAnimation = () => {
      let startTime = null
      const duration = 2000
      
      const animate = (timestamp) => {
        if (!startTime) startTime = timestamp
        const elapsed = timestamp - startTime
        
        if (elapsed < duration) {
          const progress = elapsed / duration
          const open = Math.sin(progress * Math.PI * 8) * 0.5 + 0.3 + Math.random() * 0.2
          setMouthOpen(Math.max(0, Math.min(1, open)))
          animationRef.current = requestAnimationFrame(animate)
        } else {
          setMouthOpen(0)
        }
      }
      animationRef.current = requestAnimationFrame(animate)
    }
    
    utterance.onstart = () => {
      setIsSpeaking(true)
      lipSyncAnimation()
    }
    
    utterance.onend = () => {
      setIsSpeaking(false)
      setMouthOpen(0)
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current)
      }
    }
    
    utterance.onerror = () => {
      setIsSpeaking(false)
      setMouthOpen(0)
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current)
      }
    }
    
    speechSynthesisRef.current = utterance
    window.speechSynthesis.speak(utterance)
  }

  const stopSpeaking = () => {
    window.speechSynthesis.cancel()
    setIsSpeaking(false)
    setMouthOpen(0)
    if (animationRef.current) {
      cancelAnimationFrame(animationRef.current)
    }
  }

  const sendMessage = async (e) => {
    e.preventDefault()
    if (!input.trim() || isLoading) return

    const userMessage = input.trim()
    setInput('')
    setIsLoading(true)

    setMessages(prev => [...prev, { role: 'user', content: userMessage }])

    try {
      const res = await fetch(`${API_BASE}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          message: userMessage,
          model: currentModel || undefined
        })
      })

      if (!res.ok) {
        setMessages(prev => [...prev, { 
          role: 'ai', 
          content: `请求失败: ${res.status}` 
        }])
        setIsLoading(false)
        return
      }

      const data = await res.json()

      if (data.success) {
        setMessages(prev => {
          const newMessages = [...prev, { role: 'ai', content: data.response }]
          if (data.tool_used && data.tool_calls) {
            data.tool_calls.forEach(tool => {
              newMessages.push({ 
                role: 'tool', 
                content: `[调用工具: ${tool.name}] ${tool.result}`,
                toolName: tool.name 
              })
            })
          }
          return newMessages
        })
        
        if (ttsEnabled && data.response) {
          speak(data.response)
        }
        
        setIsLoading(false)
      } else {
        setMessages(prev => [...prev, { 
          role: 'ai', 
          content: `错误: ${data.error || '未知错误'}` 
        }])
        setIsLoading(false)
      }
    } catch (err) {
      console.error('Fetch error:', err)
      setMessages(prev => [...prev, { 
        role: 'ai', 
        content: `网络错误: ${err.message}` 
      }])
      setIsLoading(false)
    }
  }

  const clearHistory = async () => {
    try {
      await fetch(`${API_BASE}/clear`, { method: 'POST' })
      setMessages([])
    } catch (err) {
      console.error('Clear failed:', err)
    }
  }

  const getStatusText = () => {
    switch (connectionStatus) {
      case 'connected': return '在线'
      case 'disconnected': return '离线'
      default: return '连接中'
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage(e)
    }
  }

  return (
    <div className="app">

      {/* ── Top Bar ── */}
      <header className="top-bar">
        <div className="connection-indicator">
          <span className={`status-dot ${connectionStatus}`} />
          <span className="status-label">Ollama {getStatusText()}</span>
        </div>
        <button
          className="settings-toggle"
          onClick={() => setShowSettings(!showSettings)}
          title="设置"
        >
          <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor">
            <path d="M19.14 12.94c.04-.3.06-.61.06-.94 0-.32-.02-.64-.07-.94l2.03-1.58a.49.49 0 00.12-.61l-1.92-3.32a.488.488 0 00-.59-.22l-2.39.96c-.5-.38-1.03-.7-1.62-.94l-.36-2.54a.484.484 0 00-.48-.41h-3.84c-.24 0-.43.17-.47.41l-.36 2.54c-.59.24-1.13.57-1.62.94l-2.39-.96c-.22-.08-.47 0-.59.22L2.74 8.87c-.12.21-.08.47.12.61l2.03 1.58c-.05.3-.07.63-.07.94s.02.64.07.94l-2.03 1.58a.49.49 0 00-.12.61l1.92 3.32c.12.22.37.29.59.22l2.39-.96c.5.38 1.03.7 1.62.94l.36 2.54c.05.24.24.41.48.41h3.84c.24 0 .44-.17.47-.41l.36-2.54c.59-.24 1.13-.56 1.62-.94l2.39.96c.22.08.47 0 .59-.22l1.92-3.32c.12-.22.07-.47-.12-.61l-2.01-1.58zM12 15.6A3.6 3.6 0 1115.6 12 3.611 3.611 0 0112 15.6z"/>
          </svg>
        </button>
      </header>

      {/* ── Settings Overlay ── */}
      {showSettings && (
        <div className="settings-backdrop" onClick={() => setShowSettings(false)}>
          <div className="settings-drawer" onClick={e => e.stopPropagation()}>
            <div className="settings-drawer-header">
              <h2 className="settings-title">设置</h2>
              <button className="settings-close" onClick={() => setShowSettings(false)}>
                <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor">
                  <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/>
                </svg>
              </button>
            </div>
            <div className="settings-drawer-body">
              <div className="setting-row">
                <label className="setting-label">语音语言</label>
                <select value={voiceLanguage} onChange={(e) => setVoiceLanguage(e.target.value)}>
                  {LANGUAGES.map(lang => (
                    <option key={lang.code} value={lang.code}>{lang.name}</option>
                  ))}
                </select>
              </div>
              <div className="setting-row setting-row-checkbox">
                <label className="setting-checkbox">
                  <input type="checkbox" checked={ttsEnabled} onChange={(e) => setTtsEnabled(e.target.checked)} />
                  <span className="checkbox-mark" />
                  <span>启用语音回答</span>
                </label>
              </div>
              <div className="setting-row">
                <label className="setting-label">语速 <span className="setting-value">{ttsSpeed.toFixed(1)}x</span></label>
                <input type="range" min="0.5" max="2" step="0.1" value={ttsSpeed} onChange={(e) => setTtsSpeed(parseFloat(e.target.value))} />
              </div>
              <div className="setting-row">
                <label className="setting-label">音量 <span className="setting-value">{Math.round(ttsVolume * 100)}%</span></label>
                <input type="range" min="0" max="1" step="0.1" value={ttsVolume} onChange={(e) => setTtsVolume(parseFloat(e.target.value))} />
              </div>
              <div className="setting-row">
                <label className="setting-label">音调 <span className="setting-value">{ttsPitch.toFixed(1)}</span></label>
                <input type="range" min="0.5" max="2" step="0.1" value={ttsPitch} onChange={(e) => setTtsPitch(parseFloat(e.target.value))} />
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ── Hero / Avatar ── */}
      <section className="hero">
        <div className="avatar-figure">
          <div className="avatar-eyes">
            <div className="eye" />
            <div className="eye" />
          </div>
          <div
            className="avatar-mouth"
            style={{ transform: `scaleY(${0.3 + mouthOpen * 0.7})` }}
          >
            <div className="mouth-line" />
          </div>
        </div>
        <h1 className="character-name">小智</h1>
        <p className="character-role">
          {isSpeaking ? '正在说话' : isListening ? '正在聆听' : '智能助手'}
        </p>
      </section>

      {/* ── Controls ── */}
      <div className="controls">
        <div className="model-group">
          <label className="model-label">模型</label>
          <select
            className="model-select"
            value={currentModel}
            onChange={(e) => switchModel(e.target.value)}
            disabled={isLoading}
          >
            {models.map(model => (
              <option key={model} value={model}>{model}</option>
            ))}
          </select>
        </div>
        <div className="action-group">
          <button className="action-btn" onClick={fetchModels} title="刷新模型">
            <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor">
              <path d="M17.65 6.35A7.958 7.958 0 0012 4c-4.42 0-7.99 3.58-7.99 8s3.57 8 7.99 8c3.73 0 6.84-2.55 7.73-6h-2.08A5.99 5.99 0 0112 18c-3.31 0-6-2.69-6-6s2.69-6 6-6c1.66 0 3.14.69 4.22 1.78L13 11h7V4l-2.35 2.35z"/>
            </svg>
          </button>
          <button className="action-btn action-btn--danger" onClick={clearHistory} title="清空对话">
            <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor">
              <path d="M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zm2.46-7.12l1.41-1.41L12 12.59l2.12-2.12 1.41 1.41L13.41 14l2.12 2.12-1.41 1.41L12 15.41l-2.12 2.12-1.41-1.41L10.59 14l-2.13-2.12zM15.5 4l-1-1h-5l-1 1H5v2h14V4h-3.5z"/>
            </svg>
          </button>
        </div>
      </div>

      {/* ── Messages ── */}
      <main className="messages">
        {messages.length === 0 ? (
          <div className="empty">
            <div className="empty-symbol">✻</div>
            <p className="empty-text">开始与小智对话吧</p>
            <p className="empty-hint">输入消息或按住麦克风按钮说话</p>
          </div>
        ) : (
          messages.map((msg, idx) => (
            <div key={idx} className={`message message--${msg.role}`}>
              <div className={`message-badge message-badge--${msg.role}`}>
                {msg.role === 'user' ? 'U' : msg.role === 'tool' ? '⚒' : 'AI'}
              </div>
              <div className="message-bubble">
                <ReactMarkdown>{msg.content}</ReactMarkdown>
              </div>
            </div>
          ))
        )}

        {isLoading && (
          <div className="message message--ai">
            <div className="message-badge message-badge--ai">AI</div>
            <div className="message-bubble">
              <div className="loading">
                <div className="loading-dot" />
                <div className="loading-dot" />
                <div className="loading-dot" />
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </main>

      {/* ── Input ── */}
      <form className="input-bar" onSubmit={sendMessage}>
        <div className="voice-actions">
          <button
            type="button"
            className={`voice-btn ${isListening ? 'voice-btn--active' : ''}`}
            onMouseDown={startListening}
            onMouseUp={stopListening}
            onMouseLeave={stopListening}
            onTouchStart={(e) => { e.preventDefault(); startListening() }}
            onTouchEnd={(e) => { e.preventDefault(); stopListening() }}
            title="按住说话"
          >
            <svg viewBox="0 0 24 24" width="22" height="22" fill="currentColor">
              <path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3z"/>
              <path d="M17 11c0 2.76-2.24 5-5 5s-5-2.24-5-5H5c0 3.53 2.61 6.43 6 6.92V21h2v-3.08c3.39-.49 6-3.39 6-6.92h-2z"/>
            </svg>
          </button>
          {isListening && <div className="voice-ring" />}

          <button
            type="button"
            className={`voice-btn speak-btn ${isSpeaking ? 'voice-btn--speaking' : ''}`}
            onClick={isSpeaking ? stopSpeaking : () => speak(input || messages[messages.length - 1]?.content)}
            disabled={!ttsEnabled && !isSpeaking}
            title={isSpeaking ? "停止说话" : "语音回答"}
          >
            <svg viewBox="0 0 24 24" width="22" height="22" fill="currentColor">
              <path d="M3 9v6h4l5 5V4L7 9H3z"/>
              <path d="M16.5 12c0-1.77-1.02-3.29-2.5-4.03v8.05c1.48-.73 2.5-2.25 2.5-4.02z"/>
            </svg>
          </button>
        </div>

        <div className="input-group">
          <textarea
            className="text-input"
            placeholder="输入消息..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            rows={1}
          />
          <button
            type="submit"
            className="send-btn"
            disabled={isLoading || !input.trim()}
          >
            <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor">
              <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/>
            </svg>
          </button>
        </div>
      </form>

    </div>
  )
}

export default App
