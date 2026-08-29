import asyncio
import json
import logging
import re
import time
from urllib.parse import urlencode

import websockets
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

import services
from agent import run_turn_stream
from core.config import (
    DEEPGRAM_API_KEY,
    DEEPGRAM_STT_MODEL,
    DEEPGRAM_TTS_MODEL,
    ENDPOINTING_MS,
    TTS_SAMPLE_RATE,
    UTTERANCE_END_MS,
)
from database.database import session_scope

router = APIRouter(tags=["Voice"])
logger = logging.getLogger(__name__)

STT_URL = "wss://api.deepgram.com/v1/listen"
TTS_URL = "wss://api.deepgram.com/v1/speak"

VOICE_INSTRUCTIONS = (
    "You are being spoken to out loud and your reply is read back by a speech "
    "synthesiser, so answer in short plain sentences. Never use markdown, headings, "
    "bullet points, tables, code or emoji. Say numbers, dates and times the way a "
    "person speaks them rather than as digits and symbols. Keep answers under about "
    "forty words unless the patient asks for more. Speech recognition mishears names "
    "and dosages, so before you book, cancel, or save anything, read the details back "
    "and wait for the patient to agree. If a reply would be a long list, say how many "
    "there are and offer to go through them."
)

FILLER_PHRASE = "One moment."
FILLER_AFTER_SECONDS = 0.6

SENTENCE_END = re.compile(r"[.!?]\s+")
WORD_BREAK = re.compile(r"[\s(\"']")
MARKDOWN_NOISE = re.compile(r"[*_`#|>]+")
ABBREVIATIONS = {"dr", "mr", "mrs", "ms", "st", "no", "vs", "approx", "am", "pm", "a.m", "p.m"}
MAX_SENTENCE_CHARS = 220


def speakable(text):
    cleaned = MARKDOWN_NOISE.sub(" ", text)
    cleaned = re.sub(r"\s+", " ", cleaned)

    return cleaned.strip()


def ends_an_abbreviation(head):
    last = WORD_BREAK.split(head)[-1].strip().lower()

    return last in ABBREVIATIONS or (len(last) == 1 and last.isalpha())


def split_sentences(buffer):
    sentences = []
    start = 0

    for match in SENTENCE_END.finditer(buffer):
        if ends_an_abbreviation(buffer[start:match.start()]):
            continue
        sentence = buffer[start:match.end()].strip()
        if sentence:
            sentences.append(sentence)
        start = match.end()

    remainder = buffer[start:]

    while len(remainder) > MAX_SENTENCE_CHARS:
        cut = remainder.rfind(" ", 0, MAX_SENTENCE_CHARS)
        if cut <= 0:
            break
        sentences.append(remainder[:cut])
        remainder = remainder[cut:].lstrip()

    return sentences, remainder


def stt_url(sample_rate, keyterms):
    query = [
        ("model", DEEPGRAM_STT_MODEL),
        ("encoding", "linear16"),
        ("sample_rate", sample_rate),
        ("channels", 1),
        ("interim_results", "true"),
        ("smart_format", "true"),
        ("punctuate", "true"),
        ("vad_events", "true"),
        ("endpointing", ENDPOINTING_MS),
        ("utterance_end_ms", UTTERANCE_END_MS),
    ]
    query.extend(("keyterm", term) for term in keyterms)

    return f"{STT_URL}?{urlencode(query)}"


def tts_url():
    query = {
        "model": DEEPGRAM_TTS_MODEL,
        "encoding": "linear16",
        "sample_rate": TTS_SAMPLE_RATE,
    }

    return f"{TTS_URL}?{urlencode(query)}"


def deepgram_headers():
    return {"Authorization": f"Token {DEEPGRAM_API_KEY}"}


