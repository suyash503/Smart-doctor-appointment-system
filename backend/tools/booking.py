from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database.database import get_db
from database import models
from schemas import schemas
from tools.google_cal import get_calendar_service
from datetime import datetime, timedelta

router = APIRouter()

@router.post("/book", response_model=schemas.AppointmentResponse)
def book_appointment(appointment: schemas.AppointmentCreate, db: Session = Depends(get_db)):
    
    # 1. Your existing database logic
    new_appointment = models.Appointment(
        patient_id=appointment.patient_id,
        doctor_id=appointment.doctor_id,
        time=appointment.appointment.time,
        symptoms=appointment.symptoms,
        status="booked"
    )
    db.add(new_appointment)
    db.commit()
    db.refresh(new_appointment)

    # 2. NEW: Google Calendar Logic
    try:
        service = get_calendar_service()
        
       
        start_time = datetime.fromisoformat(str(appointment.appointment.time).replace("Z", ""))
        end_time = start_time + timedelta(hours=1) # Assume 1 hour appointments

        event = {
            'summary': f'Doctor Appointment (Patient ID: {appointment.patient_id})',
            'description': f'Symptoms reported: {appointment.symptoms}',
            'start': {
                'dateTime': start_time.isoformat(),
                'timeZone': 'Asia/Kolkata',
            },
            'end': {
                'dateTime': end_time.isoformat(),
                'timeZone': 'Asia/Kolkata',
            },
        }

        event_result = service.events().insert(calendarId='primary', body=event).execute()
        print(f"SUCCESS: Calendar event created: {event_result.get('htmlLink')}")
        
    except Exception as e:
        print(f"WARNING: Database saved, but Google Calendar failed: {e}")

    return new_appointment