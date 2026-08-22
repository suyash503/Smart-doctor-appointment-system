import json
from datetime import datetime

from sqlalchemy.orm import Session

from database import models

RECORD_CATEGORIES = ("condition", "allergy", "surgery", "note")


class BookingError(Exception):
    pass


def parse_datetime(value, field="time"):
    if value is None:
        return None

    if isinstance(value, datetime):
        return value

    try:
        return datetime.fromisoformat(str(value).replace("Z", ""))
    except ValueError:
        raise BookingError(
            f"Invalid {field} format. Use ISO format such as 2026-05-10T10:00:00."
        )


def parse_appointment_time(value):
    return parse_datetime(value, "time")


def require_patient(db: Session, patient_id: int):
    patient = db.query(models.User).filter(models.User.id == patient_id).first()
    if patient is None:
        raise BookingError(f"No patient found with id {patient_id}.")

    return patient


def require_doctor(db: Session, doctor_id: int):
    doctor = db.query(models.Doctor).filter(models.Doctor.id == doctor_id).first()
    if doctor is None:
        raise BookingError(f"No doctor found with id {doctor_id}.")

    return doctor


def commit(db: Session, instance=None):
    try:
        db.commit()
        if instance is not None:
            db.refresh(instance)
    except Exception:
        db.rollback()
        raise

    return instance


def list_doctors(db: Session):
    doctors = db.query(models.Doctor).all()
    return [
        {
            "id": doctor.id,
            "name": doctor.user.name if doctor.user else "Unknown",
            "specialty": doctor.specialization,
        }
        for doctor in doctors
    ]


def list_patient_appointments(db: Session, patient_id: int):
    return (
        db.query(models.Appointment)
        .filter(models.Appointment.patient_id == patient_id)
        .order_by(models.Appointment.appointment_time.asc())
        .all()
    )


def create_appointment(db: Session, patient_id, doctor_id, appointment_time, symptoms):
    when = parse_appointment_time(appointment_time)
    require_patient(db, patient_id)
    require_doctor(db, doctor_id)

    clash = (
        db.query(models.Appointment)
        .filter(
            models.Appointment.doctor_id == doctor_id,
            models.Appointment.appointment_time == when,
            models.Appointment.status == "booked",
        )
        .first()
    )
    if clash is not None:
        raise BookingError(
            f"Doctor {doctor_id} already has an appointment at {when.isoformat()}."
        )

    appointment = models.Appointment(
        patient_id=patient_id,
        doctor_id=doctor_id,
        appointment_time=when,
        symptoms=symptoms,
        status="booked",
    )
    db.add(appointment)

    return commit(db, appointment)


def cancel_appointment(db: Session, appointment_id: int):
    appointment = (
        db.query(models.Appointment)
        .filter(models.Appointment.id == appointment_id)
        .first()
    )
    if appointment is None:
        raise BookingError(f"No appointment found with id {appointment_id}.")

    appointment.status = "cancelled"

    return commit(db, appointment)


def add_medical_record(db: Session, patient_id, category, title, details=None, recorded_on=None):
    require_patient(db, patient_id)

    category = (category or "").strip().lower()
    if category not in RECORD_CATEGORIES:
        allowed = ", ".join(RECORD_CATEGORIES)
        raise BookingError(f"Unknown category {category!r}. Use one of: {allowed}.")

    if not (title or "").strip():
        raise BookingError("A medical record needs a title.")

    record = models.MedicalRecord(
        patient_id=patient_id,
        category=category,
        title=title.strip(),
        details=details,
        recorded_on=parse_datetime(recorded_on, "date") or datetime.now(),
    )
    db.add(record)

    return commit(db, record)


def list_medical_records(db: Session, patient_id, category=None):
    query = db.query(models.MedicalRecord).filter(
        models.MedicalRecord.patient_id == patient_id
    )

    if category:
        query = query.filter(models.MedicalRecord.category == category.strip().lower())

    return query.order_by(models.MedicalRecord.recorded_on.desc()).all()


def delete_medical_record(db: Session, record_id: int):
    record = (
        db.query(models.MedicalRecord)
        .filter(models.MedicalRecord.id == record_id)
        .first()
    )
    if record is None:
        raise BookingError(f"No medical record found with id {record_id}.")

    db.delete(record)
    commit(db)

    return record


def add_prescription(
    db: Session,
    patient_id,
    medication,
    dosage,
    frequency,
    doctor_id=None,
    started_on=None,
    notes=None,
):
    require_patient(db, patient_id)

    if doctor_id is not None:
        require_doctor(db, doctor_id)

    if not (medication or "").strip():
        raise BookingError("A prescription needs a medication name.")

    prescription = models.Prescription(
        patient_id=patient_id,
        doctor_id=doctor_id,
        medication=medication.strip(),
        dosage=dosage,
        frequency=frequency,
        started_on=parse_datetime(started_on, "date") or datetime.now(),
        status="active",
        notes=notes,
    )
    db.add(prescription)

    return commit(db, prescription)


def list_prescriptions(db: Session, patient_id, active_only=False):
    query = db.query(models.Prescription).filter(
        models.Prescription.patient_id == patient_id
    )

    if active_only:
        query = query.filter(models.Prescription.status == "active")

    return query.order_by(models.Prescription.started_on.desc()).all()


def stop_prescription(db: Session, prescription_id: int, ended_on=None):
    prescription = (
        db.query(models.Prescription)
        .filter(models.Prescription.id == prescription_id)
        .first()
    )
    if prescription is None:
        raise BookingError(f"No prescription found with id {prescription_id}.")

    prescription.status = "stopped"
    prescription.ended_on = parse_datetime(ended_on, "date") or datetime.now()

    return commit(db, prescription)


