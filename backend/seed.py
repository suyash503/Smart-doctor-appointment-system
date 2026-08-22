from datetime import datetime, timedelta

from database.database import Base, engine, session_scope
from database import models


def seed_data():
    Base.metadata.create_all(bind=engine)

    with session_scope() as db:
        print("Cleaning out old data...")
        db.query(models.Prescription).delete()
        db.query(models.MedicalRecord).delete()
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
        db.add_all(
            [
                models.MedicalRecord(
                    patient_id=patient.id,
                    category="allergy",
                    title="Penicillin",
                    details="Rash and swelling within an hour of the first dose",
                    recorded_on=datetime(2019, 6, 2),
                ),
                models.MedicalRecord(
                    patient_id=patient.id,
                    category="condition",
                    title="Type 2 diabetes",
                    details="Managed with medication and diet",
                    recorded_on=datetime(2021, 3, 14),
                ),
                models.MedicalRecord(
                    patient_id=patient.id,
                    category="surgery",
                    title="Appendectomy",
                    details="Keyhole, no complications",
                    recorded_on=datetime(2015, 11, 20),
                ),
            ]
        )

        db.add_all(
            [
                models.Prescription(
                    patient_id=patient.id,
                    doctor_id=doctor.id,
                    medication="Metformin",
                    dosage="500mg",
                    frequency="Twice a day with food",
                    started_on=datetime(2021, 3, 20),
                    status="active",
                ),
                models.Prescription(
                    patient_id=patient.id,
                    doctor_id=doctor.id,
                    medication="Atorvastatin",
                    dosage="10mg",
                    frequency="Once a day at night",
                    started_on=datetime(2022, 1, 10),
                    ended_on=datetime(2024, 5, 1),
                    status="stopped",
                    notes="Stopped after cholesterol came down",
                ),
            ]
        )
        db.commit()

        print(f"Done. Doctor id {doctor.id}, patient id {patient.id}.")


if __name__ == "__main__":
    seed_data()
