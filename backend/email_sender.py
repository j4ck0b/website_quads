import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime, timedelta
import pytz
from icalendar import Calendar, Event

# Load email environment configurations
SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_PORT = os.getenv("SMTP_PORT", "587")
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
BUSINESS_OWNER_EMAIL = os.getenv("BUSINESS_OWNER_EMAIL")

def generate_ics_content(booking):
    """
    Generates an iCalendar (.ics) file content as bytes for a booking.
    The Teide Quad Expedition lasts for 3.5 hours.
    """
    cal = Calendar()
    cal.add('prodid', '-//Prime Quads Tenerife Booking System//EN')
    cal.add('version', '2.0')

    event = Event()
    event.add('summary', 'Teide National Park Quad Expedition')
    
    # Parse date and time
    # date format: YYYY-MM-DD
    # time format: HH:MM (e.g. 13:00, 18:00)
    dt_str = f"{booking['date']} {booking['time']}"
    naive_dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M")
    
    # Tenerife is in Europe/London or Atlantic/Canary timezone (usually WET/WEST, identical to UK time)
    tz = pytz.timezone('Atlantic/Canary')
    start_dt = tz.localize(naive_dt)
    end_dt = start_dt + timedelta(hours=3, minutes=30)  # 3.5 hours duration
    
    event.add('dtstart', start_dt)
    event.add('dtend', end_dt)
    event.add('dtstamp', datetime.now(pytz.utc))
    
    description = (
        f"Thank you for booking with Prime Quads Tenerife!\n\n"
        f"Booking ID: {booking['id']}\n"
        f"Customer: {booking['name']}\n"
        f"Phone: {booking['phone']}\n"
        f"Single Quads: {booking['single_quads']}\n"
        f"Double Quads: {booking['double_quads']}\n"
        f"Total Paid: €{booking['total_price']}\n\n"
        f"Please arrive 15 minutes before the tour starts. Don't forget your B driver's license (physical copy mandatory)!"
    )
    event.add('description', description)
    event.add('location', 'Extreme Prime Tours SL, Las Américas, Tenerife')
    event.add('uid', f"booking-{booking['id']}@primequads.com")
    
    cal.add_component(event)
    return cal.to_ical()

def send_booking_emails(booking):
    """
    Sends email confirmation with an attached .ics file to:
    1. The client (thanking them and providing event details)
    2. The business owner (notifying them of the new booking)
    """
    # Verify SMTP configuration
    if not all([SMTP_SERVER, SMTP_PORT, SMTP_USER, SMTP_PASSWORD]):
        print("[WARNING] SMTP settings are incomplete in .env. Skipping email sending.")
        print(f"[SANDBOX EMAIL LOG] Booking confirmed for {booking['name']} ({booking['email']}) on {booking['date']} at {booking['time']}")
        return False
        
    ics_bytes = generate_ics_content(booking)
    
    # 1. Send email to Client
    try:
        msg_client = MIMEMultipart()
        msg_client['From'] = SMTP_USER
        msg_client['To'] = booking['email']
        msg_client['Subject'] = 'Booking Confirmed - Teide Quad Expedition ✨'
        
        body_client = (
            f"Hi {booking['name']},\n\n"
            f"Your booking for the Teide National Park Quad Expedition is officially confirmed! 🏔️🏍️\n\n"
            f"--- Reservation Details ---\n"
            f"📅 Date: {booking['date']}\n"
            f"🕒 Time: {booking['time']} (Please arrive 15 minutes early)\n"
            f"🏍️ Single Quads (1-person): {booking['single_quads']}\n"
            f"🏍️ Double Quads (2-person): {booking['double_quads']}\n"
            f"💰 Total Paid: €{booking['total_price']}\n\n"
            f"📍 Meeting point: Extreme Prime Tours SL, Las Américas, Tenerife\n"
            f"🪪 Requirements: A valid physical B category driver's license (min. 1 year validity) is required for all drivers.\n\n"
            f"We have attached a calendar event file (.ics) to this email. You can open it to automatically add this tour to your Apple, Google, or Outlook calendar!\n\n"
            f"See you soon,\n"
            f"Prime Quads Team"
        )
        msg_client.attach(MIMEText(body_client, 'plain'))
        
        # Attach ICS
        part = MIMEBase('application', 'octet-stream')
        part.set_payload(ics_bytes)
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', 'attachment; filename="teide_quad_tour.ics"')
        msg_client.attach(part)
        
        # Connect & Send
        with smtplib.SMTP(SMTP_SERVER, int(SMTP_PORT)) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg_client)
            print(f"Confirmation email successfully sent to client: {booking['email']}")
            
    except Exception as e:
        print(f"Error sending email to client: {e}")

    # 2. Send email to Business Owner
    owner_email = BUSINESS_OWNER_EMAIL or SMTP_USER
    try:
        msg_owner = MIMEMultipart()
        msg_owner['From'] = SMTP_USER
        msg_owner['To'] = owner_email
        msg_owner['Subject'] = f"New Booking Confirmed: {booking['name']} - {booking['date']}"
        
        body_owner = (
            f"Hello Prime Quads Team,\n\n"
            f"A new booking has been confirmed via Stripe payment:\n\n"
            f"👤 Customer: {booking['name']}\n"
            f"✉️ Email: {booking['email']}\n"
            f"📞 Phone: {booking['phone']}\n"
            f"📅 Date: {booking['date']}\n"
            f"🕒 Time: {booking['time']}\n"
            f"🏍️ Single Quads: {booking['single_quads']}\n"
            f"🏍️ Double Quads: {booking['double_quads']}\n"
            f"💰 Total Amount: €{booking['total_price']}\n"
            f"🆔 Booking ID: {booking['id']}\n\n"
            f"Attached is the calendar file to add this to your system."
        )
        msg_owner.attach(MIMEText(body_owner, 'plain'))
        
        # Attach ICS
        part = MIMEBase('application', 'octet-stream')
        part.set_payload(ics_bytes)
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', 'attachment; filename="new_booking.ics"')
        msg_owner.attach(part)
        
        # Connect & Send
        with smtplib.SMTP(SMTP_SERVER, int(SMTP_PORT)) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg_owner)
            print(f"Notification email successfully sent to owner: {owner_email}")
            
    except Exception as e:
        print(f"Error sending email to business owner: {e}")
        
    return True
