import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'retailvision.db')

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Users Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL
    )
    ''')
    
    # 2. Customers Table (Tracks unique tracked customers)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS customers (
        id INTEGER PRIMARY KEY, -- Custom ID matching YOLO/ByteTrack persistent ID
        entry_time TEXT NOT NULL,
        exit_time TEXT,
        total_time INTEGER DEFAULT 0 -- in seconds
    )
    ''')
    
    # 3. Movement Table (Tracks spatial data of customers)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS movement (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id INTEGER,
        x INTEGER,
        y INTEGER,
        timestamp TEXT NOT NULL,
        zone TEXT,
        FOREIGN KEY(customer_id) REFERENCES customers(id)
    )
    ''')
    
    # 4. Zones Table (Stores zone bounding box configs in 1280x720 normalized coords)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS zones (
        name TEXT PRIMARY KEY,
        x1 INTEGER,
        y1 INTEGER,
        x2 INTEGER,
        y2 INTEGER
    )
    ''')
    
    # Insert default users if they don't exist
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", ('admin', 'admin123', 'admin'))
        cursor.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", ('manager', 'manager123', 'manager'))
    
    # Insert default zones
    # Assuming video resolution is 1280x720
    default_zones = [
        ('Entrance', 0, 500, 250, 720),
        ('Vegetables', 100, 100, 450, 400),
        ('Snacks', 550, 100, 900, 400),
        ('Beverages', 950, 100, 1280, 500),
        ('Billing', 950, 500, 1280, 720)
    ]
    
    for zone in default_zones:
        cursor.execute('''
        INSERT OR REPLACE INTO zones (name, x1, y1, x2, y2)
        VALUES (?, ?, ?, ?, ?)
        ''', zone)
        
    conn.commit()
    conn.close()
    print("Database initialized successfully.")

# --- Authentication ---
def authenticate_user(username, password):
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE username = ? AND password = ?', (username, password)).fetchone()
    conn.close()
    return user

# --- Tracking Queries ---
def start_customer_track(customer_id, entry_time=None):
    if entry_time is None:
        entry_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    conn = get_db_connection()
    try:
        conn.execute('''
        INSERT OR IGNORE INTO customers (id, entry_time)
        VALUES (?, ?)
        ''', (customer_id, entry_time))
        conn.commit()
    except sqlite3.Error as e:
        print(f"DB Error starting track for ID {customer_id}: {e}")
    finally:
        conn.close()

def log_customer_movement(customer_id, x, y, timestamp=None, zone=None):
    if timestamp is None:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    conn = get_db_connection()
    try:
        # Determine zone if not provided
        if zone is None:
            zone = get_zone_for_coordinates(x, y, conn)
            
        conn.execute('''
        INSERT INTO movement (customer_id, x, y, timestamp, zone)
        VALUES (?, ?, ?, ?, ?)
        ''', (customer_id, x, y, timestamp, zone))
        conn.commit()
    except sqlite3.Error as e:
        print(f"DB Error logging movement for ID {customer_id}: {e}")
    finally:
        conn.close()

def end_customer_track(customer_id, exit_time=None):
    if exit_time is None:
        exit_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    conn = get_db_connection()
    try:
        row = conn.execute('SELECT entry_time FROM customers WHERE id = ?', (customer_id,)).fetchone()
        if row:
            entry_time_str = row['entry_time']
            entry_time = datetime.strptime(entry_time_str, '%Y-%m-%d %H:%M:%S')
            exit_datetime = datetime.strptime(exit_time, '%Y-%m-%d %H:%M:%S')
            duration = int((exit_datetime - entry_time).total_seconds())
            
            conn.execute('''
            UPDATE customers
            SET exit_time = ?, total_time = ?
            WHERE id = ?
            ''', (exit_time, duration, customer_id))
            conn.commit()
    except sqlite3.Error as e:
        print(f"DB Error ending track for ID {customer_id}: {e}")
    finally:
        conn.close()

def get_zone_for_coordinates(x, y, conn=None):
    close_conn = False
    if conn is None:
        conn = get_db_connection()
        close_conn = True
        
    zones = conn.execute('SELECT * FROM zones').fetchall()
    
    if close_conn:
        conn.close()
        
    for zone in zones:
        if zone['x1'] <= x <= zone['x2'] and zone['y1'] <= y <= zone['y2']:
            return zone['name']
            
    return 'General Aisle'

# --- Dashboard & Analytics Queries ---
def get_total_visitors_count():
    conn = get_db_connection()
    count = conn.execute('SELECT COUNT(*) FROM customers').fetchone()[0]
    conn.close()
    return count

def get_current_visitors_count(active_seconds_threshold=10):
    conn = get_db_connection()
    count = conn.execute('SELECT COUNT(*) FROM customers WHERE exit_time IS NULL').fetchone()[0]
    conn.close()
    return count

def get_average_stay_time():
    conn = get_db_connection()
    avg_time = conn.execute('SELECT AVG(total_time) FROM customers WHERE total_time > 0').fetchone()[0]
    conn.close()
    return round(avg_time, 1) if avg_time else 0.0

def get_zone_visits_and_dwell():
    conn = get_db_connection()
    query = '''
    SELECT 
        zone, 
        COUNT(DISTINCT customer_id) as visits,
        COALESCE(AVG(dwell_seconds), 0) as avg_dwell
    FROM (
        SELECT 
            customer_id, 
            zone, 
            (strftime('%s', MAX(timestamp)) - strftime('%s', MIN(timestamp))) as dwell_seconds
        FROM movement
        WHERE zone != 'General Aisle'
        GROUP BY customer_id, zone
    )
    GROUP BY zone
    '''
    try:
        rows = conn.execute(query).fetchall()
        data = {r['zone']: {'visits': r['visits'], 'avg_dwell': round(r['avg_dwell'], 1)} for r in rows}
    except Exception as e:
        print(f"Error executing dwell query: {e}")
        rows = conn.execute('SELECT zone, COUNT(DISTINCT customer_id) as visits FROM movement GROUP BY zone').fetchall()
        data = {r['zone']: {'visits': r['visits'], 'avg_dwell': 15.0} for r in rows}
    conn.close()
    return data

def get_hourly_visitor_counts():
    conn = get_db_connection()
    query = '''
    SELECT strftime('%H', entry_time) as hour, COUNT(*) as count
    FROM customers
    GROUP BY hour
    ORDER BY hour
    '''
    rows = conn.execute(query).fetchall()
    conn.close()
    
    counts = {f"{h:02d}:00": 0 for h in range(24)}
    for r in rows:
        if r['hour']:
            counts[f"{int(r['hour']):02d}:00"] = r['count']
    return counts

def get_recent_movements(limit=1000):
    conn = get_db_connection()
    rows = conn.execute('SELECT customer_id, x, y, zone, timestamp FROM movement ORDER BY id DESC LIMIT ?', (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def clear_data():
    conn = get_db_connection()
    conn.execute('DELETE FROM movement')
    conn.execute('DELETE FROM customers')
    conn.commit()
    conn.close()

if __name__ == '__main__':
    init_db()