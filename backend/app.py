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
from email_sender import send_booking_emails
from calendar_sync import sync_to_google_calendar

app = Flask(__name__)

# Configure CORS
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5500")
CORS(app, resources={r"/api/*": {"origins": "*"}})

# Simple in-memory rate limiting to protect endpoints against abuse
IP_REQUESTS = {}
RATE_LIMIT_MAX = 60  # Max 60 requests per minute
RATE_LIMIT_WINDOW = 60  # 60 seconds

@app.before_request
def rate_limiter():
    """Applies a simple rate limiter per client IP address."""
    import time
    ip = request.remote_addr
    now = time.time()
    
    # Clean up old records
    if ip in IP_REQUESTS:
        timestamps = [t for t in IP_REQUESTS[ip] if now - t < RATE_LIMIT_WINDOW]
        IP_REQUESTS[ip] = timestamps
    else:
        IP_REQUESTS[ip] = []
        
    if len(IP_REQUESTS[ip]) >= RATE_LIMIT_MAX:
        return jsonify({"error": "Too many requests. Please try again later."}), 429
        
    # Exclude stripe webhooks from rate limiting
    if request.path != "/api/webhook":
        IP_REQUESTS[ip].append(now)

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
    single_quads = int(data.get("single_quads", 0))
    double_quads = int(data.get("double_quads", 0))
    
    if not all([name, email, phone, date_str, time_str]):
        return jsonify({"error": "Missing required fields"}), 400
        
    if single_quads <= 0 and double_quads <= 0:
        return jsonify({"error": "Must select at least 1 quad bike"}), 400
        
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
            
        # Prices: Single = €1, Double = €1 (TEMPORARY FOR TESTING)
        total_price = (single_quads * 1) + (double_quads * 1)
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
                    'unit_amount': 100, # €1.00
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
                    'unit_amount': 100, # €1.00
                },
                'quantity': double_quads,
            })
            
        # Create Stripe Session
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=line_items,
            mode='payment',
            customer_email=email,
            success_url=f"{FRONTEND_URL}/success.html?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{FRONTEND_URL}/cancel.html",
            metadata={
                "booking_id": booking_id
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
