import os
import sqlite3
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta
from calendar_sync import get_calendar_events_for_date

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
                
                # Create blocked_slots table in PostgreSQL
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS blocked_slots (
                        id VARCHAR(255) PRIMARY KEY,
                        date VARCHAR(50) NOT NULL,
                        time VARCHAR(50) NOT NULL,
                        quads INTEGER DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """)
                cur.execute("CREATE INDEX IF NOT EXISTS idx_blocked_date ON blocked_slots(date);")
                # Run migration to add quads column if not exists
                try:
                    cur.execute("ALTER TABLE blocked_slots ADD COLUMN IF NOT EXISTS quads INTEGER DEFAULT 0;")
                except Exception as pg_mig_err:
                    print(f"PostgreSQL migration warning (blocked_slots.quads): {pg_mig_err}")
                
                # Create newsletter_subscribers table in PostgreSQL
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS newsletter_subscribers (
                        email VARCHAR(255) PRIMARY KEY,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """)
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
            
            # Create blocked_slots table in SQLite
            conn.execute("""
                CREATE TABLE IF NOT EXISTS blocked_slots (
                    id TEXT PRIMARY KEY,
                    date TEXT NOT NULL,
                    time TEXT NOT NULL,
                    quads INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                );
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_blocked_date ON blocked_slots(date);")
            # Run migration to add quads column in SQLite
            try:
                conn.execute("ALTER TABLE blocked_slots ADD COLUMN quads INTEGER DEFAULT 0;")
            except Exception as sq_mig_err:
                # column might already exist, ignore this error
                pass
            
            # Create newsletter_subscribers table in SQLite
            conn.execute("""
                CREATE TABLE IF NOT EXISTS newsletter_subscribers (
                    email TEXT PRIMARY KEY,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                );
            """)
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

def get_pending_bookings(date_str):
    """
    Returns only pending bookings on a specific date created in the last 15 minutes.
    """
    conn = get_db_connection()
    bookings_list = []
    try:
        fifteen_minutes_ago = datetime.now() - timedelta(minutes=15)
        
        if DB_TYPE == "supabase" and SUPABASE_DB_URL:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT time, single_quads, double_quads FROM bookings 
                    WHERE date = %s AND status = 'pending' AND created_at > %s
                """, (date_str, fifteen_minutes_ago))
                bookings_list = [dict(row) for row in cur.fetchall()]
        else:
            cur = conn.cursor()
            fifteen_mins_ago_str = fifteen_minutes_ago.isoformat()
            cur.execute("""
                SELECT time, single_quads, double_quads FROM bookings 
                WHERE date = ? AND status = 'pending' AND created_at > ?
            """, (date_str, fifteen_mins_ago_str))
            bookings_list = [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()
    return bookings_list

def get_slot_availability(date_str, max_capacity=3):
    """
    Calculates remaining quad capacity for standard time slots:
    '11:00' (Morning) and '18:30' (Sunset)
    Queries Google Calendar if enabled, and combines it with recent pending bookings.
    Falls back to querying the database if Google Calendar is not configured.
    """
    # Try fetching from Google Calendar first
    cal_occupied = get_calendar_events_for_date(date_str)
    
    slots = {
        "11:00": max_capacity,
        "18:30": max_capacity
    }
    
    if cal_occupied is not None:
        # Google Calendar is enabled and returned data
        # We subtract calendar-occupied quads
        for slot_time, quads_booked in cal_occupied.items():
            if slot_time in slots:
                slots[slot_time] = max(0, slots[slot_time] - quads_booked)
                
        # We also count pending database bookings created in the last 15 mins (to prevent double bookings during checkout)
        pending_bookings = get_pending_bookings(date_str)
        for b in pending_bookings:
            slot_time = b["time"]
            quads_booked = int(b.get("single_quads", 0)) + int(b.get("double_quads", 0))
            if slot_time in slots:
                slots[slot_time] = max(0, slots[slot_time] - quads_booked)
    else:
        # Fallback to local database (confirmed + pending bookings)
        bookings = get_active_bookings(date_str)
        for b in bookings:
            slot_time = b["time"]
            quads_booked = int(b.get("single_quads", 0)) + int(b.get("double_quads", 0))
            if slot_time in slots:
                slots[slot_time] = max(0, slots[slot_time] - quads_booked)
                
    # Apply admin blocked slots
    try:
        blocked = get_blocked_slots_by_date(date_str)
        for b in blocked:
            b_time = b["time"]
            b_quads = b.get("quads", 0)
            
            # If b_quads is 0 or None, it means a full block (0 capacity)
            if b_quads == 0 or b_quads is None:
                if b_time == "all":
                    slots["11:00"] = 0
                    slots["18:30"] = 0
                elif b_time in slots:
                    slots[b_time] = 0
            else:
                # Partial block: subtract b_quads from capacity
                if b_time == "all":
                    slots["11:00"] = max(0, slots["11:00"] - b_quads)
                    slots["18:30"] = max(0, slots["18:30"] - b_quads)
                elif b_time in slots:
                    slots[b_time] = max(0, slots[b_time] - b_quads)
    except Exception as e:
        print(f"Error applying blocked slots: {e}")
        
    # Apply cut-off time rules (Tenerife time)
    # - 11:00 slot: min 4h preparation time -> cut-off at 07:00
    # - 18:30 slot: min 2h preparation time -> cut-off at 16:30
    try:
        import pytz
        tz = pytz.timezone('Atlantic/Canary')
        now_in_tz = datetime.now(tz)
        slot_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        current_date = now_in_tz.date()
        
        if slot_date < current_date:
            slots["11:00"] = 0
            slots["18:30"] = 0
        elif slot_date == current_date:
            # 11:00 tour: cut-off is 07:00
            cutoff_11 = now_in_tz.replace(hour=7, minute=0, second=0, microsecond=0)
            if now_in_tz >= cutoff_11:
                slots["11:00"] = 0
            # 18:30 tour: cut-off is 16:30
            cutoff_18 = now_in_tz.replace(hour=16, minute=30, second=0, microsecond=0)
            if now_in_tz >= cutoff_18:
                slots["18:30"] = 0
    except Exception as e:
        print(f"Error applying cut-off times: {e}")
        
    return slots
 
def block_slot(date_str, time_str, quads=0):
    """Blocks a slot (time_str can be '11:00', '18:30', or 'all') for a given date with specified quads."""
    import uuid
    conn = get_db_connection()
    try:
        block_id = str(uuid.uuid4())
        if DB_TYPE == "supabase" and SUPABASE_DB_URL:
            with conn.cursor() as cur:
                # First check if block already exists
                cur.execute("SELECT id FROM blocked_slots WHERE date = %s AND time = %s", (date_str, time_str))
                row = cur.fetchone()
                if row:
                    # Update existing block's quads
                    cur.execute("UPDATE blocked_slots SET quads = %s WHERE date = %s AND time = %s", (quads, date_str, time_str))
                    conn.commit()
                    return True
                cur.execute("""
                    INSERT INTO blocked_slots (id, date, time, quads)
                    VALUES (%s, %s, %s, %s)
                """, (block_id, date_str, time_str, quads))
            conn.commit()
        else:
            cur = conn.cursor()
            cur.execute("SELECT id FROM blocked_slots WHERE date = ? AND time = ?", (date_str, time_str))
            row = cur.fetchone()
            if row:
                # Update existing block's quads
                conn.execute("UPDATE blocked_slots SET quads = ? WHERE date = ? AND time = ?", (quads, date_str, time_str))
                conn.commit()
                return True
            conn.execute("""
                INSERT INTO blocked_slots (id, date, time, quads)
                VALUES (?, ?, ?, ?)
            """, (block_id, date_str, time_str, quads))
            conn.commit()
        return True
    finally:
        conn.close()

def unblock_slot(block_id):
    """Unblocks a previously blocked slot."""
    conn = get_db_connection()
    try:
        if DB_TYPE == "supabase" and SUPABASE_DB_URL:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM blocked_slots WHERE id = %s", (block_id,))
            conn.commit()
        else:
            conn.execute("DELETE FROM blocked_slots WHERE id = ?", (block_id,))
            conn.commit()
        return True
    finally:
        conn.close()

def get_blocked_slots_by_date(date_str):
    """Returns a list of blocked slots (dictionaries with time and quads) for a given date."""
    conn = get_db_connection()
    blocked_slots = []
    try:
        if DB_TYPE == "supabase" and SUPABASE_DB_URL:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT time, quads FROM blocked_slots WHERE date = %s", (date_str,))
                blocked_slots = [dict(row) for row in cur.fetchall()]
        else:
            cur = conn.cursor()
            cur.execute("SELECT time, quads FROM blocked_slots WHERE date = ?", (date_str,))
            blocked_slots = [{"time": row[0], "quads": row[1]} for row in cur.fetchall()]
    finally:
        conn.close()
    return blocked_slots

def get_all_blocked_slots():
    """Returns all blocked slots in the database, ordered by date ascending."""
    conn = get_db_connection()
    blocked_list = []
    try:
        if DB_TYPE == "supabase" and SUPABASE_DB_URL:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT id, date, time, quads FROM blocked_slots ORDER BY date ASC, time ASC")
                blocked_list = [dict(row) for row in cur.fetchall()]
        else:
            cur = conn.cursor()
            cur.execute("SELECT id, date, time, quads FROM blocked_slots ORDER BY date ASC, time ASC")
            blocked_list = [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()
    return blocked_list

def get_all_bookings():
    """Returns all bookings in the database, ordered by creation date descending."""
    conn = get_db_connection()
    bookings_list = []
    try:
        if DB_TYPE == "supabase" and SUPABASE_DB_URL:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT id, name, email, phone, date, time, single_quads, double_quads, total_price, status, stripe_session_id, created_at FROM bookings ORDER BY created_at DESC")
                for row in cur.fetchall():
                    d_row = dict(row)
                    d_row["total_price"] = float(d_row["total_price"])
                    # Convert datetime to string if needed
                    if d_row.get("created_at"):
                        d_row["created_at"] = d_row["created_at"].isoformat()
                    bookings_list.append(d_row)
        else:
            cur = conn.cursor()
            cur.execute("SELECT id, name, email, phone, date, time, single_quads, double_quads, total_price, status, stripe_session_id, created_at FROM bookings ORDER BY created_at DESC")
            bookings_list = [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()
    return bookings_list

def manually_confirm_booking(booking_id):
    """Manually confirms a booking and returns the booking dictionary for email/calendar sync."""
    conn = get_db_connection()
    booking = None
    try:
        if DB_TYPE == "supabase" and SUPABASE_DB_URL:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("UPDATE bookings SET status = 'confirmed' WHERE id = %s", (booking_id,))
                cur.execute("SELECT * FROM bookings WHERE id = %s", (booking_id,))
                res = cur.fetchone()
                if res:
                    booking = dict(res)
                    booking["total_price"] = float(booking["total_price"])
                    if booking.get("created_at"):
                        booking["created_at"] = booking["created_at"].isoformat()
            conn.commit()
        else:
            conn.execute("UPDATE bookings SET status = 'confirmed' WHERE id = ?", (booking_id,))
            cur = conn.cursor()
            cur.execute("SELECT * FROM bookings WHERE id = ?", (booking_id,))
            row = cur.fetchone()
            if row:
                booking = dict(row)
            conn.commit()
    finally:
        conn.close()
    return booking

def cancel_booking(booking_id):
    """Cancels a booking by setting its status to 'cancelled' and returns the updated booking dictionary."""
    conn = get_db_connection()
    booking = None
    try:
        if DB_TYPE == "supabase" and SUPABASE_DB_URL:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("UPDATE bookings SET status = 'cancelled' WHERE id = %s", (booking_id,))
                cur.execute("SELECT * FROM bookings WHERE id = %s", (booking_id,))
                res = cur.fetchone()
                if res:
                    booking = dict(res)
                    booking["total_price"] = float(booking["total_price"])
                    if booking.get("created_at"):
                        booking["created_at"] = booking["created_at"].isoformat()
            conn.commit()
        else:
            conn.execute("UPDATE bookings SET status = 'cancelled' WHERE id = ?", (booking_id,))
            cur = conn.cursor()
            cur.execute("SELECT * FROM bookings WHERE id = ?", (booking_id,))
            row = cur.fetchone()
            if row:
                booking = dict(row)
            conn.commit()
    finally:
        conn.close()
    return booking

def subscribe_newsletter(email):
    """Subscribes an email to the newsletter, ignoring duplicates."""
    conn = get_db_connection()
    try:
        now_str = datetime.now().isoformat()
        if DB_TYPE == "supabase" and SUPABASE_DB_URL:
            with conn.cursor() as cur:
                # PostgreSQL support for ON CONFLICT DO NOTHING
                cur.execute("""
                    INSERT INTO newsletter_subscribers (email, created_at)
                    VALUES (%s, %s)
                    ON CONFLICT (email) DO NOTHING
                """, (email, datetime.now()))
            conn.commit()
        else:
            # SQLite support for INSERT OR IGNORE
            conn.execute("""
                INSERT OR IGNORE INTO newsletter_subscribers (email, created_at)
                VALUES (?, ?)
            """, (email, now_str))
            conn.commit()
        return True
    except Exception as e:
        print(f"Error subscribing to newsletter: {e}")
        return False
    finally:
        conn.close()

