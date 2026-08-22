from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

import services
from database.database import get_db
from schemas import schemas
from tools.google_cal import add_appointment_to_calendar

router = APIRouter(tags=["Booking"])


@router.post("/book", response_model=schemas.AppointmentResponse)
def book_appointment(appointment: schemas.AppointmentCreate, db: Session = Depends(get_db)):
    try:
        booked = services.create_appointment(
            db,
            appointment.patient_id,
            appointment.doctor_id,
            appointment.appointment_time,
            appointment.symptoms,
        )
    except services.BookingError as error:
        raise HTTPException(status_code=400, detail=str(error))

    add_appointment_to_calendar(booked)

    return booked


@router.post("/cancel/{appointment_id}", response_model=schemas.AppointmentResponse)
def cancel_appointment(appointment_id: int, db: Session = Depends(get_db)):
    try:
        return services.cancel_appointment(db, appointment_id)
    except services.BookingError as error:
        raise HTTPException(status_code=404, detail=str(error))
