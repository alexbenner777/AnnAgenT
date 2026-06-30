import { useState } from 'react'
import { Send, Sparkles } from 'lucide-react'
import { motion } from 'framer-motion'
import GlassCard from '../components/GlassCard'
import PageHeader from '../components/PageHeader'

function haptic(s: 'light' | 'medium' = 'light') {
  window.Telegram?.WebApp?.HapticFeedback?.impactOccurred(s)
}

interface Message {
  id: number
  text: string
  from: 'user' | 'system'
  ts: string
}

export default function AskPage() {
  const [input, setInput] = useState('')
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 0,
      text: 'Привет! Здесь ты можешь задать вопрос или оставить заметку. Бот-ассистент скоро будет подключён.',
      from: 'system',
      ts: new Date().toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' }),
    },
  ])

  const handleSend = () => {
    if (!input.trim()) return
    haptic('light')
    const now = new Date().toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' })
    const userMsg: Message = { id: Date.now(), text: input.trim(), from: 'user', ts: now }
    setMessages(prev => [...prev, userMsg])
    setInput('')

    // Stub response
    setTimeout(() => {
      setMessages(prev => [
        ...prev,
        {
          id: Date.now() + 1,
          text: '⏳ Функция в разработке. Бот ответит, когда будет подключён к системе.',
          from: 'system',
          ts: new Date().toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' }),
        },
      ])
    }, 600)
  }

  const handleKey = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="px-4 pt-6 pb-3 flex-shrink-0">
        <PageHeader
          title="Спросить"
          subtitle="Вопросы и заметки для ассистента"
        />
      </div>

      {/* Message list */}
      <div className="flex-1 overflow-y-auto px-4 pb-4 space-y-3">
        {messages.map((msg, i) => (
          <motion.div
            key={msg.id}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i === 0 ? 0 : 0, duration: 0.25 }}
            className={`flex ${msg.from === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            {msg.from === 'system' && (
              <div className="w-8 h-8 rounded-full bg-accent/10 flex items-center justify-center mr-2 flex-shrink-0 mt-0.5">
                <Sparkles size={14} className="text-accent" />
              </div>
            )}
            <div
              className={`max-w-[78%] rounded-2xl px-4 py-3 ${
                msg.from === 'user'
                  ? 'bg-accent text-white rounded-br-sm'
                  : 'bg-white/80 backdrop-blur text-gray-800 rounded-bl-sm shadow-sm border border-white/60'
              }`}
            >
              <p className="text-sm leading-relaxed">{msg.text}</p>
              <p className={`text-[10px] mt-1 ${msg.from === 'user' ? 'text-white/60' : 'text-gray-400'}`}>
                {msg.ts}
              </p>
            </div>
          </motion.div>
        ))}
      </div>

      {/* Input bar */}
      <div className="flex-shrink-0 px-4 pb-32 pt-2">
        <GlassCard className="p-2 flex items-end gap-2">
          <textarea
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKey}
            placeholder="Написать вопрос..."
            rows={1}
            className="flex-1 bg-transparent resize-none outline-none text-sm text-gray-800 placeholder:text-gray-400 px-2 py-2 max-h-32"
            style={{ lineHeight: '1.5' }}
          />
          <button
            onClick={handleSend}
            disabled={!input.trim()}
            className={`w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0 transition-all ${
              input.trim()
                ? 'bg-accent text-white active:scale-95'
                : 'bg-gray-100 text-gray-300'
            }`}
          >
            <Send size={16} />
          </button>
        </GlassCard>
      </div>
    </div>
  )
}
