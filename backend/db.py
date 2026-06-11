import os
import sqlite3
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta

DB_TYPE = os.getenv("DB_TYPE", "sqlite").lower()
SUPABASE_DB_URL = os.getenv("SUPABASE_DB_URL")

def get_db_connection():
    """Returns a connection to the database (either SQLite or PostgreSQL/Supabase)."""
    if DB_TYPE == "supabase" and SUPABASE_DB_URL:
        # Connect to Supabase PostgreSQL
        conn = psycopg2.connect(SUPABASE_DB_URL)
        return conn
    else:
        # Fallback to local SQLite database
        conn = sqlite3.connect("bookings.db")
        conn.row_factory = sqlite3.Row
        return conn

def init_db():
    """Initializes database tables on startup if they do not exist."""
    conn = get_db_connection()
    try:
        if DB_TYPE == "supabase" and SUPABASE_DB_URL:
            with conn.cursor() as cur:
                # Create bookings table in PostgreSQL
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS bookings (
                        id VARCHAR(255) PRIMARY KEY,
                        name VARCHAR(255) NOT NULL,
                        email VARCHAR(255) NOT NULL,
                        phone VARCHAR(50) NOT NULL,
                        date VARCHAR(50) NOT NULL,
                        time VARCHAR(50) NOT NULL,
                        single_quads INTEGER DEFAULT 0,
                        double_quads INTEGER DEFAULT 0,
                        total_price DECIMAL(10,2) NOT NULL,
                        status VARCHAR(50) DEFAULT 'pending',
                        stripe_session_id VARCHAR(255),
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """)
                # Create index on date/time for performance and availability checks
                cur.execute("CREATE INDEX IF NOT EXISTS idx_bookings_date ON bookings(date);")
            conn.commit()
            print("Supabase/PostgreSQL database initialized successfully.")
        else:
            # Create bookings table in SQLite
            conn.execute("""
                CREATE TABLE IF NOT EXISTS bookings (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    email TEXT NOT NULL,
                    phone TEXT NOT NULL,
                    date TEXT NOT NULL,
                    time TEXT NOT NULL,
                    single_quads INTEGER DEFAULT 0,
                    double_quads INTEGER DEFAULT 0,
                    total_price REAL NOT NULL,
                    status TEXT DEFAULT 'pending',
                    stripe_session_id TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                );
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_bookings_date ON bookings(date);")
            conn.commit()
            print("SQLite local database initialized successfully.")
    except Exception as e:
        print(f"Error initializing database: {e}")
    finally:
        conn.close()

def create_booking(booking_id, name, email, phone, date, time, single_quads, double_quads, total_price, stripe_session_id=None):
    """Inserts a new booking record."""
    conn = get_db_connection()
    try:
        now_str = datetime.now().isoformat()
        if DB_TYPE == "supabase" and SUPABASE_DB_URL:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO bookings (id, name, email, phone, date, time, single_quads, double_quads, total_price, status, stripe_session_id, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'pending', %s, %s)
                """, (booking_id, name, email, phone, date, time, single_quads, double_quads, total_price, stripe_session_id, datetime.now()))
            conn.commit()
        else:
            conn.execute("""
                INSERT INTO bookings (id, name, email, phone, date, time, single_quads, double_quads, total_price, status, stripe_session_id, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?)
            """, (booking_id, name, email, phone, date, time, single_quads, double_quads, total_price, stripe_session_id, now_str))
            conn.commit()
    finally:
        conn.close()

def get_booking_by_stripe_session(session_id):
    """Retrieves a booking record by Stripe session ID."""
    conn = get_db_connection()
    try:
        if DB_TYPE == "supabase" and SUPABASE_DB_URL:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM bookings WHERE stripe_session_id = %s", (session_id,))
                res = cur.fetchone()
                if res:
                    # Convert Decimal to float for JSON compatibility
                    res = dict(res)
                    res["total_price"] = float(res["total_price"])
                    return res
        else:
            cur = conn.cursor()
            cur.execute("SELECT * FROM bookings WHERE stripe_session_id = ?", (session_id,))
            row = cur.fetchone()
            if row:
                return dict(row)
    finally:
        conn.close()
    return None

def confirm_booking(booking_id):
    """Confirms the booking status."""
    conn = get_db_connection()
    try:
        if DB_TYPE == "supabase" and SUPABASE_DB_URL:
            with conn.cursor() as cur:
                cur.execute("UPDATE bookings SET status = 'confirmed' WHERE id = %s", (booking_id,))
            conn.commit()
        else:
            conn.execute("UPDATE bookings SET status = 'confirmed' WHERE id = ?", (booking_id,))
            conn.commit()
    finally:
        conn.close()

def get_active_bookings(date_str):
    """
    Returns bookings on a specific date that are either:
    1. Confirmed
    2. Pending but created in the last 15 minutes (to hold slots during payment checkout)
    """
    conn = get_db_connection()
    bookings_list = []
    try:
        fifteen_minutes_ago = datetime.now() - timedelta(minutes=15)
        
        if DB_TYPE == "supabase" and SUPABASE_DB_URL:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT time, single_quads, double_quads FROM bookings 
                    WHERE date = %s AND (status = 'confirmed' OR (status = 'pending' AND created_at > %s))
                """, (date_str, fifteen_minutes_ago))
                bookings_list = [dict(row) for row in cur.fetchall()]
        else:
            cur = conn.cursor()
            fifteen_mins_ago_str = fifteen_minutes_ago.isoformat()
            cur.execute("""
                SELECT time, single_quads, double_quads FROM bookings 
                WHERE date = ? AND (status = 'confirmed' OR (status = 'pending' AND created_at > ?))
            """, (date_str, fifteen_mins_ago_str))
            bookings_list = [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()
    return bookings_list

def get_slot_availability(date_str, max_capacity=5):
    """
    Calculates remaining quad capacity for standard time slots:
    '13:00' (Afternoon) and '18:00' (Sunset)
    """
    bookings = get_active_bookings(date_str)
    
    # Initialize capacity
    slots = {
        "13:00": max_capacity,
        "18:00": max_capacity
    }
    
    for b in bookings:
        slot_time = b["time"]
        quads_booked = int(b.get("single_quads", 0)) + int(b.get("double_quads", 0))
        if slot_time in slots:
            slots[slot_time] = max(0, slots[slot_time] - quads_booked)
            
    return slots
