import { useState, useRef, useEffect, useCallback } from 'react'
import './App.css'
import Message from './Message'
import PhotoDraft from './PhotoDraft'
import { LogoMark, PaperclipIcon, SendIcon } from './icons'
import { confirmDraft, discardDraft, listPendingDrafts, sendChat, uploadPhoto } from './api'

const SUGGESTIONS = [
  'Which doctors are available?',
  'What am I allergic to?',
  'What medicines am I taking?',
  'Book me a follow-up next week',
]

function App() {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)

  const [patientId, setPatientId] = useState(() => localStorage.getItem('patientId') || '2')
  const [draft, setDraft] = useState(null)
  const [draftBusy, setDraftBusy] = useState(false)

  const [sessionId] = useState(() => `session_${Math.random().toString(36).substring(2, 9)}`)

  const endRef = useRef(null)
  const fileRef = useRef(null)
  const textareaRef = useRef(null)

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [messages, draft, isLoading])

  useEffect(() => {
    localStorage.setItem('patientId', patientId)
  }, [patientId])

  const say = useCallback((content, role = 'assistant') => {
    setMessages((prev) => [...prev, { role, content }])
  }, [])

  useEffect(() => {
    let cancelled = false
    const id = Number(patientId)
    if (!id) return undefined

    listPendingDrafts(id)
      .then((pending) => {
        if (!cancelled && pending && pending.length > 0) setDraft(pending[0])
      })
      .catch(() => {})

    return () => {
      cancelled = true
    }
  }, [patientId])

  const grow = () => {
    const el = textareaRef.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`
  }

  const ask = async (text) => {
    const question = text.trim()
    if (!question || isLoading) return

    say(question, 'user')
    setInput('')
    requestAnimationFrame(grow)
    setIsLoading(true)

    try {
      const data = await sendChat(sessionId, question, patientId)
      say(data.reply)
    } catch (error) {
      say(`I could not reach the server. ${error.message}`)
    } finally {
      setIsLoading(false)
    }
  }

  const onSubmit = (e) => {
    e.preventDefault()
    ask(input)
  }

  const onKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      ask(input)
    }
  }

  const handleFile = async (event) => {
    const file = event.target.files?.[0]
    event.target.value = ''
    if (!file) return

    const id = Number(patientId)
    if (!id) {
      say('Add your patient number in the header before uploading a photo.')
      return
    }

    say(`Sent a photo — ${file.name}`, 'user')
    setIsLoading(true)

    try {
      const uploaded = await uploadPhoto(id, file)
      setDraft(uploaded)
      say('Here is what I read from that photo. Check it over and keep what looks right.')
    } catch (error) {
      say(`I could not read that photo. ${error.message}`)
    } finally {
      setIsLoading(false)
    }
  }

  const handleConfirm = async (photoId, medications, records) => {
    setDraftBusy(true)

    try {
      const result = await confirmDraft(photoId, medications, records)
      setDraft(null)
      const bits = []
      if (result.added_medications) bits.push(`${result.added_medications} medicine${result.added_medications === 1 ? '' : 's'}`)
      if (result.added_records) bits.push(`${result.added_records} history entr${result.added_records === 1 ? 'y' : 'ies'}`)
      say(`Added ${bits.join(' and ')} to your record.`)
    } catch (error) {
      say(`Nothing was saved. ${error.message}`)
    } finally {
      setDraftBusy(false)
    }
  }

  const handleDiscard = async (photoId) => {
    setDraftBusy(true)

    try {
      await discardDraft(photoId)
      setDraft(null)
      say('Thrown away. Nothing from that photo was saved.')
    } catch (error) {
      say(`I could not discard it. ${error.message}`)
    } finally {
      setDraftBusy(false)
    }
  }

  const empty = messages.length === 0 && !draft

  return (
    <div className="app">
      <header className="topbar">
        <div className="topbar-inner">
          <div className="brand">
            <span className="brand-mark">
              <LogoMark />
            </span>
            <span className="brand-text">
              <strong>Smart Doctor</strong>
              <small>Appointments &amp; records</small>
            </span>
          </div>

          <label className="patient">
            <span>Patient</span>
            <input
              type="number"
              min="1"
              value={patientId}
              onChange={(e) => setPatientId(e.target.value)}
              aria-label="Patient number"
            />
          </label>
        </div>
      </header>

      <main className="thread">
        <div className="thread-inner">
          {empty && (
            <section className="welcome">
              <span className="welcome-mark">
                <LogoMark width="26" height="26" />
              </span>
              <h1>How can I help today?</h1>
              <p>
                Ask about doctors and appointments, or send a photo of a prescription and I will
                read it into your record.
              </p>
              <div className="chips">
                {SUGGESTIONS.map((text) => (
                  <button key={text} type="button" className="chip" onClick={() => ask(text)}>
                    {text}
                  </button>
                ))}
              </div>
            </section>
          )}

          {messages.map((msg, index) => (
            <Message key={index} role={msg.role} content={msg.content} />
          ))}

          {isLoading && <Message role="assistant" pending />}

          {draft && (
            <PhotoDraft
              key={draft.id}
              draft={draft}
              busy={draftBusy}
              onConfirm={handleConfirm}
              onDiscard={handleDiscard}
            />
          )}

          <div ref={endRef} />
        </div>
      </main>

      <footer className="composer">
        <form className="composer-inner" onSubmit={onSubmit}>
          <input
            ref={fileRef}
            type="file"
            accept="image/png,image/jpeg,image/webp"
            onChange={handleFile}
            hidden
          />

          <button
            type="button"
            className="icon-btn"
            title="Attach a prescription photo"
            aria-label="Attach a prescription photo"
            disabled={isLoading}
            onClick={() => fileRef.current?.click()}
          >
            <PaperclipIcon />
          </button>

          <textarea
            ref={textareaRef}
            rows={1}
            value={input}
            placeholder="Ask a question, or attach a photo…"
            disabled={isLoading}
            onChange={(e) => {
              setInput(e.target.value)
              grow()
            }}
            onKeyDown={onKeyDown}
          />

          <button
            type="submit"
            className="send-btn"
            aria-label="Send message"
            disabled={isLoading || !input.trim()}
          >
            <SendIcon />
          </button>
        </form>
        <p className="disclaimer">Not a substitute for medical advice.</p>
      </footer>
    </div>
  )
}

export default App
