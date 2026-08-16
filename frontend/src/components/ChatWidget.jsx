import { useEffect, useRef, useState } from 'react'
import { sendChatMessage } from '../api/client'

function ChatIcon() {
  return (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path
        d="M21 11.5C21.0034 12.8199 20.6951 14.1219 20.1 15.3C19.3944 16.7118 18.3097 17.8992 16.9674 18.7293C15.6251 19.5594 14.0782 19.9994 12.5 20C11.1801 20.0035 9.87812 19.6951 8.7 19.1L3 21L4.9 15.3C4.30493 14.1219 3.99656 12.8199 4 11.5C4.00061 9.92179 4.44061 8.37488 5.27072 7.03258C6.10083 5.69028 7.28825 4.6056 8.7 3.90003C9.87812 3.30496 11.1801 2.99659 12.5 3.00003H13C15.0843 3.11502 17.053 3.99479 18.5291 5.47089C20.0052 6.94699 20.885 8.91568 21 11V11.5Z"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}

function CloseIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M18 6L6 18" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
      <path d="M6 6L18 18" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
  )
}

function SendIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path
        d="M22 2L11 13M22 2L15 22L11 13M22 2L2 9L11 13"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}

const SUGGESTIONS = [
  'What are my top spending categories?',
  'Why did my spending jump recently?',
  'Am I on track with my budget?',
]

function ChatWidget() {
  const [open, setOpen] = useState(false)
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const [conversationId, setConversationId] = useState(null)
  const [error, setError] = useState(null)
  const scrollRef = useRef(null)

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [messages, sending])

  async function handleSend(text) {
    const messageText = text ?? input
    if (!messageText.trim() || sending) return

    setError(null)
    setInput('')
    setMessages((prev) => [...prev, { role: 'user', content: messageText }])
    setSending(true)

    try {
      const result = await sendChatMessage(messageText, conversationId)
      setConversationId(result.conversation_id)
      setMessages((prev) => [...prev, { role: 'assistant', content: result.reply }])
    } catch (err) {
      setError(
        err.response?.status === 401
          ? 'Your session expired -- try logging in again.'
          : 'Something went wrong reaching the assistant. Try again in a moment.'
      )
    } finally {
      setSending(false)
    }
  }

  function handleSubmit(e) {
    e.preventDefault()
    handleSend()
  }

  return (
    <>
      {open && (
        <div className="fixed bottom-24 right-6 z-50 w-[380px] max-w-[calc(100vw-3rem)] h-[520px] max-h-[calc(100vh-8rem)] bg-ink-900 border border-ink-700 rounded-lg shadow-2xl flex flex-col overflow-hidden">
          <div className="flex items-center justify-between px-5 py-4 border-b border-ink-700">
            <div>
              <div className="font-display text-paper text-sm tracking-wide">Ask About Your Spending</div>
              <div className="text-xs text-paper-dim mt-0.5">Grounded in your actual data</div>
            </div>
            <button
              onClick={() => setOpen(false)}
              className="text-paper-dim hover:text-paper transition-colors"
              aria-label="Close chat"
            >
              <CloseIcon />
            </button>
          </div>

          <div ref={scrollRef} className="flex-1 overflow-y-auto px-5 py-4 space-y-3">
            {messages.length === 0 && (
              <div>
                <p className="text-paper-dim text-sm mb-4">
                  Ask a question about your spending, budget, or anomalies -- answers are grounded
                  in your own computed analytics.
                </p>
                <div className="space-y-2">
                  {SUGGESTIONS.map((s) => (
                    <button
                      key={s}
                      onClick={() => handleSend(s)}
                      className="w-full text-left text-sm text-brass bg-ink-950 border border-ink-700 rounded-lg px-4 py-2.5 hover:border-brass/50 transition-colors"
                    >
                      {s}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {messages.map((m, i) => (
              <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div
                  className={`max-w-[85%] rounded-lg px-4 py-2.5 text-sm leading-relaxed ${
                    m.role === 'user'
                      ? 'bg-brass text-ink-950 font-medium'
                      : 'bg-ink-950 border border-ink-700 text-paper'
                  }`}
                >
                  {m.content}
                </div>
              </div>
            ))}

            {sending && (
              <div className="flex justify-start">
                <div className="bg-ink-950 border border-ink-700 rounded-lg px-4 py-2.5 text-sm text-paper-dim">
                  Thinking...
                </div>
              </div>
            )}

            {error && (
              <div className="text-xs text-brick bg-brick/10 border border-brick/30 rounded-lg px-4 py-2.5">
                {error}
              </div>
            )}
          </div>

          <form onSubmit={handleSubmit} className="flex gap-2 px-4 py-4 border-t border-ink-700">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask a question..."
              disabled={sending}
              className="flex-1 bg-ink-950 border border-ink-700 rounded-full px-4 py-2.5 text-sm text-paper placeholder:text-paper-dim/50 disabled:opacity-50"
            />
            <button
              type="submit"
              disabled={sending || !input.trim()}
              className="bg-brass text-ink-950 rounded-full p-2.5 disabled:opacity-40 flex items-center justify-center"
              aria-label="Send message"
            >
              <SendIcon />
            </button>
          </form>
        </div>
      )}

      <button
        onClick={() => setOpen((v) => !v)}
        className="fixed bottom-6 right-6 z-50 bg-brass text-ink-950 rounded-full w-14 h-14 flex items-center justify-center shadow-2xl hover:scale-105 transition-transform"
        aria-label={open ? 'Close chat' : 'Open chat'}
      >
        {open ? <CloseIcon /> : <ChatIcon />}
      </button>
    </>
  )
}

export default ChatWidget