class VoiceSession:
    def __init__(self, client, session_id, patient_id):
        self.client = client
        self.session_id = session_id
        self.patient_id = patient_id
        self.stt = None
        self.tts = None
        self.turn = None
        self.finals = []
        self.accept_audio = False
        self.cleared = asyncio.Event()
        self.heard_at = None
        self.metrics = None
        self.pending_flushes = 0
        self.turn_finished = False
        self.spoke_in_turn = False
        self.filler = None

    async def tell(self, payload):
        try:
            await self.client.send_text(json.dumps(payload))
        except (WebSocketDisconnect, RuntimeError):
            pass

    async def open_streams(self, sample_rate, keyterms):
        self.stt = await websockets.connect(
            stt_url(sample_rate, keyterms), additional_headers=deepgram_headers()
        )
        self.tts = await websockets.connect(
            tts_url(), additional_headers=deepgram_headers()
        )

    async def warm_up(self):
        if self.tts is None:
            return

        self.accept_audio = False
        await self.tts.send(json.dumps({"type": "Speak", "text": "Hello."}))
        await self.tts.send(json.dumps({"type": "Flush"}))

    async def close_streams(self):
        for stream in (self.stt, self.tts):
            if stream is not None:
                try:
                    await stream.close()
                except Exception:
                    pass

    async def pump_client(self):
        while True:
            message = await self.client.receive()

            if message["type"] == "websocket.disconnect":
                raise WebSocketDisconnect(message.get("code", 1000))

            if message.get("bytes") is not None:
                if self.stt is not None:
                    await self.stt.send(message["bytes"])
                continue

            payload = json.loads(message.get("text") or "{}")
            kind = payload.get("type")

            if kind == "text" and payload.get("text", "").strip():
                typed = payload["text"].strip()
                await self.tell({"type": "transcript", "text": typed, "final": True})
                self.start_turn(typed, time.perf_counter())
            elif kind == "interrupt":
                await self.barge_in()

    async def pump_stt(self):
        async for raw in self.stt:
            event = json.loads(raw)
            kind = event.get("type")

            if kind == "SpeechStarted":
                await self.barge_in()
            elif kind == "Results":
                await self.on_results(event)
            elif kind == "UtteranceEnd":
                await self.dispatch(time.perf_counter())

    async def on_results(self, event):
        alternatives = event.get("channel", {}).get("alternatives", [])
        transcript = alternatives[0].get("transcript", "") if alternatives else ""

        if not transcript.strip():
            return

        if not event.get("is_final"):
            await self.tell({"type": "transcript", "text": transcript, "final": False})
            return

        self.finals.append(transcript.strip())

        if event.get("speech_final"):
            await self.dispatch(time.perf_counter())

    async def dispatch(self, heard_at):
        spoken = " ".join(self.finals).strip()
        self.finals = []

        if not spoken:
            return

        await self.tell({"type": "transcript", "text": spoken, "final": True})
        self.start_turn(spoken, heard_at)

    def start_turn(self, spoken, heard_at):
        if self.turn is not None and not self.turn.done():
            self.turn.cancel()

        self.turn = asyncio.create_task(self.run_turn(spoken, heard_at))

    async def barge_in(self):
        if self.turn is None or self.turn.done():
            return

        self.turn.cancel()
        if self.filler is not None:
            self.filler.cancel()
        self.accept_audio = False
        self.metrics = None
        self.pending_flushes = 0
        self.turn_finished = False
        await self.clear_tts()
        await self.tell({"type": "interrupted"})

    async def clear_tts(self):
        if self.tts is None:
            return

        self.cleared.clear()
        try:
            await self.tts.send(json.dumps({"type": "Clear"}))
            await asyncio.wait_for(self.cleared.wait(), timeout=0.5)
        except (asyncio.TimeoutError, websockets.exceptions.WebSocketException):
            pass

    async def speak(self, sentence):
        text = speakable(sentence)
        if not text or self.tts is None:
            return

        self.accept_audio = True
        self.spoke_in_turn = True
        self.pending_flushes += 1
        await self.tts.send(json.dumps({"type": "Speak", "text": text}))
        await self.tts.send(json.dumps({"type": "Flush"}))

    async def fill_silence(self):
        await asyncio.sleep(FILLER_AFTER_SECONDS)

        if self.spoke_in_turn or self.turn_finished or self.metrics is None:
            return

        await self.speak(FILLER_PHRASE)

    async def finish_turn(self):
        self.turn_finished = True

        if self.pending_flushes == 0:
            await self.end_of_speech()

    async def end_of_speech(self):
        if self.metrics is None:
            return

        self.metrics["spoken_ms"] = round((time.perf_counter() - self.heard_at) * 1000)
        logger.info("voice turn %s %s", self.session_id, self.metrics)
        self.metrics = None
        self.turn_finished = False
        await self.tell({"type": "audio_end"})

    async def pump_tts(self):
        async for raw in self.tts:
            if isinstance(raw, bytes):
                if not self.accept_audio:
                    continue
                if self.metrics is not None and "first_audio_ms" not in self.metrics:
                    self.metrics["first_audio_ms"] = round(
                        (time.perf_counter() - self.heard_at) * 1000
                    )
                await self.client.send_bytes(raw)
                continue

            event = json.loads(raw)
            kind = event.get("type")

            if kind == "Cleared":
                self.cleared.set()
            elif kind == "Flushed":
                if self.metrics is None:
                    continue
                self.pending_flushes = max(0, self.pending_flushes - 1)
                if self.pending_flushes == 0 and self.turn_finished:
                    await self.end_of_speech()
            elif kind == "Warning":
                logger.warning("Deepgram speech warning: %s", event.get("description"))

    async def run_turn(self, spoken, heard_at):
        self.heard_at = heard_at
        self.metrics = {}
        self.pending_flushes = 0
        self.turn_finished = False
        self.spoke_in_turn = False
        self.filler = asyncio.create_task(self.fill_silence())
        buffer = ""

        await self.tell({"type": "reply_start"})

        try:
            with session_scope() as db:
                stream = run_turn_stream(
                    db, self.session_id, spoken, self.patient_id, VOICE_INSTRUCTIONS
                )

                async for event in stream:
                    if event["type"] == "text":
                        if "first_token_ms" not in self.metrics:
                            self.metrics["first_token_ms"] = round(
                                (time.perf_counter() - heard_at) * 1000
                            )
                        buffer += event["text"]
                        sentences, buffer = split_sentences(buffer)
                        for sentence in sentences:
                            await self.speak(sentence)
                        if sentences:
                            await self.tell(
                                {"type": "reply_chunk", "text": " ".join(sentences)}
                            )
                    elif event["type"] == "tool":
                        await self.tell({"type": "tool", "name": event["name"]})
                    elif event["type"] == "done":
                        if buffer.strip():
                            await self.speak(buffer)
                            await self.tell({"type": "reply_chunk", "text": buffer})
                        await self.tell({"type": "reply", "text": event["reply"]})
        except asyncio.CancelledError:
            raise
        except Exception as error:
            logger.exception("Voice turn failed")
            self.metrics = None
            await self.tell({"type": "error", "message": str(error)})
            return

        self.metrics["agent_ms"] = round((time.perf_counter() - heard_at) * 1000)
        await self.finish_turn()


