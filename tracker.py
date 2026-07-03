import cv2
import numpy as np
import time
import random
from datetime import datetime
from database import (
    start_customer_track, 
    log_customer_movement, 
    end_customer_track, 
    get_zone_for_coordinates,
    get_db_connection
)

class RetailTracker:
    def __init__(self, use_yolo=False, model_path="yolov8n.pt"):
        self.use_yolo = use_yolo
        self.model = None
        self.active_tracks = {}  # ID -> last_seen_timestamp
        self.shelf_dwell_start = {} # (customer_id, zone) -> start_time
        self.alerts = []
        
        if self.use_yolo:
            try:
                from ultralytics import YOLO
                self.model = YOLO(model_path)
                print("YOLOv8 initialized for tracking.")
            except ImportError:
                print("Ultralytics not installed. Falling back to Demo Mode.")
                self.use_yolo = False

        self.simulated_customers = []
        self.next_customer_id = 1
        self.zones = {
            'Entrance': (0, 500, 250, 720),
            'Vegetables': (100, 100, 450, 400),
            'Snacks': (550, 100, 900, 400),
            'Beverages': (950, 100, 1280, 500),
            'Billing': (950, 500, 1280, 720)
        }
        
    def add_alert(self, message):
        timestamp = datetime.now().strftime('%H:%M:%S')
        self.alerts.append({"time": timestamp, "message": message})
        if len(self.alerts) > 10:
            self.alerts.pop(0)

    def process_frame(self, frame):
        h, w, _ = frame.shape
        
        # Draw Zones
        for zone_name, coords in self.zones.items():
            x1, y1, x2, y2 = coords
            overlay = frame.copy()
            color = (50, 200, 50) if zone_name != 'Billing' else (50, 50, 200)
            cv2.rectangle(overlay, (x1, y1), (x2, y2), color, -1)
            cv2.addWeighted(overlay, 0.15, frame, 0.85, 0, frame)
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            cv2.putText(frame, zone_name, (x1 + 10, y1 + 30), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2, cv2.LINE_AA)
            
        current_time_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        current_epoch = time.time()
        
        detected_people = []
        
        if self.use_yolo and self.model is not None:
            results = self.model.track(frame, persist=True, tracker="bytetrack.yaml", verbose=False)
            if results and results[0].boxes is not None:
                boxes = results[0].boxes
                for box in boxes:
                    cls_id = int(box.cls[0].item()) if box.cls is not None else -1
                    if cls_id == 0:  # Person class
                        x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                        track_id = int(box.id[0].item()) if box.id is not None else None
                        if track_id is not None:
                            cx = int((x1 + x2) / 2)
                            cy = int((y1 + y2) / 2)
                            detected_people.append((track_id, cx, cy, (x1, y1, x2, y2)))
        else:
            self._update_simulation()
            for cust in self.simulated_customers:
                cx, cy = int(cust['x']), int(cust['y'])
                bx1, by1 = max(0, cx - 30), max(0, cy - 80)
                bx2, by2 = min(w, cx + 30), min(h, cy + 20)
                detected_people.append((cust['id'], cx, cy, (bx1, by1, bx2, by2)))
                
        active_ids = set()
        zone_counts = {z: 0 for z in self.zones.keys()}
        zone_counts['General Aisle'] = 0
        
        for pid, cx, cy, bbox in detected_people:
            active_ids.add(pid)
            x1, y1, x2, y2 = bbox
            zone = get_zone_for_coordinates(cx, cy)
            zone_counts[zone] = zone_counts.get(zone, 0) + 1
            
            if pid not in self.active_tracks:
                start_customer_track(pid, current_time_str)
                self.active_tracks[pid] = current_epoch
                self.add_alert(f"Customer #{pid} entered the store.")
            
            log_customer_movement(pid, cx, cy, current_time_str, zone)
            
            # Shelf Dwell Time Interest
            if zone in ['Vegetables', 'Snacks', 'Beverages']:
                key = (pid, zone)
                if key not in self.shelf_dwell_start:
                    self.shelf_dwell_start[key] = current_epoch
                else:
                    dwell_duration = current_epoch - self.shelf_dwell_start[key]
                    if dwell_duration >= 20.0 and not self.shelf_dwell_start.get((pid, zone, 'alerted'), False):
                        self.add_alert(f"Customer #{pid} shows high interest in {zone} (Stayed > 20s).")
                        self.shelf_dwell_start[(pid, zone, 'alerted')] = True
            else:
                for key in list(self.shelf_dwell_start.keys()):
                    if key[0] == pid and key[1] != zone:
                        self.shelf_dwell_start.pop(key, None)

            color = (0, 165, 255)
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            label = f"ID: {pid} | {zone}"
            cv2.putText(frame, label, (x1, y1 - 10), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2, cv2.LINE_AA)
            cv2.circle(frame, (cx, cy), 4, (0, 0, 255), -1)

        # Inactive tracks timeout
        timeout = 3.0
        for pid in list(self.active_tracks.keys()):
            if pid not in active_ids:
                if current_epoch - self.active_tracks[pid] > timeout:
                    end_customer_track(pid, current_time_str)
                    self.active_tracks.pop(pid)
                    for key in list(self.shelf_dwell_start.keys()):
                        if key[0] == pid:
                            self.shelf_dwell_start.pop(key, None)
                    self.add_alert(f"Customer #{pid} exited the store.")
            else:
                self.active_tracks[pid] = current_epoch

        # Alerts
        billing_count = zone_counts.get('Billing', 0)
        if billing_count >= 10:
            self.add_alert(f"ALERT: Billing Queue is congested! {billing_count} customers in queue.")

        total_active = len(active_ids)
        if total_active >= 30:
            self.add_alert(f"ALERT: Crowd capacity exceeded! {total_active} customers inside.")

        # Overlay statistics
        cv2.rectangle(frame, (10, 10), (320, 130), (0, 0, 0), -1)
        cv2.putText(frame, f"Total Customers: {total_active}", (20, 40), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1, cv2.LINE_AA)
        cv2.putText(frame, f"Billing Queue: {billing_count}", (20, 70), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255) if billing_count >= 10 else (255, 255, 255), 1, cv2.LINE_AA)
        cv2.putText(frame, f"Vegetables: {zone_counts.get('Vegetables', 0)}", (20, 100), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
        cv2.putText(frame, f"Snacks/Beverages: {zone_counts.get('Snacks', 0) + zone_counts.get('Beverages', 0)}", (20, 120), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)

        return frame

    def _update_simulation(self):
        if len(self.simulated_customers) < 8 and random.random() < 0.05:
            ex1, ey1, ex2, ey2 = self.zones['Entrance']
            start_x = random.randint(ex1, ex2)
            start_y = random.randint(ey1, ey2)
            
            path = ['Entrance']
            shopping_spots = ['Vegetables', 'Snacks', 'Beverages']
            random.shuffle(shopping_spots)
            path.extend(shopping_spots[:random.randint(1, 3)])
            path.append('Billing')
            path.append('Exit')
            
            self.simulated_customers.append({
                'id': self.next_customer_id,
                'x': float(start_x),
                'y': float(start_y),
                'path': path,
                'target_zone_index': 1,
                'state': 'moving',
                'state_timer': 0,
                'speed': random.uniform(2.5, 4.5),
                'target_x': None,
                'target_y': None
            })
            self.next_customer_id += 1

        for cust in list(self.simulated_customers):
            target_zone = cust['path'][cust['target_zone_index']]
            if target_zone == 'Exit':
                target_x, target_y = -50, 600
            else:
                if cust['target_x'] is None or cust['target_y'] is None:
                    zx1, zy1, zx2, zy2 = self.zones[target_zone]
                    cust['target_x'] = float(random.randint(zx1 + 20, zx2 - 20))
                    cust['target_y'] = float(random.randint(zy1 + 20, zy2 - 20))
                target_x, target_y = cust['target_x'], cust['target_y']

            dx = target_x - cust['x']
            dy = target_y - cust['y']
            dist = np.hypot(dx, dy)
            
            if dist > 5:
                cust['x'] += (dx / dist) * cust['speed']
                cust['y'] += (dy / dist) * cust['speed']
            else:
                if target_zone == 'Exit':
                    self.simulated_customers.remove(cust)
                    continue
                
                if cust['state'] == 'moving':
                    cust['state'] = 'shopping'
                    cust['state_timer'] = random.randint(120, 250) if target_zone == 'Billing' else random.randint(60, 150)
                else:
                    cust['state_timer'] -= 1
                    if cust['state_timer'] <= 0:
                        cust['target_zone_index'] += 1
                        cust['state'] = 'moving'
                        cust['target_x'] = None
                        cust['target_y'] = None