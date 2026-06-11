import os
from datetime import datetime, timedelta
import pytz
from google.oauth2 import service_account
from googleapiclient.discovery import build

GOOGLE_SERVICE_ACCOUNT_FILE = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE")
GOOGLE_CALENDAR_ID = os.getenv("GOOGLE_CALENDAR_ID", "primary")

def sync_to_google_calendar(booking):
    """
    Inserts a confirmed booking directly into the business owner's Google Calendar
    using Google service account OAuth credentials.
    """
    if not GOOGLE_SERVICE_ACCOUNT_FILE or not os.path.exists(GOOGLE_SERVICE_ACCOUNT_FILE):
        print("[INFO] Google Service Account credentials file not found. Skipping Google Calendar direct sync.")
        return False
        
    try:
        # Define scopes
        SCOPES = ['https://www.googleapis.com/auth/calendar']
        
        # Authenticate using Service Account
        creds = service_account.Credentials.from_service_account_file(
            GOOGLE_SERVICE_ACCOUNT_FILE, scopes=SCOPES
        )
        
        # Build Calendar service
        service = build('calendar', 'v3', credentials=creds)
        
        # Parse times
        dt_str = f"{booking['date']} {booking['time']}"
        naive_dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M")
        
        # Localize to Tenerife timezone
        tz = pytz.timezone('Atlantic/Canary')
        start_dt = tz.localize(naive_dt)
        end_dt = start_dt + timedelta(hours=3, minutes=30)
        
        # Format for Google Calendar API (RFC3339)
        start_rfc = start_dt.isoformat()
        end_rfc = end_dt.isoformat()
        
        event_body = {
            'summary': f"Teide Quad: {booking['name']} ({booking['single_quads']}S, {booking['double_quads']}D)",
            'location': 'Extreme Prime Tours SL, Las Américas, Tenerife',
            'description': (
                f"Booking Details:\n"
                f"- Customer Name: {booking['name']}\n"
                f"- Email: {booking['email']}\n"
                f"- Phone: {booking['phone']}\n"
                f"- Single Quads: {booking['single_quads']}\n"
                f"- Double Quads: {booking['double_quads']}\n"
                f"- Booking ID: {booking['id']}\n"
                f"- Total Price: €{booking['total_price']}\n"
            ),
            'start': {
                'dateTime': start_rfc,
                'timeZone': 'Atlantic/Canary',
            },
            'end': {
                'dateTime': end_rfc,
                'timeZone': 'Atlantic/Canary',
            },
            'reminders': {
                'useDefault': False,
                'overrides': [
                    {'method': 'email', 'minutes': 24 * 60},
                    {'method': 'popup', 'minutes': 60},
                ],
            },
        }
        
        # Insert event
        created_event = service.events().insert(
            calendarId=GOOGLE_CALENDAR_ID, body=event_body
        ).execute()
        
        print(f"Successfully synced event to Google Calendar: {created_event.get('htmlLink')}")
        return True
        
    except Exception as e:
        print(f"Error syncing to Google Calendar: {e}")
        return False
