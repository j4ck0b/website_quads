import os
import re
from datetime import datetime, timedelta
import pytz
import dateutil.parser
from google.oauth2 import service_account
from googleapiclient.discovery import build

GOOGLE_SERVICE_ACCOUNT_FILE = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE")
if GOOGLE_SERVICE_ACCOUNT_FILE and not os.path.isabs(GOOGLE_SERVICE_ACCOUNT_FILE):
    GOOGLE_SERVICE_ACCOUNT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), GOOGLE_SERVICE_ACCOUNT_FILE)

GOOGLE_CALENDAR_ID = os.getenv("GOOGLE_CALENDAR_ID", "primary")

def sync_to_google_calendar(booking):
    """
    Inserts a confirmed booking directly into the business owner's Google Calendar
    using Google service account OAuth credentials.
    """
    google_json_str = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
    if not google_json_str and (not GOOGLE_SERVICE_ACCOUNT_FILE or not os.path.exists(GOOGLE_SERVICE_ACCOUNT_FILE)):
        print("[INFO] Google Service Account credentials not found. Skipping Google Calendar direct sync.")
        return False
        
    try:
        # Define scopes
        SCOPES = ['https://www.googleapis.com/auth/calendar']
        
        # Authenticate using Service Account
        if google_json_str:
            import json
            info = json.loads(google_json_str)
            creds = service_account.Credentials.from_service_account_info(
                info, scopes=SCOPES
            )
        else:
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

def parse_quads_from_event(summary, description=""):
    """
    Parses the number of quads blocked or booked from an event title/description.
    """
    summary = (summary or "").strip()
    description = (description or "").strip()
    
    # 1. Check if it's a manual block/closure
    block_keywords = ["block", "blok", "close", "zamkn", "priv", "prywatn", "cerrar", "ocupado", "off"]
    if any(kw in summary.lower() for kw in block_keywords) or any(kw in description.lower() for kw in block_keywords):
        # Try to find a valid quad count (1 to 3) in the summary/description
        nums = [int(n) for n in re.findall(r"\b(\d+)\b", summary + " " + description) if 1 <= int(n) <= 3]
        if nums:
            return nums[0]
        else:
            # Block the entire tour slot (default max capacity is 3)
            return 3
            
    # 2. Check for standard pattern (XS, YD) or similar in summary/description
    single_count = 0
    double_count = 0
    text_to_search = f"{summary} {description}"
    
    # Match XS / X S / Xs
    s_match = re.search(r"(\d+)\s*[sS]\b", text_to_search)
    if s_match:
        single_count = int(s_match.group(1))
    else:
        # Match "X single"
        s_match_text = re.search(r"(\d+)\s*single", text_to_search, re.IGNORECASE)
        if s_match_text:
            single_count = int(s_match_text.group(1))
            
    # Match XD / X D / Xd
    d_match = re.search(r"(\d+)\s*[dD]\b", text_to_search)
    if d_match:
        double_count = int(d_match.group(1))
    else:
        # Match "X double" or "X podwoj" or "X doble"
        d_match_text = re.search(r"(\d+)\s*(double|podw|doble)", text_to_search, re.IGNORECASE)
        if d_match_text:
            double_count = int(d_match_text.group(1))
            
    if single_count > 0 or double_count > 0:
        return single_count + double_count
        
    # 3. If it contains booking keywords, default to 1 or any number found in summary
    booking_keywords = ["quad", "tour", "wycieczka", "book", "rezerw", "reser"]
    if any(kw in summary.lower() for kw in booking_keywords):
        nums = re.findall(r"\b(\d+)\b", summary)
        if nums:
            return int(nums[0])
        return 1
        
    # 4. Default for other calendar events
    return 1

