const FALLBACK_BASE = 'https://smart-doctor-appointment-system-dqh0.onrender.com'

export const API_BASE = (import.meta.env.VITE_API_BASE || FALLBACK_BASE).replace(/\/+$/, '')

async function readResponse(response) {
  const text = await response.text()

  let payload = null
  if (text) {
    try {
      payload = JSON.parse(text)
    } catch {
      payload = null
    }
  }

  if (!response.ok) {
    const detail = payload && payload.detail ? payload.detail : `Request failed (${response.status})`
    throw new Error(typeof detail === 'string' ? detail : 'Request failed')
  }

  return payload
}

export function photoImageUrl(photoId) {
  return `${API_BASE}/records/photos/image/${photoId}`
}

export async function sendChat(sessionId, message) {
  const response = await fetch(`${API_BASE}/chat/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sessionId, message }),
  })

  return readResponse(response)
}

export async function uploadPhoto(patientId, file) {
  const body = new FormData()
  body.append('patient_id', String(patientId))
  body.append('file', file)

  const response = await fetch(`${API_BASE}/records/photos`, { method: 'POST', body })

  return readResponse(response)
}

export async function listPendingDrafts(patientId) {
  const response = await fetch(`${API_BASE}/records/photos/pending/${patientId}`)

  return readResponse(response)
}

export async function confirmDraft(photoId, medications, records) {
  const response = await fetch(`${API_BASE}/records/photos/${photoId}/confirm`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ medications, records }),
  })

  return readResponse(response)
}

export async function discardDraft(photoId) {
  const response = await fetch(`${API_BASE}/records/photos/${photoId}/discard`, { method: 'POST' })

  return readResponse(response)
}
