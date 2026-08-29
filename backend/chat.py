from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from agent import run_turn
from database.database import get_db

router = APIRouter(prefix="/chat", tags=["Agentic Chat"])


class ChatRequest(BaseModel):
    session_id: str
    message: str
    patient_id: Optional[int] = None


@router.post("/")
async def chat_with_agent(request: ChatRequest, db: Session = Depends(get_db)):
    reply = await run_turn(db, request.session_id, request.message, request.patient_id)

    return {"reply": reply}
