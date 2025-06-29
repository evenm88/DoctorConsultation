from fastapi import FastAPI, HTTPException
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from dotenv import load_dotenv
from google_meet import create_meet_event
from models.appointment_model import AppointmentCreate, PrescriptionUpdate
from mongo import appointments_collection,prescriptions_collection
from datetime import datetime
from models.models import AvailabilityRequest, BookAppointmentRequest, DoctorRequest, EmailRequest, PrescriptionRequest, SlotCheckRequest, SlotBookingRequest, SlotReleaseRequest
import logging
from fastapi import APIRouter
# Add this to your imports
from datetime import datetime
import uuid


# from google_meet import create_meet_event
import os
import uuid
from datetime import datetime
from models.models import PatientRequest
from mongo import patients_collection



from fastapi_mcp import FastApiMCP
from fastapi.middleware.cors import CORSMiddleware

from mongo import doctors_collection, patients_collection

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Or ["http://localhost:3000"] for specific origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
load_dotenv()

SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
FROM_EMAIL = os.getenv("FROM_EMAIL")
SMTP_USERNAME = os.getenv("SMTP_USERNAME")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")

# def send_email(to_email: str, subject: str, html: str):
#     message = Mail(
#         from_email=FROM_EMAIL,
#         to_emails=to_email,
#         subject=subject,
#         html_content=html,
#     )
#     try:
#         sg = SendGridAPIClient(SENDGRID_API_KEY)
#         print(SENDGRID_API_KEY)
#         response = sg.send(message)
#         print("Email sent")
#         return True
#     except Exception as e:
#         print(f"SendGrid Error: {e}")
#         return False

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

SMTP_SERVER = "smtp.gmail.com"    
SMTP_PORT = 587                     
FROM_EMAIL = SMTP_USERNAME           

def send_email(to_email: str, subject: str, html: str) -> bool:
    try:
        # Create message container
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = FROM_EMAIL
        msg["To"] = to_email

        # Attach HTML content
        part = MIMEText(html, "html")
        msg.attach(part)

        # Connect to SMTP server
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()  # Secure the connection
        server.login(SMTP_USERNAME, SMTP_PASSWORD)

        # Send email
        server.sendmail(FROM_EMAIL, to_email, msg.as_string())
        server.quit()

        print("Email sent successfully")
        return True
    except Exception as e:
        print(f"SMTP Error: {e}")
        return False


@app.post("/send-email" , operation_id="send_email")
async def send_appointment_email(request: EmailRequest):
    """
    Send appointment confirmation email
    """
    subject = "Appointment Confirmation"
    html_content = """
    <html>
        <body>
            <p>Dear Sir,</p>
            <p>Your appointment has been booked.</p>
            <br>
            <p>Best regards,</p>
            <p>Your Service Team</p>
        </body>
    </html>
    """
    print(request.email)
    # Send the email
    email_sent = send_email(request.email, subject, request.html_content)

    
    if email_sent:
        return {"message": "Mail sent successfully", "email": request.email}
    else:
        raise HTTPException(status_code=500, detail="Failed to send email")


@app.post("/patient/upsert", operation_id="upsert_patient")
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
    


@app.post("/doctor/upsert", operation_id="upsert_doctor")
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

#Generate Meet Link
@app.get("/generate-meet-link", operation_id="generate_meet_link")
def generate_meet_link():
    try:
        link = create_meet_event()
        return {"meet_url": link}
    except Exception as e:
        return {"error": str(e)}

@app.post("/check-availability", operation_id="check_availability")
def check_availability(data: AvailabilityRequest):
    doctor = doctors_collection.find_one({"_id": data.doctorid})
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")

    availability = doctor.get("availability", {})
    return {"availability": availability}

@app.post("/book-appointment", operation_id="book_appointment")
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


#
# API Endpoint
# Updated API Endpoint
@app.post("/add-prescription", operation_id="add_prescription")
def add_prescription(data: PrescriptionRequest):
    try:
        # Generate unique prescription ID
        prescription_id = f"presc{str(uuid.uuid4())[:8]}"
        
        # Create prescription data
        prescription_data = {
            "_id": prescription_id,
            "doctor_id": data.doctorid,
            "patient_id": data.patientid,
            "prescriptions": [
                {
                    "name": item.name,
                    "count": item.count,
                    "dosage": item.dosage
                } for item in data.prescriptions
            ],
            "created_at": datetime.now().isoformat(),
            "status": "active"
        }
        
        # Insert the prescription
        result = prescriptions_collection.insert_one(prescription_data)
        
        if result.inserted_id:
            return {
                "message": "Prescription added successfully",
                "status": "success",
                "prescription_id": prescription_id,
                "prescription_details": {
                    "doctor_id": data.doctorid,
                    "patient_id": data.patientid,
                    "total_medicines": len(data.prescriptions),
                    "prescriptions": [
                        {
                            "name": item.name,
                            "count": item.count,
                            "dosage": item.dosage,
                            "dosage_breakdown": {
                                "morning": item.dosage.split('-')[0] if len(item.dosage.split('-')) >= 1 else "0",
                                "afternoon": item.dosage.split('-')[1] if len(item.dosage.split('-')) >= 2 else "0",
                                "night": item.dosage.split('-')[2] if len(item.dosage.split('-')) >= 3 else "0"
                            }
                        } for item in data.prescriptions
                    ]
                }
            }
        else:
            return {
                "message": "Failed to add prescription",
                "status": "failed"
            }
            
    except Exception as e:
        logging.error(f"Error in add_prescription: {str(e)}")
        return {
            "message": "Internal server error",
            "status": "failed",
            "error": str(e)
        }

@app.get("/get-prescriptions/{patient_id}", operation_id="get_prescriptions")
def get_prescriptions(patient_id: str):
    try:
        # Find all prescriptions for the patient
        prescriptions = list(prescriptions_collection.find({"patient_id": patient_id}))
        
        if prescriptions:
            return {
                "message": "Prescriptions found",
                "status": "success",
                "count": len(prescriptions),
                "prescriptions": prescriptions
            }
        else:
            return {
                "message": "No prescriptions found for this patient",
                "status": "success",
                "count": 0,
                "prescriptions": []
            }
            
    except Exception as e:
        logging.error(f"Error in get_prescriptions: {str(e)}")
        return {
            "message": "Internal server error",
            "status": "failed",
            "error": str(e)
        }

# Optional: Get prescriptions by doctor
@app.get("/get-prescriptions-by-doctor/{doctor_id}", operation_id="get_prescriptions_by_doctor")
def get_prescriptions_by_doctor(doctor_id: str):
    try:
        # Find all prescriptions by the doctor
        prescriptions = list(prescriptions_collection.find({"doctor_id": doctor_id}))
        
        if prescriptions:
            return {
                "message": "Prescriptions found",
                "status": "success",
                "count": len(prescriptions),
                "prescriptions": prescriptions
            }
        else:
            return {
                "message": "No prescriptions found for this doctor",
                "status": "success",
                "count": 0,
                "prescriptions": []
            }
            
    except Exception as e:
        logging.error(f"Error in get_prescriptions_by_doctor: {str(e)}")
        return {
            "message": "Internal server error",
            "status": "failed",
            "error": str(e)
        }


mcp = FastApiMCP(app, include_operations= [
    "upsert_patient",
    "upsert_doctor",
    "generate_meet_link",
    "check_availability",
    "book_appointment",
    "send_email",
    "add_prescription",
    "get_prescriptions",
    "get_prescriptions_by_doctor"
])
mcp.mount()