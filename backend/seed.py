from database.database import SessionLocal
import database.models as models
from datetime import datetime, timedelta

def seed_data():
    # Open a database session
    db = SessionLocal()

    print("Cleaning out old data (if any)...")
    db.query(models.Appointment).delete()
    db.query(models.Doctor).delete()
    db.query(models.User).delete()
    db.commit()

    print("Seeding new dummy data...")

    # 1. Create Users (One Doctor, One Patient)
    dr_user = models.User(name="Dr. Gregory House", email="house@hospital.com", role="doctor")
    patient_user = models.User(name="John Doe", email="johndoe@example.com", role="patient")
    
    db.add(dr_user)
    db.add(patient_user)
    db.commit() # Commit to generate their IDs

    # 2. Create the Doctor Profile linked to the dr_user
    doctor_profile = models.Doctor(user_id=dr_user.id, specialization="Cardiology")
    db.add(doctor_profile)
    db.commit()

    # 3. Create a past appointment and a future appointment
    past_appt = models.Appointment(
        patient_id=patient_user.id,
        doctor_id=doctor_profile.id,
        appointment_time=datetime.now() - timedelta(days=5),
        symptoms="Mild chest pain",
        status="completed"
    )

    future_appt = models.Appointment(
        patient_id=patient_user.id,
        doctor_id=doctor_profile.id,
        appointment_time=datetime.now() + timedelta(days=2),
        symptoms="Follow-up checkup",
        status="booked"
    )

    db.add(past_appt)
    db.add(future_appt)
    db.commit()

    print(f"Success! Created Doctor ID: {doctor_profile.id} and Patient ID: {patient_user.id}")
    
    # Always close the session!
    db.close()

if __name__ == "__main__":
    seed_data()