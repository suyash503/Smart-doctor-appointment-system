import json

from mcp.server.fastmcp import Context, FastMCP

import services
from database.database import Base, engine, session_scope

Base.metadata.create_all(bind=engine)

mcp = FastMCP("smart-doctor-scheduler")


@mcp.resource("appointment://patient/{patient_id}/history")
def patient_history(patient_id: str) -> str:
    """The full appointment history for a patient, oldest first."""
    with session_scope() as db:
        return services.format_patient_history(db, int(patient_id))


@mcp.tool()
async def list_doctors(ctx: Context) -> str:
    """List every doctor in the hospital with their id and specialty."""
    with session_scope() as db:
        doctors = services.list_doctors(db)

    if not doctors:
        await ctx.info("No doctors are registered yet.")
        return "There are no doctors registered."

    return json.dumps(doctors)


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

    return json.dumps(payload)


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


if __name__ == "__main__":
    mcp.run(transport="stdio")