def get_calendar_events_for_date(date_str):
    """
    Queries Google Calendar API for events on the given date (YYYY-MM-DD).
    Returns a dictionary of occupied capacity per slot, e.g. {"11:00": 2, "18:30": 0}.
    If Google credentials are not set or calendar sync fails, returns None.
    """
    google_json_str = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
    if not google_json_str and (not GOOGLE_SERVICE_ACCOUNT_FILE or not os.path.exists(GOOGLE_SERVICE_ACCOUNT_FILE)):
        return None
        
    try:
        # Define scopes
        SCOPES = ['https://www.googleapis.com/auth/calendar']
        
        # Authenticate using Service Account
        if google_json_str:
            import json
            info = json.loads(google_json_str)
            creds = service_account.Credentials.from_service_account_info(
                info, scopes=SCOPES
            )
        else:
            creds = service_account.Credentials.from_service_account_file(
                GOOGLE_SERVICE_ACCOUNT_FILE, scopes=SCOPES
            )
        
        # Build Calendar service
        service = build('calendar', 'v3', credentials=creds)
        
        # Tenerife timezone
        tz = pytz.timezone('Atlantic/Canary')
        
        # Start and end of the day in Tenerife local time
        start_dt = tz.localize(datetime.strptime(f"{date_str} 00:00:00", "%Y-%m-%d %H:%M:%S"))
        end_dt = tz.localize(datetime.strptime(f"{date_str} 23:59:59", "%Y-%m-%d %H:%M:%S"))
        
        # Format for API
        timeMin = start_dt.isoformat()
        timeMax = end_dt.isoformat()
        
        # Fetch events
        events_result = service.events().list(
            calendarId=GOOGLE_CALENDAR_ID,
            timeMin=timeMin,
            timeMax=timeMax,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        events = events_result.get('items', [])
        
        occupied = {
            "11:00": 0,
            "18:30": 0
        }
        
        for event in events:
            # Get event start time
            start_time_str = event['start'].get('dateTime')
            if not start_time_str:
                # All-day events do not block specific slots by default unless explicitly matching booking keywords
                continue
                
            # Parse start time and convert to local Tenerife time
            event_start = dateutil.parser.isoparse(start_time_str).astimezone(tz)
            hour = event_start.hour
            
            # Count quads blocked
            quads = parse_quads_from_event(event.get('summary'), event.get('description'))
            
            # Map start hour to slots (11:00 / 18:30)
            if 9 <= hour <= 13:
                occupied["11:00"] += quads
            elif 17 <= hour <= 20:
                occupied["18:30"] += quads
                
        return occupied
        
    except Exception as e:
        print(f"[ERROR] Error fetching events from Google Calendar: {e}")
        return None

def delete_from_google_calendar(booking_id):
    """
    Finds and deletes calendar event matching a booking ID.
    """
    google_json_str = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
    if not google_json_str and (not GOOGLE_SERVICE_ACCOUNT_FILE or not os.path.exists(GOOGLE_SERVICE_ACCOUNT_FILE)):
        print("[INFO] Google Service Account credentials not found. Skipping Google Calendar deletion.")
        return False
        
    try:
        # Define scopes
        SCOPES = ['https://www.googleapis.com/auth/calendar']
        
        # Authenticate using Service Account
        if google_json_str:
            import json
            info = json.loads(google_json_str)
            creds = service_account.Credentials.from_service_account_info(
                info, scopes=SCOPES
            )
        else:
            creds = service_account.Credentials.from_service_account_file(
                GOOGLE_SERVICE_ACCOUNT_FILE, scopes=SCOPES
            )
        
        # Build Calendar service
        service = build('calendar', 'v3', credentials=creds)
        
        # Search for events containing booking_id
        events_result = service.events().list(
            calendarId=GOOGLE_CALENDAR_ID,
            q=booking_id,
            singleEvents=True
        ).execute()
        events = events_result.get('items', [])
        
        if not events:
            print(f"[INFO] No calendar event found for booking ID: {booking_id}")
            return False
            
        for event in events:
            service.events().delete(calendarId=GOOGLE_CALENDAR_ID, eventId=event['id']).execute()
            print(f"Successfully deleted event {event['id']} from Google Calendar matching booking ID {booking_id}")
            
        return True
    except Exception as e:
        print(f"Error deleting event from Google Calendar: {e}")
        return False

