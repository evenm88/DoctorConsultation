import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
client = MongoClient(MONGO_URI)

# Access DB and Collections
db = client["OnlineDoctorConsultation"]
doctors_collection = db["Doctors"]
patients_collection = db["Patients"]
appointments_collection = db["Appointments"]


