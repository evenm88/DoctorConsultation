from pydantic import BaseModel, EmailStr

from typing import Dict
class SlotCheckRequest(BaseModel):
    doctor_id: str

class SlotBookingRequest(BaseModel):
    doctor_id: str
    patient_id: str
    time: str  # "09:00"

class SlotReleaseRequest(BaseModel):
    doctor_id: str
    time: str

class Symptoms(BaseModel):
    primary_complaint: str
    duration: str

class PatientRequest(BaseModel):
    name: str
    age: int
    email: str
    blood_pressure: str
    sugar_level: str
    symptoms: Symptoms
from pydantic import BaseModel, Field
from typing import Dict

class DoctorRequest(BaseModel):
    doctor_id: str = Field(alias="_id")
    name: str
    role: str
    email: str
    availability: Dict[str, bool]

class AvailabilityRequest(BaseModel):
    doctorid: str
    date: str
class BookAppointmentRequest(BaseModel):
    doctorid: str
    patientid: str
    time: str  # Format: "2025-06-28T09:00:00"


# Pydantic model for request body
class EmailRequest(BaseModel):
    email: EmailStr
    html_content: str