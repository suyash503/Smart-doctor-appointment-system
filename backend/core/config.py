import os
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BACKEND_DIR / ".env")

DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{BACKEND_DIR / 'health_assistant.db'}")

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
GROQ_VISION_MODEL = os.getenv("GROQ_VISION_MODEL", "qwen/qwen3.6-27b")

DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")
DEEPGRAM_STT_MODEL = os.getenv("DEEPGRAM_STT_MODEL", "nova-3-medical")
DEEPGRAM_TTS_MODEL = os.getenv("DEEPGRAM_TTS_MODEL", "aura-2-thalia-en")
TTS_SAMPLE_RATE = int(os.getenv("TTS_SAMPLE_RATE", 24000))
ENDPOINTING_MS = int(os.getenv("ENDPOINTING_MS", 300))
UTTERANCE_END_MS = int(os.getenv("UTTERANCE_END_MS", 1000))

DEFAULT_ORIGINS = [
    "http://localhost:5173",
    "https://smart-doctor-ai.vercel.app",
    "https://smart-doctor-likeko96f-suyashs-projects-9cc08d7d.vercel.app",
]

ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv("ALLOWED_ORIGINS", ",".join(DEFAULT_ORIGINS)).split(",")
    if origin.strip()
]

CALENDAR_TIMEZONE = os.getenv("CALENDAR_TIMEZONE", "Asia/Kolkata")
TOKEN_FILE = BACKEND_DIR / "token.json"
CREDENTIALS_FILE = BACKEND_DIR / "credentials.json"

UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", str(BACKEND_DIR / "uploads")))
MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_BYTES", 8 * 1024 * 1024))
ALLOWED_IMAGE_TYPES = {"image/png", "image/jpeg", "image/webp"}
