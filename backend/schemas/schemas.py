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


class MedicalRecordCreate(BaseModel):
    patient_id: int
    category: str
    title: str
    details: Optional[str] = None
    recorded_on: Optional[datetime] = None


class MedicalRecordResponse(BaseModel):
    id: int
    patient_id: int
    category: str
    title: str
    details: Optional[str] = None
    recorded_on: datetime

    class Config:
        from_attributes = True


class PrescriptionCreate(BaseModel):
    patient_id: int
    medication: str
    dosage: Optional[str] = None
    frequency: Optional[str] = None
    doctor_id: Optional[int] = None
    started_on: Optional[datetime] = None
    notes: Optional[str] = None


class PrescriptionResponse(BaseModel):
    id: int
    patient_id: int
    doctor_id: Optional[int] = None
    medication: str
    dosage: Optional[str] = None
    frequency: Optional[str] = None
    started_on: datetime
    ended_on: Optional[datetime] = None
    status: str
    notes: Optional[str] = None

    class Config:
        from_attributes = True
