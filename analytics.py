import random
from datetime import datetime, timedelta
from database import (
    get_db_connection, 
    get_total_visitors_count, 
    get_current_visitors_count, 
    get_average_stay_time, 
    get_zone_visits_and_dwell, 
    get_hourly_visitor_counts
)

def get_analytics_summary():
    total_visitors = get_total_visitors_count()
    current_visitors = get_current_visitors_count()
    avg_stay = get_average_stay_time()
    
    hourly_data = get_hourly_visitor_counts()
    peak_hour = "N/A"
    max_count = -1
    for hr, count in hourly_data.items():
        if count > max_count:
            max_count = count
            peak_hour = hr
            
    zone_data = get_zone_visits_and_dwell()
    
    most_visited_zone = "N/A"
    max_visits = -1
    for zone, stats in zone_data.items():
        if stats['visits'] > max_visits:
            max_visits = stats['visits']
            most_visited_zone = zone
            
    return {
        "total_visitors": total_visitors,
        "current_visitors": current_visitors,
        "average_stay_time": f"{avg_stay}s",
        "peak_hour": f"{peak_hour} ({max_count} visits)" if max_count > 0 else "N/A",
        "most_visited_zone": most_visited_zone,
        "hourly_chart": hourly_data,
        "zone_chart": zone_data
    }

def populate_historical_mock_data():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM customers")
    if cursor.fetchone()[0] > 10:
        print("Historical data already exists, skipping generation.")
        conn.close()
        return
        
    print("Populating database with rich historical data...")
    
    zones = {
        'Entrance': (120, 610),
        'Vegetables': (270, 250),
        'Snacks': (720, 250),
        'Beverages': (1110, 300),
        'Billing': (1110, 610)
    }
    
    start_time = datetime.now() - timedelta(days=1)
    
    for customer_id in range(1, 120):
        hour_prob = random.random()
        if hour_prob < 0.35:
            entry_hour = random.randint(17, 20)
        elif hour_prob < 0.6:
            entry_hour = random.randint(12, 14)
        elif hour_prob < 0.9:
            entry_hour = random.randint(9, 16)
        else:
            entry_hour = random.choice([8, 21, 22])
            
        entry_datetime = start_time.replace(hour=entry_hour, minute=random.randint(0, 59), second=random.randint(0, 59))
        
        selected_zones = ['Entrance']
        options = ['Vegetables', 'Snacks', 'Beverages']
        random.shuffle(options)
        selected_zones.extend(options[:random.randint(1, 3)])
        selected_zones.append('Billing')
        
        current_time = entry_datetime
        cursor.execute("INSERT OR REPLACE INTO customers (id, entry_time) VALUES (?, ?)", 
                       (customer_id, current_time.strftime('%Y-%m-%d %H:%M:%S')))
        
        for zone in selected_zones:
            center_x, center_y = zones[zone]
            dwell_pts = random.randint(3, 10)
            
            for _ in range(dwell_pts):
                offset_x = random.randint(-50, 50)
                offset_y = random.randint(-50, 50)
                x = max(0, min(1280, center_x + offset_x))
                y = max(0, min(720, center_y + offset_y))
                
                current_time += timedelta(seconds=random.randint(5, 20))
                cursor.execute(
                    "INSERT INTO movement (customer_id, x, y, timestamp, zone) VALUES (?, ?, ?, ?, ?)",
                    (customer_id, x, y, current_time.strftime('%Y-%m-%d %H:%M:%S'), zone)
                )
                
        exit_time = current_time.strftime('%Y-%m-%d %H:%M:%S')
        total_seconds = int((current_time - entry_datetime).total_seconds())
        cursor.execute(
            "UPDATE customers SET exit_time = ?, total_time = ? WHERE id = ?",
            (exit_time, total_seconds, customer_id)
        )
        
    conn.commit()
    conn.close()
    print("Mock database generation complete.")

if __name__ == '__main__':
    from database import init_db
    init_db()
    populate_historical_mock_data()