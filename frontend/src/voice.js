import { API_BASE } from './api'

const CAPTURE_RATE = 16000
const FRAME_SAMPLES = 1024

const CAPTURE_WORKLET = `
class PcmCapture extends AudioWorkletProcessor {
  constructor() {
    super()
    this.frame = new Int16Array(${FRAME_SAMPLES})
    this.filled = 0
  }

  process(inputs) {
    const channel = inputs[0] && inputs[0][0]
    if (!channel) return true

    for (let i = 0; i < channel.length; i += 1) {
      const sample = Math.max(-1, Math.min(1, channel[i]))
      this.frame[this.filled] = sample < 0 ? sample * 0x8000 : sample * 0x7fff
      this.filled += 1

      if (this.filled === this.frame.length) {
        const copy = this.frame.slice()
        this.port.postMessage(copy.buffer, [copy.buffer])
        this.filled = 0
      }
    }

    return true
  }
}

registerProcessor('pcm-capture', PcmCapture)
`

export function voiceUrl(sessionId, patientId) {
  const base = API_BASE.replace(/^http/, 'ws')
  const params = new URLSearchParams({ session_id: sessionId })
  if (patientId) params.set('patient_id', String(patientId))

  return `${base}/voice?${params.toString()}`
}

function stripWavHeader(buffer) {
  if (buffer.byteLength < 44) return buffer

  const head = new Uint8Array(buffer, 0, 4)
  const isRiff = head[0] === 82 && head[1] === 73 && head[2] === 70 && head[3] === 70

  return isRiff ? buffer.slice(44) : buffer
}

class Speaker {
  constructor() {
    this.context = null
    this.rate = 24000
    this.playhead = 0
    this.sources = new Set()
  }

  resume(rate) {
    if (rate) this.rate = rate
    if (!this.context) {
      const Context = window.AudioContext || window.webkitAudioContext
      this.context = new Context()
    }

    return this.context.resume()
  }

  play(raw) {
    if (!this.context) return

    const buffer = stripWavHeader(raw)
    const usable = buffer.byteLength - (buffer.byteLength % 2)
    if (usable <= 0) return

    const pcm = new Int16Array(buffer, 0, usable / 2)
    const audio = this.context.createBuffer(1, pcm.length, this.rate)
    const channel = audio.getChannelData(0)
    for (let i = 0; i < pcm.length; i += 1) channel[i] = pcm[i] / 0x8000

    const source = this.context.createBufferSource()
    source.buffer = audio
    source.connect(this.context.destination)

    const startAt = Math.max(this.context.currentTime + 0.06, this.playhead)
    source.start(startAt)
    this.playhead = startAt + audio.duration

    this.sources.add(source)
    source.onended = () => this.sources.delete(source)
  }

  get busy() {
    return this.sources.size > 0
  }

  flush() {
    this.sources.forEach((source) => {
      try {
        source.stop()
      } catch {
        /* already finished */
      }
    })
    this.sources.clear()
    this.playhead = 0
  }

  async close() {
    this.flush()
    if (this.context) {
      await this.context.close().catch(() => {})
      this.context = null
    }
  }
}

export class VoiceLink {
  constructor(handlers = {}) {
    this.handlers = handlers
    this.socket = null
    this.stream = null
    this.capture = null
    this.node = null
    this.speaker = new Speaker()
    this.workletUrl = null
  }

  emit(name, payload) {
    const handler = this.handlers[name]
    if (handler) handler(payload)
  }

  get active() {
    return this.socket !== null
  }

  async start(sessionId, patientId) {
    if (this.socket) return

    this.stream = await navigator.mediaDevices.getUserMedia({
      audio: {
        channelCount: 1,
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true,
      },
    })

    const Context = window.AudioContext || window.webkitAudioContext
    this.capture = new Context({ sampleRate: CAPTURE_RATE })
    await this.capture.resume()

    this.workletUrl = URL.createObjectURL(
      new Blob([CAPTURE_WORKLET], { type: 'application/javascript' }),
    )
    await this.capture.audioWorklet.addModule(this.workletUrl)

    await this.speaker.resume()

    this.socket = new WebSocket(voiceUrl(sessionId, patientId))
    this.socket.binaryType = 'arraybuffer'

    this.socket.onopen = () => {
      this.socket.send(JSON.stringify({ type: 'start', sample_rate: this.capture.sampleRate }))
      this.listen()
    }

    this.socket.onmessage = (event) => {
      if (typeof event.data !== 'string') {
        this.speaker.play(event.data)
        this.emit('speaking')
        return
      }

      const payload = JSON.parse(event.data)

      if (payload.type === 'ready') {
        this.speaker.resume(payload.sample_rate)
        this.emit('ready', payload)
      } else if (payload.type === 'interrupted') {
        this.speaker.flush()
        this.emit('interrupted')
      } else {
        this.emit(payload.type, payload)
      }
    }

    this.socket.onerror = () => this.emit('error', { message: 'The voice connection failed.' })
    this.socket.onclose = () => this.emit('closed')
  }

  listen() {
    this.node = new AudioWorkletNode(this.capture, 'pcm-capture')
    this.node.port.onmessage = (event) => {
      if (this.socket && this.socket.readyState === WebSocket.OPEN) {
        this.socket.send(event.data)
      }
    }

    const silence = this.capture.createGain()
    silence.gain.value = 0

    this.capture.createMediaStreamSource(this.stream).connect(this.node)
    this.node.connect(silence).connect(this.capture.destination)
  }

  say(text) {
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      this.socket.send(JSON.stringify({ type: 'text', text }))
    }
  }

  interrupt() {
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      this.socket.send(JSON.stringify({ type: 'interrupt' }))
    }
    this.speaker.flush()
  }

  async stop() {
    if (this.socket) {
      this.socket.onclose = null
      this.socket.close()
      this.socket = null
    }

    if (this.node) {
      this.node.port.onmessage = null
      this.node.disconnect()
      this.node = null
    }

    if (this.stream) {
      this.stream.getTracks().forEach((track) => track.stop())
      this.stream = null
    }

    if (this.capture) {
      await this.capture.close().catch(() => {})
      this.capture = null
    }

    if (this.workletUrl) {
      URL.revokeObjectURL(this.workletUrl)
      this.workletUrl = null
    }

    await this.speaker.close()
  }
}
