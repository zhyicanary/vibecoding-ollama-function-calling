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
    <div className="app-container">
      <div className="scanlines" />
      
      <div className="connection-status">
        <div className={`connection-dot ${connectionStatus}`} />
        <span>Ollama: {getStatusText()}</span>
      </div>

      <div className="avatar-section">
        <div className="avatar-container">
          <div className="avatar-glow" />
          <div className="avatar-ring" />
          <div className="avatar-image">
            <div className="avatar-eyes">
              <div className="avatar-eye" />
              <div className="avatar-eye" />
            </div>
            <div className={`avatar-mouth ${isSpeaking ? 'speaking' : ''}`} style={{ transform: `scaleY(${0.3 + mouthOpen * 0.7})` }} />
          </div>
        </div>
        <div className="avatar-name">AIRA</div>
        <div className="status-badge">
          <div className={`status-dot ${isSpeaking ? 'speaking' : isListening ? 'listening' : ''}`} />
          <span>{isSpeaking ? '正在说话' : isListening ? '正在聆听' : '智能助手'}</span>
        </div>
      </div>

      <div className="chat-section">
        <div className="chat-header">
          <div className="header-left">
            <h1 className="chat-title">对话</h1>
            <div className="model-selector">
              <select 
                value={currentModel} 
                onChange={(e) => switchModel(e.target.value)}
                disabled={isLoading}
              >
                {models.map(model => (
                  <option key={model} value={model}>{model}</option>
                ))}
              </select>
            </div>
          </div>
          <div className="header-actions">
            <button className="header-btn" onClick={() => setShowSettings(!showSettings)}>
              ⚙️ 设置
            </button>
            <button className="header-btn" onClick={fetchModels}>
              刷新模型
            </button>
            <button className="header-btn danger" onClick={clearHistory}>
              清空对话
            </button>
          </div>
        </div>

        {showSettings && (
          <div className="settings-panel">
            <div className="settings-group">
              <label>语音语言</label>
              <select value={voiceLanguage} onChange={(e) => setVoiceLanguage(e.target.value)}>
                {LANGUAGES.map(lang => (
                  <option key={lang.code} value={lang.code}>{lang.name}</option>
                ))}
              </select>
            </div>
            <div className="settings-group">
              <label>
                <input type="checkbox" checked={ttsEnabled} onChange={(e) => setTtsEnabled(e.target.checked)} />
                启用语音回答
              </label>
            </div>
            <div className="settings-group">
              <label>语速: {ttsSpeed.toFixed(1)}x</label>
              <input type="range" min="0.5" max="2" step="0.1" value={ttsSpeed} onChange={(e) => setTtsSpeed(parseFloat(e.target.value))} />
            </div>
            <div className="settings-group">
              <label>音量: {Math.round(ttsVolume * 100)}%</label>
              <input type="range" min="0" max="1" step="0.1" value={ttsVolume} onChange={(e) => setTtsVolume(parseFloat(e.target.value))} />
            </div>
            <div className="settings-group">
              <label>音调: {ttsPitch.toFixed(1)}</label>
              <input type="range" min="0.5" max="2" step="0.1" value={ttsPitch} onChange={(e) => setTtsPitch(parseFloat(e.target.value))} />
            </div>
          </div>
        )}

        <div className="messages-container">
          {messages.length === 0 ? (
            <div className="empty-state">
              <div className="empty-icon">◈</div>
              <p className="empty-text">
                开始与AI数字人助手对话吧
              </p>
            </div>
          ) : (
            messages.map((msg, idx) => (
              <div key={idx} className={`message ${msg.role}`}>
                <div className="message-avatar">
                  {msg.role === 'user' ? 'U' : msg.role === 'tool' ? '🔧' : 'AI'}
                </div>
                <div className="message-content">
                  <ReactMarkdown>{msg.content}</ReactMarkdown>
                </div>
              </div>
            ))
          )}
          
          {isLoading && (
            <div className="message ai">
              <div className="message-avatar">AI</div>
              <div className="message-content">
                <div className="loading-indicator">
                  <div className="loading-dot" />
                  <div className="loading-dot" />
                  <div className="loading-dot" />
                </div>
              </div>
            </div>
          )}
          
          <div ref={messagesEndRef} />
        </div>

        <form className="input-container" onSubmit={sendMessage}>
          <div className="voice-controls">
            <button 
              type="button"
              className={`voice-btn ${isListening ? 'listening' : ''}`}
              onMouseDown={startListening}
              onMouseUp={stopListening}
              onMouseLeave={stopListening}
              onTouchStart={(e) => { e.preventDefault(); startListening() }}
              onTouchEnd={(e) => { e.preventDefault(); stopListening() }}
              title="按住说话"
            >
              <svg viewBox="0 0 24 24">
                <path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3z"/>
                <path d="M17 11c0 2.76-2.24 5-5 5s-5-2.24-5-5H5c0 3.53 2.61 6.43 6 6.92V21h2v-3.08c3.39-.49 6-3.39 6-6.92h-2z"/>
              </svg>
            </button>
            {isListening && <div className="voice-wave" />}
            
            <button 
              type="button"
              className={`voice-btn speak-btn ${isSpeaking ? 'speaking' : ''}`}
              onClick={isSpeaking ? stopSpeaking : () => speak(input || messages[messages.length - 1]?.content)}
              disabled={!ttsEnabled && !isSpeaking}
              title={isSpeaking ? "停止说话" : "语音回答"}
            >
              <svg viewBox="0 0 24 24">
                <path d="M3 9v6h4l5 5V4L7 9H3z"/>
                <path d="M16.5 12c0-1.77-1.02-3.29-2.5-4.03v8.05c1.48-.73 2.5-2.25 2.5-4.02z"/>
              </svg>
            </button>
          </div>
          
          <div className="input-wrapper">
            <textarea
              className="message-input"
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
              <svg viewBox="0 0 24 24">
                <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/>
              </svg>
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

export default App
