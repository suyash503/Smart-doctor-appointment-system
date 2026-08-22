from datetime import datetime

from sqlalchemy.orm import Session

from database import models


class BookingError(Exception):
    pass


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


def parse_appointment_time(value):
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value).replace("Z", ""))
    except ValueError:
        raise BookingError(
            "Invalid time format. Use ISO format such as 2026-05-10T10:00:00."
        )


def create_appointment(db: Session, patient_id, doctor_id, appointment_time, symptoms):
    when = parse_appointment_time(appointment_time)

    patient = db.query(models.User).filter(models.User.id == patient_id).first()
    if patient is None:
        raise BookingError(f"No patient found with id {patient_id}.")

    doctor = db.query(models.Doctor).filter(models.Doctor.id == doctor_id).first()
    if doctor is None:
        raise BookingError(f"No doctor found with id {doctor_id}.")

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

    try:
        db.add(appointment)
        db.commit()
        db.refresh(appointment)
    except Exception:
        db.rollback()
        raise

    return appointment


def format_patient_history(db: Session, patient_id: int) -> str:
    appointments = list_patient_appointments(db, patient_id)
    if not appointments:
        return f"No appointments on record for patient {patient_id}."

    lines = [
        f"- {appointment.appointment_time}: {appointment.symptoms} (status: {appointment.status})"
        for appointment in appointments
    ]
    return f"Medical history for patient {patient_id}:\n" + "\n".join(lines)


def cancel_appointment(db: Session, appointment_id: int):
    appointment = (
        db.query(models.Appointment)
        .filter(models.Appointment.id == appointment_id)
        .first()
    )
    if appointment is None:
        raise BookingError(f"No appointment found with id {appointment_id}.")

    appointment.status = "cancelled"

    try:
        db.commit()
        db.refresh(appointment)
    except Exception:
        db.rollback()
        raise

    return appointment
