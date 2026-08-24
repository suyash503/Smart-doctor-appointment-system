# Voice agent — working notes

Notes for building a spoken interface on top of the existing Smart Doctor assistant,
using Deepgram for speech. Written to be handed to a fresh session, so it repeats
things that are obvious if you have the project open.

Read the "What already exists" section first. Most of the design work is deciding
how the voice loop reuses what is there rather than growing a second copy of it.

---

## 1. What already exists

A FastAPI backend, a React frontend, and an MCP server that holds the tools.

```
backend/
  mcp_server.py     FastMCP server over stdio: 14 tools + 1 resource
  mcp_client.py     stdio client; Toolbox class, one shared instance
  services.py       ALL domain logic: booking, records, prescriptions, photo drafts
  extraction.py     reads medicines/conditions out of an uploaded image
  chat.py           POST /chat/ — the agent loop lives here
  main.py           FastAPI app, starts the MCP server as a subprocess on startup
  core/config.py    env, model names, paths
  database/         SQLAlchemy models + session helpers
  tools/            HTTP routers: booking, querying, records, photos, google_cal
frontend/src/
  App.jsx           chat shell, text size control, patient number
  Message.jsx       renders assistant markdown
  PhotoDraft.jsx    review-and-confirm card for uploaded photos
  api.js            all fetch calls, base URL from VITE_API_BASE
```

### The shape that matters

`services.py` is the single source of domain logic. It has exactly two callers: the
MCP tools and the HTTP routers. Neither holds its own copy. **The voice agent must
become a third caller of the same layer, not a fourth implementation.**

`chat.py` is an MCP *client*. It does not hardcode tool schemas — it calls
`toolbox.tool_specs()`, which lists tools over MCP and converts them to the model's
function-calling format at runtime. Adding a tool to `mcp_server.py` is enough to
make the agent aware of it. Keep that property.

### MCP tools currently exposed

`list_doctors`, `list_patient_appointments`, `book_appointment`, `cancel_appointment`,
`add_medical_record`, `list_medical_records`, `delete_medical_record`,
`add_prescription`, `list_prescriptions`, `stop_prescription`, `list_photo_drafts`,
`get_photo_draft`, `confirm_photo_draft`, `discard_photo_draft`

Resource: `appointment://patient/{patient_id}/history` — allergies, conditions,
medications and appointments as one readable summary.

### Models in use (`backend/core/config.py`)

| Setting | Default | Notes |
| --- | --- | --- |
| `GROQ_MODEL` | `openai/gpt-oss-120b` | tool calling; free tier, rate limited |
| `GROQ_VISION_MODEL` | `qwen/qwen3.6-27b` | reads photos |

Groq's free tier is the only LLM budget. `llama-3.3-70b-versatile` was retired and
removed — do not reintroduce it.

---

## 2. Conventions to preserve

These are settled decisions, not preferences to relitigate.

- **No comments in the code.** Docstrings on MCP tools are the exception, because
  FastMCP sends them to the model as the tool description.
- **Commit messages stay plain** — a subject and a body explaining why, with no
  trailers and no tool or generator attribution of any kind. Same for code and docs.
- **Domain logic goes in `services.py`.** Routers and tools stay thin.
- **Nothing is written to a medical record without the patient confirming it.**
  Photo extraction produces a *draft*; `confirm_photo_draft` is a separate step. Voice
  must not weaken this — see §7.
- Commit in small steps and push to `main`.

---

## 3. The goal

A spoken interface: the patient talks, the assistant answers out loud, and it can
still book appointments and read records through the same MCP tools.

The point of the exercise is **orchestration**. The pipeline is assembled from
primitives — streaming STT, an LLM tool loop, streaming TTS — with turn-taking,
interruption and latency handling written by hand.

### Explicit non-goal

Deepgram sells a **Voice Agent API** that wires STT + LLM + TTS together and handles
turn-taking for you. It is a good product and the wrong choice here: using it would
mean the orchestration is Deepgram's, and the resume claim would not be honest.

Use Deepgram for **speech-to-text and text-to-speech only**. Own the loop between them.

If you later decide the turnkey API is the pragmatic choice, that is fine — just
describe it accurately as an integration rather than as an agent you built.

---

## 4. Recommended architecture

One WebSocket between browser and backend. Deepgram is only ever spoken to from the
server.

