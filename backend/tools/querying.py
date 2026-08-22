from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

import services
from database.database import get_db
from schemas import schemas

router = APIRouter(prefix="/tools/query", tags=["Querying Tools"])


@router.get("/doctors", response_model=List[schemas.DoctorResponse])
def get_all_doctors(db: Session = Depends(get_db)):
    return services.list_doctors(db)


@router.get("/appointments/{patient_id}", response_model=List[schemas.AppointmentResponse])
def get_patient_appointments(patient_id: int, db: Session = Depends(get_db)):
    return services.list_patient_appointments(db, patient_id)
