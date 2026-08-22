from datetime import datetime, timedelta

from database.database import Base, engine, session_scope
from database import models


def seed_data():
    Base.metadata.create_all(bind=engine)

    with session_scope() as db:
        print("Cleaning out old data...")
        db.query(models.Appointment).delete()
        db.query(models.Doctor).delete()
        db.query(models.User).delete()
        db.commit()

        print("Seeding dummy data...")
        doctor_user = models.User(
            name="Dr. Gregory House", email="house@hospital.com", role="doctor"
        )
        patient = models.User(
            name="John Doe", email="johndoe@example.com", role="patient"
        )
        db.add_all([doctor_user, patient])
        db.commit()

        doctor = models.Doctor(user_id=doctor_user.id, specialization="Cardiology")
        db.add(doctor)
        db.commit()

        db.add_all(
            [
                models.Appointment(
                    patient_id=patient.id,
                    doctor_id=doctor.id,
                    appointment_time=datetime.now() - timedelta(days=5),
                    symptoms="Mild chest pain",
                    status="completed",
                ),
                models.Appointment(
                    patient_id=patient.id,
                    doctor_id=doctor.id,
                    appointment_time=datetime.now() + timedelta(days=2),
                    symptoms="Follow-up checkup",
                    status="booked",
                ),
            ]
        )
        db.commit()

        print(f"Done. Doctor id {doctor.id}, patient id {patient.id}.")


if __name__ == "__main__":
    seed_data()
