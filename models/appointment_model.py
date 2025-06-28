from pydantic import BaseModel
from typing import Optional

class AppointmentCreate(BaseModel):
    patient_id: str
    doctor_id: str
    time: str  # ISO format or "2025-06-28T09:00:00"
    prescription: Optional[str] = None
    status: str = "scheduled"  # optional, default to scheduled

class PrescriptionUpdate(BaseModel):
    appointment_id: str
    prescription: str
