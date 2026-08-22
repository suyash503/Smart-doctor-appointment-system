import logging
from datetime import timedelta

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from core.config import CALENDAR_TIMEZONE, CREDENTIALS_FILE, TOKEN_FILE

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/calendar.events"]

APPOINTMENT_LENGTH = timedelta(hours=1)


def get_calendar_service(allow_prompt=True):
    creds = None

    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)

    if creds and creds.valid:
        return build("calendar", "v3", credentials=creds)

    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    elif allow_prompt:
        flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_FILE), SCOPES)
        creds = flow.run_local_server(port=0)
    else:
        return None

    TOKEN_FILE.write_text(creds.to_json())

    return build("calendar", "v3", credentials=creds)


def add_appointment_to_calendar(appointment):
    if not TOKEN_FILE.exists():
        logger.info("Skipping calendar sync, no Google token has been authorised yet.")
        return None

    try:
        service = get_calendar_service(allow_prompt=False)
        if service is None:
            return None

        start = appointment.appointment_time
        event = {
            "summary": f"Doctor appointment (patient {appointment.patient_id})",
            "description": f"Symptoms reported: {appointment.symptoms}",
            "start": {"dateTime": start.isoformat(), "timeZone": CALENDAR_TIMEZONE},
            "end": {
                "dateTime": (start + APPOINTMENT_LENGTH).isoformat(),
                "timeZone": CALENDAR_TIMEZONE,
            },
        }

        created = service.events().insert(calendarId="primary", body=event).execute()
        logger.info("Created calendar event %s", created.get("htmlLink"))

        return created
    except Exception as error:
        logger.warning("Appointment %s saved but calendar sync failed: %s", appointment.id, error)
        return None


if __name__ == "__main__":
    get_calendar_service()
    print(f"Google Calendar authorised, token saved to {TOKEN_FILE}")
