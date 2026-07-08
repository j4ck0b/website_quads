import os
import uuid
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

# Load environment variables first
load_dotenv()

# Initialize Stripe
import stripe
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")

# Import our custom database and integration layers
from db import (
    init_db, get_slot_availability, create_booking, get_booking_by_stripe_session, 
    confirm_booking, block_slot, unblock_slot, get_all_blocked_slots, 
    get_all_bookings, manually_confirm_booking, cancel_booking, subscribe_newsletter
)
from email_sender import send_booking_emails, send_contact_email
from calendar_sync import sync_to_google_calendar, delete_from_google_calendar
import html
import re

app = Flask(__name__)

# Configure CORS (Restrict origins to trusted domains, allow all in development mode)
if os.getenv("FLASK_ENV") == "development":
    CORS(app, resources={r"/api/*": {"origins": "*"}})
else:
    FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5500")
    allowed_origins = [url.strip() for url in FRONTEND_URL.split(",") if url.strip()]
    if not allowed_origins:
        allowed_origins = ["*"]
    CORS(app, resources={r"/api/*": {"origins": allowed_origins}})

# Helper functions for form safety
def check_honeypot(data):
    """Returns True if honeypot field is filled (bot activity), False otherwise."""
    if data and data.get("website_url"):
        return True
    return False

def sanitize_input(text, length_limit=100):
    """Sanitizes text to escape HTML tags and limits length."""
    if not text:
        return ""
    return html.escape(str(text).strip())[:length_limit]

# Endpoint-specific rate limiting configurations
PATH_LIMITS = {
    "/api/contact": (3, 60),      # 3 requests per 60 seconds
    "/api/bookings": (5, 60),     # 5 requests per 60 seconds
    "/api/availability": (30, 60), # 30 requests per 60 seconds
    "/api/newsletter": (3, 60)    # 3 requests per 60 seconds
}
IP_PATH_REQUESTS = {}

@app.before_request
def rate_limiter():
    """Applies strict rate limiting per path & IP, respecting proxies on Vercel."""
    import time
    path = request.path
    if path not in PATH_LIMITS:
        return
        
    # Extract client IP (handle Vercel proxies via X-Forwarded-For)
    ip = request.headers.get("X-Forwarded-For", request.remote_addr)
    if ip and "," in ip:
        ip = ip.split(",")[0].strip()
        
    now = time.time()
    limit_max, limit_window = PATH_LIMITS[path]
    
    if ip not in IP_PATH_REQUESTS:
        IP_PATH_REQUESTS[ip] = {}
    if path not in IP_PATH_REQUESTS[ip]:
        IP_PATH_REQUESTS[ip][path] = []
        
    # Clean up older records
    IP_PATH_REQUESTS[ip][path] = [t for t in IP_PATH_REQUESTS[ip][path] if now - t < limit_window]
    
    if len(IP_PATH_REQUESTS[ip][path]) >= limit_max:
        return jsonify({"error": f"Too many requests to {path}. Please try again later."}), 429
        
    IP_PATH_REQUESTS[ip][path].append(now)

@app.after_request
def add_security_headers(response):
    """Adds standard security headers to all HTTP responses."""
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    return response

