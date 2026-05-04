from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database.database import get_db
import database.models as models
from schemas import schemas

# APIRouter lets us group related tools together
router = APIRouter(prefix="/tools/booking", tags=["Booking Tools"])

@router.post("/book", response_model=schemas.AppointmentResponse)
def book_appointment(
    appointment_data: schemas.AppointmentCreate,  
    db: Session = Depends(get_db)
):
    """
    MCP Tool: Books a new appointment for a patient.
    The LLM will read this exact description to understand when and how to use this tool!
    """
    # 1. Verify the doctor exists in the database
    doctor = db.query(models.Doctor).filter(models.Doctor.id == appointment_data.doctor_id).first()
    if not doctor:
        # If the LLM hallucinates a doctor ID, we throw an error back to it
        raise HTTPException(status_code=404, detail="Doctor not found. Please provide a valid doctor ID.")

    # 2. Create the new appointment record using our SQLAlchemy model
    new_appointment = models.Appointment(
        patient_id=appointment_data.patient_id,
        doctor_id=appointment_data.doctor_id,
        appointment_time=appointment_data.appointment_time,
        symptoms=appointment_data.symptoms,
        status="booked"
    )
    
    # 3. Save to the database
    db.add(new_appointment)
    db.commit()
    db.refresh(new_appointment) # Grabs the newly generated ID assigned by the database
    
    # 4. Return the SQLAlchemy object 
    # (FastAPI automatically filters it through our Pydantic AppointmentResponse schema)
    return new_appointment