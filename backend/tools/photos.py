import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

import extraction
import services
from core.config import ALLOWED_IMAGE_TYPES, MAX_UPLOAD_BYTES, UPLOAD_DIR
from database.database import get_db

router = APIRouter(prefix="/records/photos", tags=["Photo Uploads"])

SUFFIXES = {"image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp"}


class DraftMedication(BaseModel):
    medication: str
    dosage: Optional[str] = ""
    frequency: Optional[str] = ""
    notes: Optional[str] = ""


class DraftRecord(BaseModel):
    category: str
    title: str
    details: Optional[str] = ""


class ConfirmRequest(BaseModel):
    medications: Optional[List[DraftMedication]] = None
    records: Optional[List[DraftRecord]] = None


def store_image(contents: bytes, content_type: str) -> str:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    destination = UPLOAD_DIR / f"{uuid.uuid4().hex}{SUFFIXES.get(content_type, '.img')}"
    destination.write_bytes(contents)

    return str(destination)


@router.post("", status_code=201)
async def upload_photo(
    patient_id: int = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=400, detail="Upload a PNG, JPEG or WebP image.")

    contents = await file.read()

    if not contents:
        raise HTTPException(status_code=400, detail="The uploaded file is empty.")

    if len(contents) > MAX_UPLOAD_BYTES:
        limit = MAX_UPLOAD_BYTES // (1024 * 1024)
        raise HTTPException(status_code=413, detail=f"Images must be under {limit}MB.")

    try:
        services.require_patient(db, patient_id)
    except services.BookingError as error:
        raise HTTPException(status_code=404, detail=str(error))

    stored_path = store_image(contents, file.content_type)
    photo = services.create_photo(db, patient_id, file.filename, file.content_type, stored_path)

    try:
        extracted = await extraction.extract_from_image(contents, file.content_type)
        services.save_extraction(db, photo, extracted=extracted)
    except extraction.ExtractionError as error:
        services.save_extraction(db, photo, error=str(error))

    return services.photo_draft(photo, db)


@router.get("/pending/{patient_id}")
def list_pending(patient_id: int, db: Session = Depends(get_db)):
    photos = services.list_pending_photos(db, patient_id)

    return [services.photo_draft(photo, db) for photo in photos]


@router.get("/draft/{photo_id}")
def get_draft(photo_id: int, db: Session = Depends(get_db)):
    try:
        return services.photo_draft(services.get_photo(db, photo_id), db)
    except services.BookingError as error:
        raise HTTPException(status_code=404, detail=str(error))


@router.get("/image/{photo_id}")
def get_image(photo_id: int, db: Session = Depends(get_db)):
    try:
        photo = services.get_photo(db, photo_id)
    except services.BookingError as error:
        raise HTTPException(status_code=404, detail=str(error))

    return FileResponse(photo.stored_path, media_type=photo.content_type)


@router.post("/{photo_id}/confirm")
def confirm(photo_id: int, request: ConfirmRequest, db: Session = Depends(get_db)):
    medications = None if request.medications is None else [m.model_dump() for m in request.medications]
    records = None if request.records is None else [r.model_dump() for r in request.records]

    try:
        created = services.confirm_photo(db, photo_id, medications, records)
    except services.BookingError as error:
        raise HTTPException(status_code=400, detail=str(error))

    return {
        "photo_id": photo_id,
        "added_medications": len(created["medications"]),
        "added_records": len(created["records"]),
    }


@router.post("/{photo_id}/discard")
def discard(photo_id: int, db: Session = Depends(get_db)):
    try:
        photo = services.discard_photo(db, photo_id)
    except services.BookingError as error:
        raise HTTPException(status_code=400, detail=str(error))

    return {"photo_id": photo.id, "status": photo.status}
