# Required imports and helper function
import datetime
import uuid
import os
# from google.oauth2 import service_account
# from googleapiclient.discovery import build

def get_credentials():
    """Get credentials either from file or environment variables"""
    
    # Debug: Print current working directory
    print(f"Current working directory: {os.getcwd()}")
    print(f"Files in current directory: {os.listdir('.')}")
    
    # Try to get service account info from environment variables first
    service_account_info = os.getenv('GOOGLE_SERVICE_ACCOUNT_INFO')
    
    if service_account_info:
        import json
        service_account_dict = json.loads(service_account_info)
        credentials = service_account.Credentials.from_service_account_info(
            service_account_dict,
            scopes=['https://www.googleapis.com/auth/calendar']
        )
        return credentials
    
    # Fallback to service account file with absolute path
    SERVICE_ACCOUNT_FILE = 'C:\Hackathon\DoctorConsultation\service-account.json'
    
    # Debug: Check if file exists
    print(f"Looking for file: {SERVICE_ACCOUNT_FILE}")
    print(f"File exists: {os.path.exists(SERVICE_ACCOUNT_FILE)}")
    print(f"Absolute path would be: {os.path.abspath(SERVICE_ACCOUNT_FILE)}")
    
    if os.path.exists(SERVICE_ACCOUNT_FILE):
        credentials = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE,
            scopes=['https://www.googleapis.com/auth/calendar']
        )
        return credentials
    
    raise FileNotFoundError(f"Service account file not found at {SERVICE_ACCOUNT_FILE} and GOOGLE_SERVICE_ACCOUNT_INFO environment variable not set")
# Simplified function without parameters
def create_meet_event():
    """Create Google Meet event with default participants"""
    doctor_email = "doctor@example.com"
    patient_email = "patient@example.com"
    duration_minutes = 30
    
    try:
        credentials = get_credentials()
        service = build('calendar', 'v3', credentials=credentials)

        now = datetime.datetime.utcnow()
        start_time = now.isoformat() + 'Z'
        end_time = (now + datetime.timedelta(minutes=duration_minutes)).isoformat() + 'Z'

        event_body = {
            "summary": "Doctor Consultation",
            "start": {
                "dateTime": start_time,
                "timeZone": "UTC"
            },
            "end": {
                "dateTime": end_time,
                "timeZone": "UTC"
            },
            "attendees": [
                {"email": doctor_email},
                {"email": patient_email}
            ],
            "conferenceData": {
                "createRequest": {
                    "requestId": str(uuid.uuid4()),
                    "conferenceSolutionKey": {
                        "type": "hangoutsMeet"
                    }
                }
            }
        }

        # Use the service account's primary calendar
        event = service.events().insert(
            calendarId="primary",
            body=event_body,
            conferenceDataVersion=1
        ).execute()

        meet_link = event.get("hangoutLink")
        if not meet_link:
            # Sometimes the link is in conferenceData
            conference_data = event.get("conferenceData", {})
            entry_points = conference_data.get("entryPoints", [])
            for entry_point in entry_points:
                if entry_point.get("entryPointType") == "video":
                    meet_link = entry_point.get("uri")
                    break
        
        return meet_link

    except Exception as e:
        raise Exception(f"Failed to create Google Meet event: {str(e)}")