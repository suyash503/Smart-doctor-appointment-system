from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class AppointmentCreate(BaseModel):
    patient_id: int
    doctor_id: int
    appointment_time: datetime
    symptoms: str


class DoctorResponse(BaseModel):
    id: int
    name: str
    specialty: str

    class Config:
        from_attributes = True


class AppointmentResponse(BaseModel):
    id: int
    doctor_id: int
    patient_id: int
    appointment_time: datetime
    symptoms: Optional[str] = None
    status: str = "booked"

    class Config:
        from_attributes = True
