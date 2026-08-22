from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

import services
from database.database import get_db
from schemas import schemas

router = APIRouter(prefix="/records", tags=["Medical Records"])


@router.post("/history", response_model=schemas.MedicalRecordResponse, status_code=201)
def add_medical_record(record: schemas.MedicalRecordCreate, db: Session = Depends(get_db)):
    try:
        return services.add_medical_record(
            db,
            record.patient_id,
            record.category,
            record.title,
            record.details,
            record.recorded_on,
        )
    except services.BookingError as error:
        raise HTTPException(status_code=400, detail=str(error))


@router.get("/history/{patient_id}", response_model=List[schemas.MedicalRecordResponse])
def list_medical_records(
    patient_id: int,
    category: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
):
    return services.list_medical_records(db, patient_id, category)


@router.delete("/history/{record_id}", status_code=204)
def delete_medical_record(record_id: int, db: Session = Depends(get_db)):
    try:
        services.delete_medical_record(db, record_id)
    except services.BookingError as error:
        raise HTTPException(status_code=404, detail=str(error))


@router.post("/prescriptions", response_model=schemas.PrescriptionResponse, status_code=201)
def add_prescription(prescription: schemas.PrescriptionCreate, db: Session = Depends(get_db)):
    try:
        return services.add_prescription(
            db,
            prescription.patient_id,
            prescription.medication,
            prescription.dosage,
            prescription.frequency,
            prescription.doctor_id,
            prescription.started_on,
            prescription.notes,
        )
    except services.BookingError as error:
        raise HTTPException(status_code=400, detail=str(error))


@router.get("/prescriptions/{patient_id}", response_model=List[schemas.PrescriptionResponse])
def list_prescriptions(
    patient_id: int,
    active_only: bool = Query(default=False),
    db: Session = Depends(get_db),
):
    return services.list_prescriptions(db, patient_id, active_only)


@router.post("/prescriptions/{prescription_id}/stop", response_model=schemas.PrescriptionResponse)
def stop_prescription(prescription_id: int, db: Session = Depends(get_db)):
    try:
        return services.stop_prescription(db, prescription_id)
    except services.BookingError as error:
        raise HTTPException(status_code=404, detail=str(error))


@router.get("/summary/{patient_id}")
def patient_summary(patient_id: int, db: Session = Depends(get_db)):
    try:
        return {"patient_id": patient_id, "summary": services.format_patient_history(db, patient_id)}
    except services.BookingError as error:
        raise HTTPException(status_code=404, detail=str(error))
