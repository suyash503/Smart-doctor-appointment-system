from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from groq import Groq
import os
import json
from dotenv import load_dotenv
from tools.querying import get_all_doctors, get_patient_appointments
from tools.booking import book_appointment
import schemas.schemas as schemas

from database.database import get_db
import database.models as models

# Import our actual tool functions 
from tools.querying import get_all_doctors

load_dotenv()

router = APIRouter(prefix="/chat", tags=["Agentic Chat"])

# Initialize Groq Client
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

class ChatRequest(BaseModel):
    session_id: str
    message: str

# Groq/OpenAI Tool Schema format
GROQ_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_all_doctors",
            "description": "Retrieves a list of all available doctors and their specialties.",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_patient_appointments",
            "description": "Retrieves the appointment history for a specific patient.",
            "parameters": {
                "type": "object",
                "properties": {
                    "patient_id": {"type": "integer", "description": "The ID of the patient"}
                },
                "required": ["patient_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "book_appointment",
            "description": "Books a new appointment for a patient.",
            "parameters": {
                "type": "object",
                "properties": {
                    "patient_id": {"type": "integer"},
                    "doctor_id": {"type": "integer"},
                    "appointment_time": {"type": "string", "description": "ISO format datetime string, e.g., 2026-05-10T10:00:00"},
                    "symptoms": {"type": "string", "description": "Short description of symptoms"}
                },
                "required": ["patient_id", "doctor_id", "appointment_time", "symptoms"]
            }
        }
    }
]

@router.post("/")
def chat_with_agent(request: ChatRequest, db: Session = Depends(get_db)):
    # --- 1. MEMORY: Fetch past conversation from the database ---
    past_messages = db.query(models.ChatMessage).filter(
        models.ChatMessage.session_id == request.session_id
    ).order_by(models.ChatMessage.timestamp.asc()).all()

    # Format history for Groq. We inject a System prompt first to guide the AI's behavior.
    messages_for_groq = [
        {"role": "system", "content": "You are a helpful hospital scheduling assistant. Always use your tools to look up doctors or appointments. Do not guess."}
    ]
    
    # Add historical messages
    for msg in past_messages:
         messages_for_groq.append({"role": msg.role, "content": msg.content})
    
    # --- 2. Append the new user message ---
    messages_for_groq.append({"role": "user", "content": request.message})
    
    # Save the user's message to the database
    new_user_msg = models.ChatMessage(session_id=request.session_id, role="user", content=request.message)
    db.add(new_user_msg)
    db.commit()

    # --- 3. THE LLM CALL: Ask Groq what to do ---
    # We use Llama 3.1 70B, which is excellent at tool calling
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=messages_for_groq,
        tools=GROQ_TOOLS,
        tool_choice="auto"
    )

    response_message = response.choices[0].message

    # --- 4. TOOL EXECUTION LOOP ---
    # Did Llama decide to use a tool?
    if response_message.tool_calls:
        # Append the AI's request to use the tool to the conversation history
        messages_for_groq.append(response_message)
        
        for tool_call in response_message.tool_calls:
            # We need to parse the arguments Groq sends us back into a Python dictionary
            args = json.loads(tool_call.function.arguments)
            
            tool_result = None
            
            if tool_call.function.name == "get_all_doctors":
                tool_result = get_all_doctors(db=db)
                
            elif tool_call.function.name == "get_patient_appointments":
                # We pass the specific patient_id the AI extracted from the conversation
                tool_result = get_patient_appointments(patient_id=args["patient_id"], db=db)
                
            elif tool_call.function.name == "book_appointment":
                # We format the AI's arguments into our strict Pydantic schema
                appointment_data = schemas.AppointmentCreate(**args)
                db_record = book_appointment(appointment=appointment_data, db=db)
                # Convert the database object to a dictionary so we can send it back to Groq
                tool_result = {
                    "id": db_record.id,
                    "status": db_record.status,
                    "time": str(db_record.appointment_time)
                }
                
            # Send the result back to Groq
            messages_for_groq.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "name": tool_call.function.name,
                "content": json.dumps(tool_result) 
            })
        
        # 5c. Call Groq a second time with the database results so it can answer the user
        second_response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages_for_groq
        )
        final_text = second_response.choices[0].message.content
    else:
        # Groq just wanted to chat normally
        final_text = response_message.content

    # --- 6. Save Groq's final text answer to our database memory ---
    new_ai_msg = models.ChatMessage(session_id=request.session_id, role="assistant", content=final_text)
    db.add(new_ai_msg)
    db.commit()

    return {"reply": final_text}