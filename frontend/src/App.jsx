import { useState, useRef, useEffect, useCallback } from 'react'
import './App.css'
import PhotoDraft from './PhotoDraft'
import { confirmDraft, discardDraft, listPendingDrafts, sendChat, uploadPhoto } from './api'

const GREETING = "Hello! I'm your hospital assistant. Ask about doctors, book a visit, or upload a photo of a prescription."

function App() {
  const [messages, setMessages] = useState([{ role: 'assistant', content: GREETING }])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)

  const [patientId, setPatientId] = useState(() => localStorage.getItem('patientId') || '2')
  const [draft, setDraft] = useState(null)
  const [draftBusy, setDraftBusy] = useState(false)

  const [sessionId] = useState(() => `session_${Math.random().toString(36).substring(2, 9)}`)

  const messagesEndRef = useRef(null)
  const fileInputRef = useRef(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, draft])

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
        if (!cancelled && pending && pending.length > 0) {
          setDraft(pending[0])
        }
      })
      .catch(() => {})

    return () => {
      cancelled = true
    }
  }, [patientId])

  const sendMessage = async (e) => {
    e.preventDefault()
    if (!input.trim()) return

    const userMessage = input.trim()
    say(userMessage, 'user')
    setInput('')
    setIsLoading(true)

    try {
      const data = await sendChat(sessionId, userMessage)
      say(data.reply)
    } catch (error) {
      say(`Sorry, I could not reach the server. ${error.message}`)
    } finally {
      setIsLoading(false)
    }
  }

  const handleFile = async (event) => {
    const file = event.target.files?.[0]
    event.target.value = ''
    if (!file) return

    const id = Number(patientId)
    if (!id) {
      say('Enter your patient number before uploading a photo.')
      return
    }

    say(`Uploading ${file.name}...`, 'user')
    setIsLoading(true)

    try {
      const uploaded = await uploadPhoto(id, file)
      setDraft(uploaded)
      say('I read the photo. Check the details below and save the ones that look right.')
    } catch (error) {
      say(`That photo could not be read. ${error.message}`)
    } finally {
      setIsLoading(false)
    }
  }

  const handleConfirm = async (photoId, medications, records) => {
    setDraftBusy(true)

    try {
      const result = await confirmDraft(photoId, medications, records)
      setDraft(null)
      say(
        `Saved ${result.added_medications} medication(s) and ${result.added_records} history entr${
          result.added_records === 1 ? 'y' : 'ies'
        } to your record.`,
      )
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
      say('Discarded that photo. Nothing was saved.')
    } catch (error) {
      say(`Could not discard it. ${error.message}`)
    } finally {
      setDraftBusy(false)
    }
  }

  return (
    <div className="chat-container">
      <header className="chat-header">
        <h1>🏥 Smart Hospital Assistant</h1>
        <label className="patient-field">
          Patient
          <input
            type="number"
            min="1"
            value={patientId}
            onChange={(e) => setPatientId(e.target.value)}
          />
        </label>
      </header>

      <div className="chat-box">
        {messages.map((msg, index) => (
          <div key={index} className={`message-wrapper ${msg.role}`}>
            <div className={`message-bubble ${msg.role}`}>{msg.content}</div>
          </div>
        ))}

        {isLoading && (
          <div className="message-wrapper assistant">
            <div className="message-bubble assistant typing">Thinking...</div>
          </div>
        )}

        {draft && (
          <PhotoDraft
            key={draft.id}
            draft={draft}
            busy={draftBusy}
            onConfirm={handleConfirm}
            onDiscard={handleDiscard}
          />
        )}

        <div ref={messagesEndRef} />
      </div>

      <form onSubmit={sendMessage} className="chat-input-form">
        <input
          ref={fileInputRef}
          type="file"
          accept="image/png,image/jpeg,image/webp"
          onChange={handleFile}
          hidden
        />
        <button
          type="button"
          className="attach-button"
          title="Upload a prescription photo"
          disabled={isLoading}
          onClick={() => fileInputRef.current?.click()}
        >
          📎
        </button>
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask about doctors, or attach a prescription photo..."
          disabled={isLoading}
        />
        <button type="submit" disabled={isLoading || !input.trim()}>
          Send
        </button>
      </form>
    </div>
  )
}

export default App