def describe_record(record):
    line = f"- {record.recorded_on:%Y-%m-%d} {record.title} ({record.category})"
    if record.details:
        line += f": {record.details}"

    return line


def describe_prescription(prescription):
    parts = [prescription.medication, prescription.dosage, prescription.frequency]
    label = " ".join(part for part in parts if part)

    return f"- {label} (started {prescription.started_on:%Y-%m-%d}, {prescription.status})"


def format_patient_history(db: Session, patient_id: int) -> str:
    patient = require_patient(db, patient_id)

    sections = []

    records = list_medical_records(db, patient_id)
    allergies = [record for record in records if record.category == "allergy"]
    conditions = [record for record in records if record.category != "allergy"]

    if allergies:
        sections.append(
            "Allergies:\n" + "\n".join(describe_record(record) for record in allergies)
        )

    if conditions:
        sections.append(
            "Conditions and notes:\n"
            + "\n".join(describe_record(record) for record in conditions)
        )

    prescriptions = list_prescriptions(db, patient_id)
    if prescriptions:
        sections.append(
            "Medications:\n"
            + "\n".join(describe_prescription(item) for item in prescriptions)
        )

    appointments = list_patient_appointments(db, patient_id)
    if appointments:
        sections.append(
            "Appointments:\n"
            + "\n".join(
                f"- {item.appointment_time:%Y-%m-%d %H:%M} {item.symptoms} ({item.status})"
                for item in appointments
            )
        )

    if not sections:
        return f"Nothing on record yet for {patient.name} (patient {patient_id})."

    header = f"Medical history for {patient.name} (patient {patient_id})"

    return header + "\n\n" + "\n\n".join(sections)


def get_photo(db: Session, photo_id: int):
    photo = (
        db.query(models.PhotoUpload)
        .filter(models.PhotoUpload.id == photo_id)
        .first()
    )
    if photo is None:
        raise BookingError(f"No photo found with id {photo_id}.")

    return photo


def mark_duplicates(db: Session, patient_id, medications, records):
    existing_medications = {
        (prescription.medication or "").strip().lower()
        for prescription in list_prescriptions(db, patient_id, active_only=True)
    }
    existing_records = {
        ((record.category or "").lower(), (record.title or "").strip().lower())
        for record in list_medical_records(db, patient_id)
    }

    for item in medications:
        name = (item.get("medication") or "").strip().lower()
        item["already_on_file"] = name in existing_medications

    for item in records:
        key = ((item.get("category") or "").lower(), (item.get("title") or "").strip().lower())
        item["already_on_file"] = key in existing_records


def photo_draft(photo, db: Session = None):
    try:
        extracted = json.loads(photo.extracted) if photo.extracted else {}
    except json.JSONDecodeError:
        extracted = {}

    medications = extracted.get("medications", [])
    records = extracted.get("records", [])

    if db is not None:
        mark_duplicates(db, photo.patient_id, medications, records)

    return {
        "id": photo.id,
        "patient_id": photo.patient_id,
        "filename": photo.filename,
        "uploaded_at": photo.uploaded_at.isoformat() if photo.uploaded_at else None,
        "status": photo.status,
        "summary": photo.summary,
        "error": photo.error,
        "medications": medications,
        "records": records,
    }


def create_photo(db: Session, patient_id, filename, content_type, stored_path):
    require_patient(db, patient_id)

    photo = models.PhotoUpload(
        patient_id=patient_id,
        filename=filename,
        content_type=content_type,
        stored_path=str(stored_path),
        status="pending",
    )
    db.add(photo)

    return commit(db, photo)


def save_extraction(db: Session, photo, extracted=None, error=None):
    photo.extracted = json.dumps(extracted) if extracted else None
    photo.summary = (extracted or {}).get("summary") or None
    photo.error = error
    photo.status = "failed" if error else "pending"

    return commit(db, photo)


def list_pending_photos(db: Session, patient_id):
    return (
        db.query(models.PhotoUpload)
        .filter(
            models.PhotoUpload.patient_id == patient_id,
            models.PhotoUpload.status == "pending",
        )
        .order_by(models.PhotoUpload.uploaded_at.desc())
        .all()
    )


def confirm_photo(db: Session, photo_id, medications=None, records=None):
    photo = get_photo(db, photo_id)

    if photo.status == "confirmed":
        raise BookingError(f"Photo {photo_id} has already been confirmed.")

    if photo.status == "discarded":
        raise BookingError(f"Photo {photo_id} was discarded.")

    draft = photo_draft(photo)
    chosen_medications = draft["medications"] if medications is None else medications
    chosen_records = draft["records"] if records is None else records

    created = {"medications": [], "records": []}

    for item in chosen_records:
        record = add_medical_record(
            db,
            photo.patient_id,
            item.get("category") or "note",
            item.get("title"),
            item.get("details") or None,
        )
        created["records"].append(record.id)

    for item in chosen_medications:
        prescription = add_prescription(
            db,
            photo.patient_id,
            item.get("medication"),
            item.get("dosage") or None,
            item.get("frequency") or None,
            None,
            None,
            item.get("notes") or None,
        )
        created["medications"].append(prescription.id)

    photo.status = "confirmed"
    commit(db, photo)

    return created


def discard_photo(db: Session, photo_id):
    photo = get_photo(db, photo_id)

    if photo.status == "confirmed":
        raise BookingError(f"Photo {photo_id} was already confirmed and cannot be discarded.")

    photo.status = "discarded"

    return commit(db, photo)
