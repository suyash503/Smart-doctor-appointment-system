from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from .database import Base
from datetime import datetime

class User(Base):
    """this handles both Patients and Doctors for unified login or roles."""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    email = Column(String, unique=True, index=True)
    role = Column(String)

class Doctor(Base):
    """ details specifically for doctors."""
    __tablename__ = "doctors"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    specialization = Column(String)

    user = relationship("User")

class Appointment(Base):
    """the core table the LLM will manipulate."""
    __tablename__ = "appointments"
    
    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("users.id"))
    doctor_id = Column(Integer, ForeignKey("doctors.id"))
    appointment_time = Column(DateTime)
    symptoms = Column(Text)
    status = Column(String, default="booked")

class MedicalRecord(Base):
    """Something a patient records about their own health."""
    __tablename__ = "medical_records"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("users.id"), index=True)
    category = Column(String, index=True)
    title = Column(String)
    details = Column(Text)
    recorded_on = Column(DateTime, default=datetime.now)

    patient = relationship("User")

class Prescription(Base):
    """A medication a patient is taking or has taken."""
    __tablename__ = "prescriptions"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("users.id"), index=True)
    doctor_id = Column(Integer, ForeignKey("doctors.id"), nullable=True)
    medication = Column(String)
    dosage = Column(String)
    frequency = Column(String)
    started_on = Column(DateTime, default=datetime.now)
    ended_on = Column(DateTime, nullable=True)
    status = Column(String, default="active")
    notes = Column(Text, nullable=True)

    patient = relationship("User")
    doctor = relationship("Doctor")

class PhotoUpload(Base):
    """A photo the patient uploaded, and whatever the vision model read from it."""
    __tablename__ = "photo_uploads"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("users.id"), index=True)
    filename = Column(String)
    content_type = Column(String)
    stored_path = Column(String)
    uploaded_at = Column(DateTime, default=datetime.now)
    status = Column(String, default="pending", index=True)
    summary = Column(Text, nullable=True)
    extracted = Column(Text, nullable=True)
    error = Column(Text, nullable=True)

    patient = relationship("User")

class ChatMessage(Base):
    """Stores the multi-turn conversation history."""
    __tablename__ = "chat_messages"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, index=True)
    role = Column(String)
    content = Column(Text)
    timestamp = Column(DateTime, default=datetime.now)