```
browser mic
   │  PCM/Opus frames over WS
   ▼
FastAPI  /voice  (new: backend/voice.py)
   │
   ├──► Deepgram STT socket ──► transcripts, turn-end signal
   │
   ├──► agent loop (extracted from chat.py) ──► MCP tools ──► services.py ──► DB
   │
   └──► Deepgram TTS ──► audio frames ──► back down the same WS
                                              │
                                              ▼
                                    browser plays audio
```

### Why the server proxies Deepgram

The browser can talk to Deepgram directly, and it is tempting because it is fewer
hops. Do not. It puts the API key in client code. Proxying through FastAPI keeps the
key server-side and gives one place to run the tool loop. (Deepgram supports
short-lived scoped keys if you later want direct browser connections — that is the
correct way to do it, not shipping the raw key.)

### The refactor to do first

`chat.py` currently holds the agent loop inside the HTTP handler: build conversation,
call Groq with `toolbox.tool_specs()`, run tool calls, loop up to `MAX_TOOL_ROUNDS`,
persist messages.

Extract it into `backend/agent.py`, something like:

```
async def run_turn(db, session_id, message, patient_id) -> str
```

and have `POST /chat/` call it. Then the voice path calls the same function. This is
the same "one implementation, two callers" pattern `services.py` already follows, so
it fits the codebase rather than fighting it.

Do this as its own commit, with the text chat verified working, *before* any audio
code exists. It is much easier to debug a refactor when there is no WebSocket in the
picture.

For voice you will probably want a streaming variant that yields text as it arrives,
so TTS can start on the first sentence instead of the whole reply. Consider
`run_turn_stream(...)` yielding chunks, with `run_turn` as a thin wrapper that joins
them.

---

## 5. Deepgram specifics

Checked August 2026. Re-verify before relying on any of it — model names and prices
move.

**Free budget:** $200 in credit, no card required, credits do not expire. Usable
across STT, TTS and Voice Agent. That is a lot for this project — roughly 6M
characters of Aura-2 TTS, or thousands of minutes of streaming STT.

### Speech to text

| Model | Why you might pick it |
| --- | --- |
| `flux-general-en` | Built for voice agents; understands conversational flow and handles turn-taking natively. Strong default here. |
| `nova-3-medical` | Medical vocabulary. Drug names are exactly where general models fail. |
| `nova-3` | General current-gen, streaming + batch. |

Streaming is over a websocket. Pricing at time of writing: Nova-3 ≈ $0.0077/min
streaming, ≈ $0.0043/min pre-recorded.

**The interesting tension:** Flux gives you turn-taking for free, `nova-3-medical`
gives you better drug-name accuracy. Try Flux first — turn-taking is the harder
problem to write yourself, and misheard drug names get caught by the confirmation
step anyway. Measure before switching.

### Text to speech

Aura-2, voices named `[model]-[voice]-[lang]`, e.g. `aura-2-thalia-en`. Legacy Aura 1
voices look like `aura-asteria-en`. Roughly $0.030 per 1,000 characters. There is a
streaming endpoint — confirm the current transport in the docs, since streaming TTS
is what keeps time-to-first-audio low.

Note there was a promotion running to 12 Sept 2026 for free Flux TTS with up to 45
concurrent streams. Check whether it still applies.

### Keyterm prompting — worth doing

Deepgram supports biasing recognition toward supplied terms. **Pull the patient's
known medications out of the database and pass them as keyterms when opening the STT
socket.** "Atorvastatin" is not in a general vocabulary but it is sitting in the
`prescriptions` table.

This is a small piece of code and a genuinely good thing to talk about: domain
knowledge from your own data improving upstream recognition accuracy.

---

## 6. Latency

Voice is unforgiving in a way text is not. Target under ~1.2s from the user finishing
a sentence to hearing the first audio.

| Stage | Rough budget |
| --- | --- |
| STT final transcript after speech end | 100–300 ms |
| LLM first token | 200–500 ms |
| Tool call round trip (MCP → SQLite) | 10–50 ms |
| TTS first audio | 100–300 ms |

Two things blow this budget:

1. **Waiting for the full LLM reply before starting TTS.** Stream, and send the first
   sentence to TTS as soon as it lands.
2. **Multiple tool rounds.** `MAX_TOOL_ROUNDS` is 4. A two-round answer doubles the
   LLM latency. Consider speaking a filler ("let me check that") when a tool call
   starts — that is orchestration work worth showing.

