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
from db import init_db, get_slot_availability, create_booking, get_booking_by_stripe_session, confirm_booking
from email_sender import send_booking_emails, send_contact_email
from calendar_sync import sync_to_google_calendar

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

# Endpoint-specific rate limiting configurations
PATH_LIMITS = {
    "/api/contact": (3, 60),      # 3 requests per 60 seconds
    "/api/bookings": (5, 60),     # 5 requests per 60 seconds
    "/api/availability": (30, 60) # 30 requests per 60 seconds
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
        
    # Limit lengths to prevent memory/DoS abuse
    name = str(name).strip()[:100]
    email = str(email).strip()[:100]
    phone = str(phone).strip()[:30]
    date_str = str(date_str).strip()[:15]
    time_str = str(time_str).strip()[:10]
    
    # Validate email format
    import re
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
        
    if single_quads + double_quads > 5:
        return jsonify({"error": "Cannot book more than 5 quads in total"}), 400
        
    try:
        # Check real-time availability before booking
        slots = get_slot_availability(date_str)
        requested_quads = single_quads + double_quads
        
        if time_str not in slots:
            return jsonify({"error": "Selected tour slot does not exist"}), 400
            
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
        
    name = data.get("name")
    email = data.get("email")
    message = data.get("message")
    lang = data.get("lang", "en")
    
    if lang not in ["en", "pl", "es"]:
        lang = "en"
    
    if not all([name, email, message]):
        return jsonify({"error": "Missing required fields"}), 400
        
    # Validate and sanitize inputs to protect against large payloads
    name = str(name).strip()[:100]
    email = str(email).strip()[:100]
    message = str(message).strip()[:3000]
    
    import re
    EMAIL_REGEX = r"(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$)"
    if not re.match(EMAIL_REGEX, email):
        return jsonify({"error": "Invalid email address format"}), 400
        
    success = send_contact_email(name, email, message, lang=lang)
    if success:
        return jsonify({"status": "success", "message": "Message sent successfully"}), 200
    else:
        return jsonify({"error": "Failed to send email. Check backend logs."}), 500

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

if __name__ == "__main__":
    # Initialize SQLite or PostgreSQL table schemas
    init_db()
    
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=(os.getenv("FLASK_ENV") == "development"))
