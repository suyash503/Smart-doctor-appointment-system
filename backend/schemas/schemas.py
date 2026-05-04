from pydantic import BaseModel
from datetime import datetime
from typing import Optional
# Add this right below your imports, above the other classes

class AppointmentCreate(BaseModel):
    patient_id: int
    doctor_id: int
    appointment_time: datetime
    symptoms: str

# NEW: Model for returning doctor information
class DoctorResponse(BaseModel):
    id: int
    name: str
    specialty: str

    class Config:
        from_attributes = True 

# EXISTING: Your appointment model
class AppointmentResponse(BaseModel):
    id: int
    doctor_id: int # Good to have this so the LLM knows who the appointment is with
    patient_id: int
    appointment_time: datetime
    symptoms: Optional[str] = None
    status: str = "confirmed"

    class Config:
        from_attributes = True