@app.route("/api/availability", methods=["GET"])
def check_availability():
    """
    Returns available capacity for a given date.
    Query parameters: date (format: YYYY-MM-DD)
    """
    date_str = request.args.get("date")
    if not date_str:
        return jsonify({"error": "Missing date parameter"}), 400
        
    try:
        # Check availability (default capacity is 5 quads total per tour slot)
        slots = get_slot_availability(date_str)
        return jsonify({
            "date": date_str,
            "slots": slots
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/bookings", methods=["POST"])
def new_booking():
    """
    Creates a pending booking and returns a Stripe Checkout Session URL.
    """
    data = request.json
    if not data:
        return jsonify({"error": "Invalid request payload"}), 400
        
    # Honeypot spam/bot check
    if check_honeypot(data):
        return jsonify({"status": "success", "message": "Redirecting to payment..."}), 200

    # Required fields
    name = data.get("name")
    email = data.get("email")
    phone = data.get("phone")
    date_str = data.get("date")
    time_str = data.get("time")
    lang = data.get("lang", "en")
    
    if lang not in ["en", "pl", "es"]:
        lang = "en"
    
    # Input Validation & Sanitization
    if not all([name, email, phone, date_str, time_str]):
        return jsonify({"error": "Missing required fields"}), 400
        
    name = sanitize_input(name, 100)
    email = sanitize_input(email, 100)
    phone = sanitize_input(phone, 30)
    date_str = sanitize_input(date_str, 15)
    time_str = sanitize_input(time_str, 10)
    
    # Validate email format
    EMAIL_REGEX = r"(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$)"
    if not re.match(EMAIL_REGEX, email):
        return jsonify({"error": "Invalid email address format"}), 400
        
    try:
        single_quads = int(data.get("single_quads", 0))
        double_quads = int(data.get("double_quads", 0))
    except (ValueError, TypeError):
        return jsonify({"error": "Quad counts must be integers"}), 400
        
    if single_quads < 0 or double_quads < 0:
        return jsonify({"error": "Quad counts cannot be negative"}), 400
        
    if single_quads == 0 and double_quads == 0:
        return jsonify({"error": "Must select at least 1 quad bike"}), 400
        
    if single_quads + double_quads > 4:
        return jsonify({"error": "Cannot book more than 4 quads in total"}), 400
        
    try:
        # Check real-time availability before booking
        slots = get_slot_availability(date_str)
        requested_quads = single_quads + double_quads
        
        if time_str not in slots:
            return jsonify({"error": "Selected tour slot does not exist"}), 400
            
        # Check cut-off time rules and return helpful messages based on language
        # (Atlantic/Canary timezone)
        try:
            import pytz
            from datetime import datetime
            tz = pytz.timezone('Atlantic/Canary')
            now_in_tz = datetime.now(tz)
            slot_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            current_date = now_in_tz.date()
            
            is_past_cutoff = False
            if slot_date < current_date:
                is_past_cutoff = True
            elif slot_date == current_date:
                if time_str == "13:00":
                    cutoff_13 = now_in_tz.replace(hour=9, minute=0, second=0, microsecond=0)
                    if now_in_tz >= cutoff_13:
                        is_past_cutoff = True
                elif time_str == "18:30":
                    cutoff_18 = now_in_tz.replace(hour=16, minute=30, second=0, microsecond=0)
                    if now_in_tz >= cutoff_18:
                        is_past_cutoff = True
                        
            if is_past_cutoff:
                if lang == "pl":
                    err_msg = "Rezerwacja na tę godzinę jest już zamknięta. Wycieczka o 13:00 wymaga rezerwacji z minimum 4-godzinnym wyprzedzeniem, a o 18:30 z 2-godzinnym wyprzedzeniem."
                elif lang == "es":
                    err_msg = "La reserva para este horario ya está cerrada. La excursión de las 13:00 requiere reserva con al menos 4 horas de antelación, y la de las 18:30 con 2 horas de antelación."
                else:
                    err_msg = "Booking for this tour is now closed. The 13:00 tour requires booking at least 4 hours in advance, and the 18:30 tour requires 2 hours in advance."
                return jsonify({"error": err_msg}), 400
        except Exception as e:
            print(f"Error validating cut-off times in bookings endpoint: {e}")
            
        remaining_capacity = slots[time_str]
        if requested_quads > remaining_capacity:
            return jsonify({
                "error": f"Not enough slots available. Only {remaining_capacity} quad(s) left for this tour."
            }), 400
            
        # Reverted prices back to standard (Single = €120, Double = €140)
        total_price = (single_quads * 120) + (double_quads * 140)
        booking_id = str(uuid.uuid4())
        
        # Build Stripe Checkout Session
        line_items = []
        if single_quads > 0:
            line_items.append({
                'price_data': {
                    'currency': 'eur',
                    'product_data': {
                        'name': 'Teide Quad Expedition - Single Quad (1 Driver)',
                        'description': 'Premium 550cc quad tour to Mount Teide (Single Rider)',
                    },
                    'unit_amount': 12000, # €120.00
                },
                'quantity': single_quads,
            })
            
        if double_quads > 0:
            line_items.append({
                'price_data': {
                    'currency': 'eur',
                    'product_data': {
                        'name': 'Teide Quad Expedition - Double Quad (Driver + Passenger)',
                        'description': 'Premium 550cc quad tour to Mount Teide (Double Rider)',
                    },
                    'unit_amount': 14000, # €140.00
                },
                'quantity': double_quads,
            })
            
        # Determine the redirect origin dynamically (handling local dev, custom domain, Vercel URLs)
        origin = request.headers.get("Origin")
        fallback_url = os.getenv("FRONTEND_URL", "http://localhost:5500").split(",")[0].strip()
        if not origin:
            origin = fallback_url
        else:
            # Basic validation to ensure origin is a trusted domain
            import urllib.parse
            parsed_origin = urllib.parse.urlparse(origin).hostname
            if parsed_origin:
                is_trusted = (
                    parsed_origin in ["localhost", "127.0.0.1"] or
                    parsed_origin.endswith("primequads.com") or
                    parsed_origin.endswith("vercel.app")
                )
                if not is_trusted:
                    origin = fallback_url
            else:
                origin = fallback_url

        # Create Stripe Session
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=line_items,
            mode='payment',
            customer_email=email,
            success_url=f"{origin}/success.html?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{origin}/cancel.html",
            locale=lang,
            metadata={
                "booking_id": booking_id,
                "lang": lang
            }
        )
        
        # Save pending booking to database
        create_booking(
            booking_id=booking_id,
            name=name,
            email=email,
            phone=phone,
            date=date_str,
            time=time_str,
            single_quads=single_quads,
            double_quads=double_quads,
            total_price=total_price,
            stripe_session_id=session.id
        )
        
        return jsonify({
            "checkout_url": session.url,
            "booking_id": booking_id
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/contact", methods=["POST"])
def contact_form():
    """
    Handles submissions from the website contact form, validates fields, and sends an email to the owner.
    """
    data = request.json
    if not data:
        return jsonify({"error": "Invalid request payload"}), 400
        
    # Honeypot spam/bot check
    if check_honeypot(data):
        return jsonify({"status": "success", "message": "Message sent successfully"}), 200

    name = data.get("name")
    email = data.get("email")
    message = data.get("message")
    lang = data.get("lang", "en")
    
    if lang not in ["en", "pl", "es"]:
        lang = "en"
    
    if not all([name, email, message]):
        return jsonify({"error": "Missing required fields"}), 400
        
    name = sanitize_input(name, 100)
    email = sanitize_input(email, 100)
    message = sanitize_input(message, 3000)
    
    EMAIL_REGEX = r"(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$)"
    if not re.match(EMAIL_REGEX, email):
        return jsonify({"error": "Invalid email address format"}), 400
        
    success = send_contact_email(name, email, message, lang=lang)
    if success:
        return jsonify({"status": "success", "message": "Message sent successfully"}), 200
    else:
        return jsonify({"error": "Failed to send email. Check backend logs."}), 500

@app.route("/api/newsletter", methods=["POST"])
def newsletter_subscribe():
    """
    Handles newsletter subscriptions, validates fields, check honeypot, and inserts into DB.
    """
    data = request.json
    if not data:
        return jsonify({"error": "Invalid request payload"}), 400
        
    # Honeypot spam/bot check
    if check_honeypot(data):
        return jsonify({"status": "success", "message": "Subscribed successfully"}), 200

    email = data.get("email")
    
    if not email:
        return jsonify({"error": "Email is required"}), 400
        
    email = sanitize_input(email, 100)
    
    EMAIL_REGEX = r"(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$)"
    if not re.match(EMAIL_REGEX, email):
        return jsonify({"error": "Invalid email address format"}), 400
        
    success = subscribe_newsletter(email)
    if success:
        return jsonify({"status": "success", "message": "Subscribed successfully"}), 200
    else:
        return jsonify({"error": "Subscription failed. Please try again later."}), 500

@app.route("/api/webhook", methods=["POST"])
def stripe_webhook():
    """
    Handles secure Stripe webhook notifications to confirm bookings upon payment.
    """
    payload = request.data
    sig_header = request.headers.get("HTTP_STRIPE_SIGNATURE") or request.headers.get("Stripe-Signature")
    
    if not sig_header:
        return jsonify({"error": "Missing Stripe signature header"}), 400
        
    try:
        # Verify Stripe webhook signature to prevent spoofing
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
    except ValueError as e:
        # Invalid payload
        return jsonify({"error": "Invalid payload"}), 400
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        return jsonify({"error": "Invalid signature verification"}), 400
        
    # Handle the event
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        session_id = session.get("id")
        
        # Retrieve the booking by Stripe Session ID
        booking = get_booking_by_stripe_session(session_id)
        if booking:
            if booking["status"] == "pending":
                # Confirm booking status
                confirm_booking(booking["id"])
                booking["status"] = "confirmed" # Update locally for notifications
                
                # Retrieve lang from Stripe metadata
                lang = session.get("metadata", {}).get("lang", "en")
                booking["lang"] = lang
                
                # Send email confirmations with calendar invites (.ics)
                send_booking_emails(booking)
                
                # Sync directly to owner's Google Calendar
                sync_to_google_calendar(booking)
                
                print(f"[SUCCESS] Confirmed booking {booking['id']} via Webhook.")
            else:
                print(f"[INFO] Booking {booking['id']} is already confirmed.")
        else:
            print(f"[WARNING] Webhook received for Stripe session {session_id} but no matching booking found.")
            
    return jsonify({"status": "success"}), 200

@app.route("/api/booking-details", methods=["GET"])
def get_booking_details():
    """
    Returns confirmed booking details to show on the success.html page.
    """
    session_id = request.args.get("session_id")
    if not session_id:
        return jsonify({"error": "Missing session_id parameter"}), 400
        
    try:
        booking = get_booking_by_stripe_session(session_id)
        if booking and booking["status"] == "confirmed":
            return jsonify({
                "name": booking["name"],
                "email": booking["email"],
                "date": booking["date"],
                "time": booking["time"],
                "single_quads": booking["single_quads"],
                "double_quads": booking["double_quads"],
                "total_price": booking["total_price"]
            }), 200
        else:
            return jsonify({"error": "Booking not found or not confirmed yet"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ─── Admin CMS API Endpoints ─────────────────────────────────
import hmac
import hashlib
import time
import base64
import json

def generate_admin_token(username):
    # Token valid for 7 days
    expiry = int(time.time()) + (7 * 24 * 3600)
    payload = json.dumps({"user": username, "exp": expiry})
    payload_b64 = base64.urlsafe_b64encode(payload.encode()).decode()
    
    secret = os.getenv("STRIPE_SECRET_KEY", "fallback_secret_key_1234").encode()
    signature = hmac.new(secret, payload_b64.encode(), hashlib.sha256).hexdigest()
    return f"{payload_b64}.{signature}"

def verify_admin_token(token):
    if not token:
        return None
    try:
        if token.startswith("Bearer "):
            token = token[7:]
        parts = token.split(".")
        if len(parts) != 2:
            return None
        payload_b64, signature = parts
        
        secret = os.getenv("STRIPE_SECRET_KEY", "fallback_secret_key_1234").encode()
        expected_sig = hmac.new(secret, payload_b64.encode(), hashlib.sha256).hexdigest()
        
        if not hmac.compare_digest(signature, expected_sig):
            return None
            
        payload_bytes = base64.urlsafe_b64decode(payload_b64.encode())
        payload = json.loads(payload_bytes.decode())
        
        if time.time() > payload.get("exp", 0):
            return None
            
        return payload.get("user")
    except Exception:
        return None

def require_admin(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get("Authorization")
        user = verify_admin_token(token)
        if not user:
            return jsonify({"error": "Unauthorized"}), 401
        return f(*args, **kwargs)
    return decorated

@app.route("/api/admin/login", methods=["POST"])
def admin_login():
    data = request.json or {}
    username = data.get("username")
    password = data.get("password")
    
    expected_user = os.getenv("ADMIN_USERNAME", "admin")
    expected_pass = os.getenv("ADMIN_PASSWORD", "admin123")
    
    if username == expected_user and password == expected_pass:
        token = generate_admin_token(username)
        return jsonify({"token": token}), 200
    else:
        return jsonify({"error": "Invalid username or password"}), 401

@app.route("/api/admin/blocked", methods=["GET"])
@require_admin
def get_blocked():
    try:
        blocked = get_all_blocked_slots()
        return jsonify({"blocked": blocked}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/admin/block", methods=["POST"])
@require_admin
def block_date_time():
    data = request.json or {}
    date_str = data.get("date")
    time_str = data.get("time") # '13:00', '18:30', or 'all'
    try:
        quads = int(data.get("quads", 0))
    except (ValueError, TypeError):
        quads = 0
    
    if not date_str or not time_str:
        return jsonify({"error": "Missing date or time parameter"}), 400
        
    try:
        success = block_slot(date_str, time_str, quads)
        if success:
            return jsonify({"message": f"Successfully blocked {time_str} on {date_str} (quads: {quads})"}), 200
        else:
            return jsonify({"error": "This block already exists"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/admin/unblock", methods=["POST"])
@require_admin
def unblock_date_time():
    data = request.json or {}
    block_id = data.get("id")
    
    if not block_id:
        return jsonify({"error": "Missing block ID"}), 400
        
    try:
        unblock_slot(block_id)
        return jsonify({"message": "Successfully unblocked slot"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/admin/bookings", methods=["GET"])
@require_admin
def list_bookings():
    try:
        bookings = get_all_bookings()
        return jsonify({"bookings": bookings}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/admin/confirm-booking", methods=["POST"])
@require_admin
def admin_confirm_booking():
    data = request.json or {}
    booking_id = data.get("id")
    
    if not booking_id:
        return jsonify({"error": "Missing booking ID"}), 400
        
    try:
        booking = manually_confirm_booking(booking_id)
        if booking:
            # Send confirmation emails
            try:
                send_booking_emails(booking)
            except Exception as email_err:
                print(f"[ADMIN CONFIRM] Email sending failed: {email_err}")
                
            # Sync to Google Calendar
            try:
                sync_to_google_calendar(booking)
            except Exception as cal_err:
                print(f"[ADMIN CONFIRM] Google calendar sync failed: {cal_err}")
                
            return jsonify({"message": "Booking manually confirmed successfully"}), 200
        else:
            return jsonify({"error": "Booking not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/admin/cancel-booking", methods=["POST"])
@require_admin
def admin_cancel_booking():
    data = request.json or {}
    booking_id = data.get("id")
    
    if not booking_id:
        return jsonify({"error": "Missing booking ID"}), 400
        
    try:
        booking = cancel_booking(booking_id)
        if booking:
            # Sync cancellation by deleting event from Google Calendar if configured
            try:
                delete_from_google_calendar(booking_id)
            except Exception as cal_err:
                print(f"[ADMIN CANCEL] Google calendar deletion failed: {cal_err}")
                
            return jsonify({"message": "Booking cancelled successfully"}), 200
        else:
            return jsonify({"error": "Booking not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    # Initialize SQLite or PostgreSQL table schemas
    init_db()
    
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=(os.getenv("FLASK_ENV") == "development"))
