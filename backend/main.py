import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import chat
import voice
from core.config import ALLOWED_ORIGINS
from database.database import Base, engine
from mcp_client import toolbox
from tools import booking, photos, querying, records

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        await toolbox.start()
        logger.info("Connected to the smart-doctor MCP server.")
    except Exception as error:
        logger.error("Could not start the MCP server: %s", error)

    try:
        yield
    finally:
        await toolbox.stop()


app = FastAPI(title="Smart Doctor Assistant API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(booking.router)
app.include_router(querying.router)
app.include_router(records.router)
app.include_router(photos.router)
app.include_router(chat.router)
app.include_router(voice.router)


@app.get("/")
def read_root():
    return {"status": "ok", "mcp_connected": toolbox.connected}
