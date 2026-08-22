import json

from mcp.server.fastmcp import Context, FastMCP

import services
from database.database import Base, engine, session_scope

Base.metadata.create_all(bind=engine)

mcp = FastMCP("smart-doctor-scheduler")


def as_json(rows):
    return json.dumps(rows, default=str)


@mcp.resource("appointment://patient/{patient_id}/history")
def patient_history(patient_id: str) -> str:
    """Everything on file for a patient: allergies, conditions, medications and appointments."""
    with session_scope() as db:
        try:
            return services.format_patient_history(db, int(patient_id))
        except services.BookingError as error:
            return str(error)


@mcp.tool()
async def list_doctors(ctx: Context) -> str:
    """List every doctor in the hospital with their id and specialty."""
    with session_scope() as db:
        doctors = services.list_doctors(db)

    if not doctors:
        await ctx.info("No doctors are registered yet.")
        return "There are no doctors registered."

    return as_json(doctors)


@mcp.tool()
async def list_patient_appointments(patient_id: int, ctx: Context) -> str:
    """Look up every appointment belonging to a patient."""
    with session_scope() as db:
        appointments = services.list_patient_appointments(db, patient_id)
        payload = [
            {
                "id": appointment.id,
                "doctor_id": appointment.doctor_id,
                "appointment_time": appointment.appointment_time.isoformat(),
                "symptoms": appointment.symptoms,
                "status": appointment.status,
            }
            for appointment in appointments
        ]

    if not payload:
        return f"Patient {patient_id} has no appointments."

    return as_json(payload)


@mcp.tool()
async def book_appointment(
    patient_id: int,
    doctor_id: int,
    appointment_time: str,
    symptoms: str,
    ctx: Context,
) -> str:
    """Book an appointment for a patient with a doctor at an ISO 8601 time."""
    with session_scope() as db:
        try:
            appointment = services.create_appointment(
                db, patient_id, doctor_id, appointment_time, symptoms
            )
        except services.BookingError as error:
            await ctx.warning(str(error))
            return str(error)

        await ctx.info(f"Booked appointment {appointment.id} for patient {patient_id}.")
        return (
            f"Appointment {appointment.id} confirmed for "
            f"{appointment.appointment_time.isoformat()} with doctor {doctor_id}."
        )


@mcp.tool()
async def cancel_appointment(appointment_id: int, ctx: Context) -> str:
    """Cancel an existing appointment by its id."""
    with session_scope() as db:
        try:
            appointment = services.cancel_appointment(db, appointment_id)
        except services.BookingError as error:
            await ctx.warning(str(error))
            return str(error)

        await ctx.info(f"Cancelled appointment {appointment.id}.")
        return f"Appointment {appointment.id} is now cancelled."


@mcp.tool()
async def add_medical_record(
    patient_id: int,
    category: str,
    title: str,
    ctx: Context,
    details: str = "",
    recorded_on: str = "",
) -> str:
    """Add something to a patient's medical history.

    Category must be one of condition, allergy, surgery or note. Use the title for
    the name of the condition, allergy or procedure, and details for anything the
    patient adds about it. Pass recorded_on as an ISO date when the patient says
    the condition started, otherwise it is recorded as today.
    """
    with session_scope() as db:
        try:
            record = services.add_medical_record(
                db,
                patient_id,
                category,
                title,
                details or None,
                recorded_on or None,
            )
        except services.BookingError as error:
            await ctx.warning(str(error))
            return str(error)

        await ctx.info(f"Added {record.category} record {record.id} for patient {patient_id}.")
        return f"Recorded {record.category} '{record.title}' as record {record.id}."


@mcp.tool()
async def list_medical_records(patient_id: int, ctx: Context, category: str = "") -> str:
    """List a patient's medical history, optionally filtered to one category."""
    with session_scope() as db:
        records = services.list_medical_records(db, patient_id, category or None)
        payload = [
            {
                "id": record.id,
                "category": record.category,
                "title": record.title,
                "details": record.details,
                "recorded_on": record.recorded_on.isoformat(),
            }
            for record in records
        ]

    if not payload:
        return f"Patient {patient_id} has no medical history recorded."

    return as_json(payload)


@mcp.tool()
async def delete_medical_record(record_id: int, ctx: Context) -> str:
    """Remove a medical history entry the patient no longer wants on file."""
    with session_scope() as db:
        try:
            record = services.delete_medical_record(db, record_id)
        except services.BookingError as error:
            await ctx.warning(str(error))
            return str(error)

        await ctx.info(f"Deleted medical record {record_id}.")
        return f"Removed '{record.title}' from the patient's history."


@mcp.tool()
async def add_prescription(
    patient_id: int,
    medication: str,
    ctx: Context,
    dosage: str = "",
    frequency: str = "",
    doctor_id: int = 0,
    started_on: str = "",
    notes: str = "",
) -> str:
    """Record a medication a patient is taking.

    Dosage is the amount per dose such as 500mg, and frequency is how often they
    take it such as twice a day. Pass doctor_id when the patient knows which
    doctor prescribed it, and started_on as an ISO date if they remember it.
    """
    with session_scope() as db:
        try:
            prescription = services.add_prescription(
                db,
                patient_id,
                medication,
                dosage or None,
                frequency or None,
                doctor_id or None,
                started_on or None,
                notes or None,
            )
        except services.BookingError as error:
            await ctx.warning(str(error))
            return str(error)

        await ctx.info(f"Added prescription {prescription.id} for patient {patient_id}.")
        return f"Recorded {prescription.medication} as prescription {prescription.id}."


@mcp.tool()
async def list_prescriptions(patient_id: int, ctx: Context, active_only: bool = False) -> str:
    """List the medications on file for a patient."""
    with session_scope() as db:
        prescriptions = services.list_prescriptions(db, patient_id, active_only)
        payload = [
            {
                "id": prescription.id,
                "medication": prescription.medication,
                "dosage": prescription.dosage,
                "frequency": prescription.frequency,
                "doctor_id": prescription.doctor_id,
                "started_on": prescription.started_on.isoformat(),
                "ended_on": prescription.ended_on.isoformat() if prescription.ended_on else None,
                "status": prescription.status,
                "notes": prescription.notes,
            }
            for prescription in prescriptions
        ]

    if not payload:
        return f"Patient {patient_id} has no medications recorded."

    return as_json(payload)


@mcp.tool()
async def stop_prescription(prescription_id: int, ctx: Context, ended_on: str = "") -> str:
    """Mark a medication as no longer being taken."""
    with session_scope() as db:
        try:
            prescription = services.stop_prescription(db, prescription_id, ended_on or None)
        except services.BookingError as error:
            await ctx.warning(str(error))
            return str(error)

        await ctx.info(f"Stopped prescription {prescription_id}.")
        return f"Marked {prescription.medication} as stopped."


if __name__ == "__main__":
    mcp.run(transport="stdio")