async def keyterms_for(patient_id):
    if not patient_id:
        return []

    try:
        with session_scope() as db:
            return services.speech_keyterms(db, patient_id)
    except Exception:
        logger.warning("Could not load keyterms for patient %s", patient_id)
        return []


@router.websocket("/voice")
async def voice_socket(websocket: WebSocket):
    await websocket.accept()

    parameters = websocket.query_params
    session_id = parameters.get("session_id") or "voice"
    raw_patient = parameters.get("patient_id")
    patient_id = int(raw_patient) if raw_patient and raw_patient.isdigit() else None

    if not DEEPGRAM_API_KEY:
        await websocket.send_text(
            json.dumps({"type": "error", "message": "Speech is not set up on the server."})
        )
        await websocket.close()
        return

    session = VoiceSession(websocket, session_id, patient_id)

    try:
        opening = json.loads(await websocket.receive_text())
    except (WebSocketDisconnect, json.JSONDecodeError):
        return

    sample_rate = int(opening.get("sample_rate") or 16000)
    keyterms = await keyterms_for(patient_id)

    try:
        await session.open_streams(sample_rate, keyterms)
    except Exception as error:
        logger.error("Could not reach Deepgram: %s", error)
        await session.tell(
            {"type": "error", "message": "I could not start the speech service."}
        )
        await websocket.close()
        return

    await session.warm_up()
    await session.tell(
        {"type": "ready", "sample_rate": TTS_SAMPLE_RATE, "keyterms": len(keyterms)}
    )

    pumps = [
        asyncio.create_task(session.pump_client()),
        asyncio.create_task(session.pump_stt()),
        asyncio.create_task(session.pump_tts()),
    ]

    try:
        done, _ = await asyncio.wait(pumps, return_when=asyncio.FIRST_COMPLETED)
        for task in done:
            error = task.exception()
            if error and not isinstance(error, WebSocketDisconnect):
                logger.error("Voice session ended: %s", error)
    finally:
        for task in pumps:
            task.cancel()
        if session.turn is not None:
            session.turn.cancel()
        await session.close_streams()
        try:
            await websocket.close()
        except RuntimeError:
            pass
