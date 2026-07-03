import cv2
import argparse
import os
import sys
import numpy as np
import time
from tracker import RetailTracker
from database import init_db, clear_data
from heatmap import generate_heatmap

def run_detection(source_path, use_yolo=False, output_path=None, reset_db=True):
    init_db()
    if reset_db:
        clear_data()
        print("Database cleared for a fresh run.")

    tracker = RetailTracker(use_yolo=use_yolo)
    
    is_webcam = False
    if source_path.isdigit():
        cap = cv2.VideoCapture(int(source_path))
        is_webcam = True
        print(f"Reading from Webcam {source_path}...")
    else:
        if not os.path.exists(source_path) and not use_yolo:
            print(f"Video file '{source_path}' not found. Spawning simulated store feed...")
            is_webcam = False
        else:
            cap = cv2.VideoCapture(source_path)
            if not cap.isOpened():
                print(f"Error: Could not open video file {source_path}")
                sys.exit(1)
            print(f"Reading from video file '{source_path}'...")
            is_webcam = False

    if source_path.isdigit() or (isinstance(source_path, str) and os.path.exists(source_path)):
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = int(cap.get(cv2.CAP_PROP_FPS))
        if fps <= 0:
            fps = 30
    else:
        width, height, fps = 1280, 720, 30

    writer = None
    if output_path:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
        print(f"Saving output video to '{output_path}'...")

    frame_count = 0
    try:
        while True:
            if source_path.isdigit() or (isinstance(source_path, str) and os.path.exists(source_path)):
                ret, frame = cap.read()
                if not ret:
                    break
            else:
                frame = np.ones((height, width, 3), dtype=np.uint8) * 45
                cv2.rectangle(frame, (400, 100), (500, 600), (80, 80, 80), -1)
                cv2.rectangle(frame, (750, 100), (850, 600), (80, 80, 80), -1)
                cv2.putText(frame, "SHELF A", (410, 350), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (180, 180, 180), 2)
                cv2.putText(frame, "SHELF B", (760, 350), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (180, 180, 180), 2)
                time.sleep(1.0 / fps)
                
            frame_count += 1
            processed_frame = tracker.process_frame(frame)
            if writer:
                writer.write(processed_frame)
                
            if frame_count % 100 == 0:
                print(f"Processed {frame_count} frames. Active tracks: {len(tracker.active_tracks)}")
                
            if not (source_path.isdigit() or (isinstance(source_path, str) and os.path.exists(source_path))) and frame_count >= 600:
                print("Simulation run finished.")
                break
    except KeyboardInterrupt:
        print("Interrupted by user.")
    finally:
        if 'cap' in locals() and cap.isOpened():
            cap.release()
        if writer:
            writer.release()
        cv2.destroyAllWindows()
        print("Releasing camera and writers.")
        print("Generating final traffic heatmap...")
        generate_heatmap()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="RetailVision Customer Behavior Detection & Tracking")
    parser.add_argument('--source', type=str, default='simulated', help="Path to video file, webcam ID, or 'simulated'")
    parser.add_argument('--yolo', action='store_true', help="Use YOLOv8 AI Model")
    parser.add_argument('--output', type=str, default='outputs/output_video.mp4', help="Path to save video")
    parser.add_argument('--no-reset', action='store_true', help="Do not clear database")
    args = parser.parse_args()
    run_detection(args.source, args.yolo, args.output, not args.no_reset)