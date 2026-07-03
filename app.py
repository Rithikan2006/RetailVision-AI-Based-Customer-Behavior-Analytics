import cv2
import numpy as np
import time
import os
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, Response, send_file
from database import init_db, authenticate_user, clear_data
from tracker import RetailTracker
from analytics import get_analytics_summary, populate_historical_mock_data
from heatmap import generate_heatmap
from report import generate_pdf_report

app = Flask(__name__)
app.secret_key = 'retailvision_super_secret_session_key'

current_source = 'simulated'
tracker = RetailTracker(use_yolo=False)
init_db()
populate_historical_mock_data()
generate_heatmap()

@app.route('/')
def index():
    if 'username' in session:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/login', methods=['POST'])
def login():
    username = request.form.get('username')
    password = request.form.get('password')
    user = authenticate_user(username, password)
    if user:
        session['username'] = user['username']
        session['role'] = user['role']
        return redirect(url_for('dashboard'))
    return render_template('index.html', error="Invalid username or password.")

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        return redirect(url_for('index'))
    return render_template('dashboard.html', source=current_source)

@app.route('/api/analytics')
def api_analytics():
    if 'username' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    summary = get_analytics_summary()
    summary['alerts'] = tracker.alerts
    return jsonify(summary)

@app.route('/api/change_source')
def api_change_source():
    if 'username' not in session:
        return jsonify({"error": "Unauthorized"}), 401
        
    global current_source, tracker
    source = request.args.get('source', 'simulated')
    
    if source != current_source:
        current_source = source
        use_yolo = (source == '0')
        tracker = RetailTracker(use_yolo=use_yolo)
        print(f"Server changed tracking source to: {source}")
        
    return jsonify({"status": "success", "source": current_source})

@app.route('/api/refresh_heatmap')
def api_refresh_heatmap():
    if 'username' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    generate_heatmap()
    return jsonify({"status": "success"})

@app.route('/api/clear_db', methods=['POST'])
def api_clear_db():
    if 'username' not in session or session.get('role') != 'admin':
        return jsonify({"error": "Unauthorized"}), 401
        
    clear_data()
    tracker.alerts = []
    tracker.active_tracks = {}
    tracker.shelf_dwell_start = {}
    generate_heatmap()
    return jsonify({"status": "success"})

def gen_frames():
    global current_source, tracker
    local_source = current_source
    
    if local_source == 'simulated':
        cap = None
        width, height, fps = 1280, 720, 30
    else:
        src = int(local_source) if local_source.isdigit() else local_source
        cap = cv2.VideoCapture(src)
        if not cap.isOpened():
            print(f"Error: Could not open camera source {src}. Falling back to simulation.")
            cap = None
            local_source = 'simulated'
            current_source = 'simulated'
            width, height, fps = 1280, 720, 30
        else:
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = int(cap.get(cv2.CAP_PROP_FPS))
            if fps <= 0:
                fps = 30

    frame_delay = 1.0 / fps

    try:
        while True:
            if local_source != current_source:
                break
                
            if local_source == 'simulated':
                frame = np.ones((height, width, 3), dtype=np.uint8) * 35
                cv2.rectangle(frame, (400, 100), (500, 600), (55, 55, 55), -1)
                cv2.rectangle(frame, (400, 100), (500, 600), (80, 80, 80), 1)
                cv2.putText(frame, "SHELF A", (415, 350), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (140, 140, 140), 1)
                
                cv2.rectangle(frame, (750, 100), (850, 600), (55, 55, 55), -1)
                cv2.rectangle(frame, (750, 100), (850, 600), (80, 80, 80), 1)
                cv2.putText(frame, "SHELF B", (765, 350), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (140, 140, 140), 1)
                time.sleep(frame_delay)
            else:
                ret, frame = cap.read()
                if not ret:
                    if not isinstance(src, int):
                        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                        continue
                    else:
                        break

            processed = tracker.process_frame(frame)
            ret, buffer = cv2.imencode('.jpg', processed)
            if not ret:
                continue
                
            frame_bytes = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
    finally:
        if cap is not None:
            cap.release()
            print("Released camera stream connection.")

@app.route('/video_feed')
def video_feed():
    if 'username' not in session:
        return redirect(url_for('index'))
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/download_report')
def download_report():
    if 'username' not in session:
        return redirect(url_for('index'))
    generate_heatmap()
    report_path = generate_pdf_report(filename="daily_analytics_report.pdf")
    return send_file(report_path, as_attachment=True)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)