Instrument this from the start. Log per-stage timings and keep them; "p50
time-to-first-audio of X ms" is worth far more on a resume than "built a voice agent".

---

## 7. Project-specific gotchas

**The confirmation gate.** Photo drafts are never auto-saved, and the system prompt
tells the assistant to read items back before confirming. Voice makes this *more*
important, not less — a misheard "yes" should not book an appointment or write a
dosage. Read back before any write, and consider requiring an explicit confirmation
phrase for `book_appointment`, `cancel_appointment` and `confirm_photo_draft`.

**No authentication.** `patient_id` is supplied by the caller. It is a number typed
into the header. Voice does not change this, but do not let the *model* choose the
id from the transcript — pass it from the session, as `/chat/` already does. If you
ever add auth, this is the place it matters most.

**The MCP subprocess.** `main.py` starts `mcp_server.py` over stdio in the FastAPI
lifespan and shares one `Toolbox`. Voice sessions are longer-lived and concurrent, so
watch that the single stdio session holds up. `GET /` reports `mcp_connected`.

**Groq free tier rate limits.** Voice makes many more LLM calls than typing does.
Expect 429s under load and handle them without dropping the call.

**Render's free tier.** The backend sleeps after ~15 minutes and takes 30–50s to wake.
That is survivable for chat and fatal for a voice demo. Warm it before demoing, or
host the voice path somewhere that stays up. Also confirm WebSocket support on
whatever plan you use.

**Uploaded images are on local disk** (`backend/uploads`) and do not survive a
redeploy. Extracted records do.

**Audio format.** `MediaRecorder` gives webm/opus, which is easy but adds buffering
latency. An `AudioWorklet` producing raw `linear16` PCM is more work and noticeably
faster. Start with whichever gets you a round trip, then measure.

**Barge-in.** If the patient starts talking while the assistant is speaking, stop the
TTS playback and discard queued audio immediately. Nothing makes a voice agent feel
worse than one that talks over you. This is the single most visible piece of
orchestration in the whole build.

---

## 8. Suggested build order

Each step should end with something demonstrable and its own commit.

1. **Extract the agent loop** into `agent.py`; `/chat/` uses it; text chat still works.
   No audio yet.
2. **Echo WebSocket.** `/voice` accepts a connection, receives mic frames, logs sizes,
   sends something back. Proves transport and CORS before Deepgram is involved.
3. **STT only.** Pipe browser audio to Deepgram, stream interim + final transcripts
   back, render them on screen. Now you can see what it hears.
4. **TTS only.** Take a typed sentence, speak it. Proves the audio return path.
5. **Close the loop.** Final transcript → `agent.py` → reply → TTS. First real
   conversation. Expect it to feel slow; that is fine at this stage.
6. **Turn-taking and barge-in.** Interrupt handling, cancelling in-flight TTS.
7. **Latency work.** Sentence-level streaming into TTS, filler phrases during tool
   calls, per-stage timing logs.
8. **Domain polish.** Keyterm prompting from the patient's medications, read-back
   confirmation before writes, graceful 429 handling.
9. **Frontend.** A push-to-talk or always-listening control that fits the existing UI.
   Respect the accessibility work already done — large targets, visible state, a clear
   way to see what was heard, and a text fallback that always works.

---

## 9. Resume framing

What is actually impressive here, in rough order:

- A full-duplex streaming pipeline assembled from primitives, not a turnkey SDK.
- Interruption handling and turn-taking.
- Tool calls executed mid-conversation, with the tool list discovered over MCP at
  runtime rather than hardcoded.
- One domain layer serving three surfaces: HTTP chat, MCP, and voice.
- Measured latency, with the numbers to quote.
- Domain-aware recognition — feeding known drug names back into STT.

Phrase it as orchestration and measurement, not as "integrated Deepgram". And keep
the accessibility thread: the UI already has a text-size control and 44px targets
because the users are often elderly, and voice is the same argument continued.

---

## 10. Decide before starting

- Push-to-talk or always-listening? Always-listening is a better demo and much more
  work (needs VAD, barge-in, and a plan for background noise).
- Voice-only, or voice alongside the existing chat thread? Showing transcripts in the
  same thread is more accessible and easier to debug.
- Does voice get its own session id, or share the chat session so history carries
  across both? Sharing is nicer and means `chat_messages` needs no change.
- Is a spoken booking allowed to complete, or does it always hand off to the screen
  for the final confirm?
