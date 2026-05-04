from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from database.database import get_db
import database.models as models
from schemas import schemas

# Set up the router
router = APIRouter(prefix="/tools/query", tags=["Querying Tools"])

@router.get("/doctors", response_model=List[schemas.DoctorResponse])
def get_all_doctors(db: Session = Depends(get_db)):
    # 1. This grabs the raw objects (which Pydantic hates)
    doctors = db.query(models.Doctor).all()
    
    # 2. We build a clean list of dictionaries that perfectly match the Pydantic schema
    result = []
    for doc in doctors:
        result.append({
            "id": doc.id,
            "name": doc.user.name if doc.user else "Unknown", 
            "specialty": doc.specialization 
        })
        
    # 3. THE FIX: Make sure this says `return result`
    return result

@router.get("/appointments/{patient_id}", response_model=List[schemas.AppointmentResponse])
def get_patient_appointments(patient_id: int, db: Session = Depends(get_db)):
    """
    MCP Tool: Retrieves all upcoming appointments for a specific patient ID.
    The LLM uses this to remind patients of their schedule.
    """
    # Fetch all appointments matching the patient ID
    appointments = db.query(models.Appointment).filter(
        models.Appointment.patient_id == patient_id
    ).all()
    
    # It's totally fine if a patient has 0 appointments, so we just return an empty list
    return appointments