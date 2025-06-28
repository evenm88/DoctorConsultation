from fastapi import FastAPI, HTTPException
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from dotenv import load_dotenv
from models.appointment_model import AppointmentCreate, PrescriptionUpdate
from mongo import appointments_collection
from datetime import datetime
from models.models import AvailabilityRequest, BookAppointmentRequest, DoctorRequest, SlotCheckRequest, SlotBookingRequest, SlotReleaseRequest
import logging
from fastapi import APIRouter
from google_meet import create_meet_event
import os
import uuid
from datetime import datetime
from models.models import PatientRequest
from mongo import patients_collection


from mongo import doctors_collection, patients_collection

app = FastAPI()
load_dotenv()

SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
FROM_EMAIL = os.getenv("FROM_EMAIL")


def send_email(to_email: str, subject: str, html: str):
    message = Mail(
        from_email=FROM_EMAIL,
        to_emails=to_email,
        subject=subject,
        html_content=html,
    )
    try:
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        sg.send(message)
        print("Email sent")
    except Exception as e:
        print(f"SendGrid Error: {e}")

@app.post("/patient/upsert")
def upsert_patient(data: PatientRequest):
    try:
        if not data.email or not data.email.strip():
            raise HTTPException(status_code=400, detail="Email is required")
        
        normalized_email = data.email.strip().lower()
        
        patient_data = {
            "name": data.name,
            "age": data.age,
            "email": normalized_email,
            "blood_pressure": data.blood_pressure,
            "sugar_level": data.sugar_level,
            "symptoms": {
                "primary_complaint": data.symptoms.primary_complaint,
                "duration": data.symptoms.duration
            }
        }
        
        # Use upsert to either update existing or create new
        result = patients_collection.update_one(
            {"email": normalized_email},
            {"$set": patient_data},
            upsert=True
        )
        
        if result.upserted_id:
            return {
                "message": "New patient added",
                "patient_details": {
                    "_id": str(result.upserted_id),
                    **patient_data
                }
            }
        else:
            # Get the updated patient
            updated_patient = patients_collection.find_one({"email": normalized_email})
            return {
                "message": "Patient updated",
                "patient_details": {
                    "_id": str(updated_patient["_id"]),
                    **patient_data
                }
            }
            
    except Exception as e:
        logging.error(f"Error in upsert_patient: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
    
from pydantic import BaseModel
from typing import Dict
import logging


@app.post("/doctor/upsert")
def upsert_doctor(data: DoctorRequest):
    try:
        if not data.email or not data.email.strip():
            raise HTTPException(status_code=400, detail="Email is required")
        
        if not data.doctor_id or not data.doctor_id.strip():
            raise HTTPException(status_code=400, detail="Doctor ID is required")
        
        normalized_email = data.email.strip().lower()
        normalized_id = data.doctor_id.strip()  # Changed from data._id
        
        doctor_data = {
            "_id": normalized_id,
            "name": data.name,
            "role": data.role,
            "email": normalized_email,
            "availability": data.availability
        }
        
        # Use upsert to either update existing or create new based on _id
        result = doctors_collection.update_one(
            {"_id": normalized_id},
            {"$set": doctor_data},
            upsert=True
        )
        
        if result.upserted_id:
            return {
                "message": "New doctor added",
                "doctor_details": doctor_data
            }
        else:
            # Get the updated doctor
            updated_doctor = doctors_collection.find_one({"_id": normalized_id})
            return {
                "message": "Doctor updated",
                "doctor_details": {
                    "_id": updated_doctor["_id"],
                    "name": updated_doctor["name"],
                    "role": updated_doctor["role"],
                    "email": updated_doctor["email"],
                    "availability": updated_doctor["availability"]
                }
            }
            
    except Exception as e:
        logging.error(f"Error in upsert_doctor: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/generate-meet-link")
def generate_meet_link():
    try:
        link = create_meet_event()
        return {"meet_url": link}
    except Exception as e:
        return {"error": str(e)}

@app.post("/check-availability")
def check_availability(data: AvailabilityRequest):
    doctor = doctors_collection.find_one({"_id": data.doctorid})
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")

    availability = doctor.get("availability", {})
    return {"availability": availability}

@app.post("/book-appointment")
def book_appointment(data: BookAppointmentRequest):
    try:
        # Check if the time slot is already booked
        existing_appointment = appointments_collection.find_one({
            "time": data.time
        })
        
        if existing_appointment:
            return {
                "message": "No slot available",
                "status": "failed"
            }
        
        # Generate unique appointment ID
        appointment_id = f"apt{str(uuid.uuid4())[:8]}"
        
        # Generate room ID
        room_id = f"room{str(uuid.uuid4())[:4]}"
        
        # Create appointment data
        appointment_data = {
            "_id": appointment_id,
            "patient_id": data.patientid,
            "doctor_id": data.doctorid,
            "time": data.time,
            "roomid": room_id,
            "status": "confirmed",
            "created_at": datetime.now().isoformat()
        }
        
        # Insert the appointment
        result = appointments_collection.insert_one(appointment_data)
        
        if result.inserted_id:
            return {
                "message": "Appointment booked successfully",
                "status": "success",
                "appointment_id": appointment_id,
                "room_id": room_id
            }
        else:
            return {
                "message": "Failed to book appointment",
                "status": "failed"
            }
            
    except Exception as e:
        logging.error(f"Error in book_appointment: {str(e)}")
        return {
            "message": "Internal server error",
            "status": "failed",
            "error": str(e)
        }

# @app.post("/book-slot")
# def book_slot(data: SlotBookingRequest):
#     doctor = doctors_collection.find_one({"_id": data.doctor_id})
#     patient = patients_collection.find_one({"_id": data.patient_id})

#     if not doctor or not patient:
#         raise HTTPException(status_code=404, detail="Doctor or patient not found")

#     if doctor["availability"].get(data.time) != "yes":
#         raise HTTPException(status_code=400, detail="Slot not available")

#     # Mark slot as booked
#     doctors_collection.update_one(
#         {"_id": data.doctor_id},
#         {"$set": {f"availability.{data.time}": "no"}}
#     )

#     # Send email
#     subject = "Doctor Consultation Slot Booked"
#     html = f"""
#         <p>Dear {doctor['name']},</p>
#         <p>{patient['name']} has booked your <strong>{data.time}</strong> slot for consultation today.</p>
#     """
#     send_email(doctor["email"], subject, html)

#     return {"message": "Slot booked and doctor notified"}


# @app.post("/release-slot")
# def release_slot(data: SlotReleaseRequest):
#     doctor = doctors_collection.find_one({"_id": data.doctor_id})
#     if not doctor:
#         raise HTTPException(status_code=404, detail="Doctor not found")

#     doctors_collection.update_one(
#         {"_id": data.doctor_id},
#         {"$set": {f"availability.{data.time}": "yes"}}
#     )
#     return {"message": f"Slot {data.time} released for doctor {data.doctor_id}"}
# @app.post("/create-appointment")
# def create_appointment(data: AppointmentCreate):
#     new_apt = {
#         "patient_id": data.patient_id,
#         "doctor_id": data.doctor_id,
#         "time": data.time,
#         "prescription": data.prescription,
#         "status": data.status
#     }
#     result = appointments_collection.insert_one(new_apt)
#     return {"message": "Appointment created", "appointment_id": str(result.inserted_id)}
# @app.post("/add-prescription")
# def add_prescription(data: PrescriptionUpdate):
#     result = appointments_collection.update_one(
#         {"_id": data.appointment_id},
#         {"$set": {"prescription": data.prescription, "status": "completed"}}
#     )
#     if result.modified_count == 0:
#         raise HTTPException(status_code=404, detail="Appointment not found")
#     return {"message": "Prescription added and status updated to completed"}
