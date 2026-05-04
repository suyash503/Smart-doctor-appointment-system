from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from .database import Base
from datetime import datetime

class User(Base):
    """Handles both Patients and Doctors for unified login/roles."""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    email = Column(String, unique=True, index=True)
    role = Column(String)  # Expected: "patient" or "doctor"

class Doctor(Base):
    """Extended details specifically for doctors."""
    __tablename__ = "doctors"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    specialization = Column(String)
    
    user = relationship("User")

class Appointment(Base):
    """The core transactional table the LLM will manipulate."""
    __tablename__ = "appointments"
    
    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("users.id"))
    doctor_id = Column(Integer, ForeignKey("doctors.id"))
    appointment_time = Column(DateTime)
    symptoms = Column(Text)
    status = Column(String, default="booked")  # e.g., booked, cancelled, completed
    # Add this to the bottom of your models.py file

class ChatMessage(Base):
    """Stores the multi-turn conversation history."""
    __tablename__ = "chat_messages"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, index=True) # A unique ID for the user's current chat session
    role = Column(String)                   # 'user', 'assistant', or 'tool'
    content = Column(Text)                  # The actual message text
    timestamp = Column(DateTime, default=datetime.now)