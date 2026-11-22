/**
 * AITutorPanel — Socratic AI Programming Tutor.
 * Provides conceptual intuition, algorithm logic, and syntax hints without giving away solutions.
 */

import { useState, useRef, useEffect } from 'react'
import ReactMarkdown from 'react-markdown'
import { askAITutor, Language } from '../api/client'

interface AITutorPanelProps {
  problemSlug: string
  problemTitle: string
  currentCode: string
  currentLanguage: Language
}

interface Message {
  id: string
  sender: 'student' | 'tutor'
  text: string
  timestamp: string
  model?: string
  isLive?: boolean
}

const PRESET_PROMPTS = [
  '💡 Explain the logic in simple terms',
  '🔍 What edge cases should I consider?',
  '⏱️ What time complexity should I aim for?',
  '🛠️ How should I structure my data structures?',
]

export default function AITutorPanel({
  problemSlug,
  problemTitle,
  currentCode,
  currentLanguage,
}: AITutorPanelProps) {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 'welcome',
      sender: 'tutor',
      text: `👋 Hi! I'm your **CodeForge AI Tutor** for **${problemTitle}**.\n\nI can help you understand the problem's underlying logic, think through algorithmic steps, or clarify language syntax.`,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    },
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [includeCode, setIncludeCode] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const messagesEndRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages, loading])

  const handleSend = async (userText?: string) => {
    const textToSend = (userText || input).trim()
    if (!textToSend || loading) return

    setError(null)
    const userMsg: Message = {
      id: 'user-' + Date.now(),
      sender: 'student',
      text: textToSend,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    }

    setMessages((prev) => [...prev, userMsg])
    if (!userText) setInput('')
    setLoading(true)

    try {
      const res = await askAITutor(
        problemSlug,
        textToSend,
        includeCode ? currentCode : undefined,
        currentLanguage
      )

      const tutorMsg: Message = {
        id: 'tutor-' + Date.now(),
        sender: 'tutor',
        text: res.reply,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        model: res.model,
        isLive: res.is_live,
      }
      setMessages((prev) => [...prev, tutorMsg])
    } catch (err: any) {
      console.error(err)
      const detail = err.response?.data?.detail || 'Failed to reach AI Tutor. Please try again.'
      setError(detail)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex flex-col h-full bg-white dark:bg-zinc-950 text-zinc-900 dark:text-zinc-100 font-sans transition-colors">
      {/* Header */}
      <div className="px-5 py-3.5 border-b border-zinc-200 dark:border-zinc-800 flex items-center justify-between shrink-0 bg-zinc-50 dark:bg-zinc-900/40">
        <div className="flex items-center gap-2">
          <span className="text-lg">🤖</span>
          <div>
            <h2 className="text-xs font-bold uppercase tracking-wider text-zinc-900 dark:text-white flex items-center gap-1.5">
              <span>Socratic AI Tutor</span>
              <span className="text-[10px] px-1.5 py-0.2 rounded-full bg-orange-500/10 text-orange-600 dark:text-orange-400 font-mono">
                {currentLanguage.toUpperCase()}
              </span>
            </h2>
            <p className="text-[11px] text-zinc-500">Conceptual logic & edge cases</p>
          </div>
        </div>

        <div className="flex items-center gap-1 text-[11px] font-mono text-zinc-400">
          <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
          <span>Active</span>
        </div>
      </div>

      {/* Preset Prompt Chips */}
      <div className="px-4 py-2 border-b border-zinc-100 dark:border-zinc-900 bg-white dark:bg-zinc-950 flex flex-wrap gap-1.5 shrink-0">
        {PRESET_PROMPTS.map((prompt) => (
          <button
            key={prompt}
            onClick={() => handleSend(prompt)}
            disabled={loading}
            className="text-[11px] px-2.5 py-1 rounded-lg bg-zinc-100 hover:bg-orange-50 dark:bg-zinc-900 dark:hover:bg-zinc-800 text-zinc-700 dark:text-zinc-300 hover:text-orange-600 dark:hover:text-orange-400 border border-zinc-200 dark:border-zinc-800 transition disabled:opacity-50"
          >
            {prompt}
          </button>
        ))}
      </div>

      {/* Messages Scroll Area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((m) => (
          <div
            key={m.id}
            className={`flex flex-col ${m.sender === 'student' ? 'items-end' : 'items-start'}`}
          >
            <div className="flex items-center gap-2 mb-1 px-1">
              <span className="text-[10px] font-bold uppercase tracking-wider text-zinc-400">
                {m.sender === 'student' ? 'You' : 'AI Tutor'}
              </span>
              <span className="text-[10px] text-zinc-500">{m.timestamp}</span>
              {m.model && (
                <span className="text-[9px] font-mono px-1.5 py-0.2 rounded bg-zinc-100 dark:bg-zinc-800 text-zinc-500">
                  {m.model === 'offline-socratic' ? 'Socratic AI' : m.model}
                </span>
              )}
            </div>

            <div
              className={`max-w-[90%] rounded-2xl px-4 py-3 text-xs leading-relaxed shadow-sm ${
                m.sender === 'student'
                  ? 'bg-orange-600 text-white rounded-br-sm'
                  : 'bg-zinc-100 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800/80 text-zinc-800 dark:text-zinc-200 rounded-bl-sm'
              }`}
            >
              {m.sender === 'student' ? (
                <p className="whitespace-pre-wrap">{m.text}</p>
              ) : (
                <div className="prose prose-xs dark:prose-invert max-w-none text-xs">
                  <ReactMarkdown>{m.text}</ReactMarkdown>
                </div>
              )}
            </div>
          </div>
        ))}

        {loading && (
          <div className="flex items-center gap-2 text-zinc-400 text-xs italic p-2 animate-pulse">
            <div className="w-3.5 h-3.5 border-2 border-orange-500 border-t-transparent rounded-full animate-spin" />
            <span>Analyzing problem logic and formulating pedagogical guidance…</span>
          </div>
        )}

        {error && (
          <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-xl text-red-500 text-xs">
            {error}
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Controls */}
      <div className="p-3 border-t border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-900/30 shrink-0 flex flex-col gap-2">
        <div className="flex items-center justify-between text-[11px] text-zinc-500 px-1">
          <label className="flex items-center gap-1.5 cursor-pointer">
            <input
              type="checkbox"
              checked={includeCode}
              onChange={(e) => setIncludeCode(e.target.checked)}
              className="rounded border-zinc-300 dark:border-zinc-700 text-orange-600 focus:ring-0"
            />
            <span>Include current editor code context</span>
          </label>
        </div>

        <form
          onSubmit={(e) => {
            e.preventDefault()
            handleSend()
          }}
          className="flex items-center gap-2"
        >
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask a question about the logic, complexity, or edge cases..."
            disabled={loading}
            className="flex-1 bg-white dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 rounded-xl px-3.5 py-2.5 text-xs text-zinc-900 dark:text-white placeholder-zinc-400 focus:outline-none focus:border-orange-500 transition shadow-inner"
          />
          <button
            type="submit"
            disabled={loading || !input.trim()}
            className="px-4 py-2.5 bg-orange-600 hover:bg-orange-500 disabled:bg-zinc-300 dark:disabled:bg-zinc-800 text-white rounded-xl text-xs font-bold uppercase tracking-wider transition shadow-sm shrink-0 flex items-center gap-1.5"
          >
            <span>Ask</span>
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 5l7 7m0 0l-7 7m7-7H3" />
            </svg>
          </button>
        </form>
      </div>
    </div>
  )
}
