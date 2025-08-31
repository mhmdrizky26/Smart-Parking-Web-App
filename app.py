import threading
import time
import json
import base64
from flask import Flask, render_template, Response
import cv2
import requests
import numpy as np

# =========================
# Config
# =========================
API_KEY = "qE1OUAiCA3MXNpfmaHoe"
MODEL_URL = f"https://detect.roboflow.com/dataset-trileaf-awzb0/2?api_key={API_KEY}"
THRESHOLD = 0.6
DETECT_EVERY_N_FRAMES = 5

# Ganti IP sesuai ESP32 kamu
ESP32_URL = "http://10.208.162.225/update"

# =========================
# Helper functions
# =========================
def overlap_ratio(boxA, boxB):
    xA = max(boxA[0], boxB[0])
    yA = max(boxA[1], boxB[1])
    xB = min(boxA[2], boxB[2])
    yB = min(boxA[3], boxB[3])
    if xA >= xB or yA >= yB:
        return 0.0
    interArea = (xB - xA) * (yB - yA)
    carArea = (boxB[2] - boxB[0]) * (boxB[3] - boxB[1])
    return interArea / float(carArea) if carArea > 0 else 0.0

def sort_slots(slots):
    row_threshold = 50
    return sorted(slots, key=lambda b: (b[1] // row_threshold, b[0]))

def send_to_esp32(statuses):
    """Kirim status slot ke ESP32"""
    try:
        resp = requests.post(ESP32_URL, json=statuses, timeout=2)
        print("ESP32 response:", resp.text)
    except Exception as e:
        print("Gagal kirim ke ESP32:", e)

# =========================
# Global
# =========================
output_frame = None
output_lock = threading.Lock()
current_status = {"slots": []}
status_lock = threading.Lock()

# =========================
# Camera thread
# =========================
def camera_loop(source=1):
    global output_frame, current_status
    cap = cv2.VideoCapture(source, cv2.CAP_DSHOW) 
    if not cap.isOpened():
        print("ERROR: Webcam tidak terbuka!")
        return

    frame_count = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            print("Frame tidak terbaca...")
            time.sleep(0.1)
            continue

        frame_count += 1
        annotated = frame.copy()

        slots, cars = [], []
        if frame_count % DETECT_EVERY_N_FRAMES == 0:
            _, buffer = cv2.imencode(".jpg", frame)
            img_base64 = base64.b64encode(buffer).decode()

            try:
                resp = requests.post(
                    MODEL_URL,
                    data=img_base64,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                    timeout=10
                )
                preds = resp.json()
                if "predictions" in preds:
                    for pred in preds["predictions"]:
                        x, y, w, h = pred["x"], pred["y"], pred["width"], pred["height"]
                        box = (int(x - w/2), int(y - h/2), int(x + w/2), int(y + h/2))
                        if pred["class"].lower() == "slot":
                            slots.append(box)
                        elif pred["class"].lower() == "car":
                            cars.append(box)
            except Exception as e:
                print("Deteksi error:", e)

            statuses = []
            sorted_slots = sort_slots(slots)
            for i, slot_box in enumerate(sorted_slots, start=1):
                occupied, occ_ratio = False, 0.0
                for car_box in cars:
                    ratio = overlap_ratio(slot_box, car_box)
                    if ratio >= THRESHOLD:
                        occupied, occ_ratio = True, ratio
                        break
                statuses.append({
                    "index": i,
                    "occupied": occupied,
                    "ratio": round(occ_ratio, 3),
                    "box": slot_box
                })
                # draw slot box
                x1, y1, x2, y2 = slot_box
                if occupied:
                    cv2.rectangle(annotated, (x1, y1), (x2, y2), (0,0,255), 2)
                    cv2.putText(annotated, f"Slot {i}: OCCUPIED {int(occ_ratio*100)}%",
                                (x1, y1-8), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,0,255), 2)
                else:
                    cv2.rectangle(annotated, (x1, y1), (x2, y2), (0,255,0), 2)
                    cv2.putText(annotated, f"Slot {i}: EMPTY",
                                (x1, y1-8), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,255,0), 2)

            # draw cars
            for car_box in cars:
                cx1, cy1, cx2, cy2 = car_box
                cv2.rectangle(annotated, (cx1, cy1), (cx2, cy2), (255,0,0), 2)
                cv2.putText(annotated, "Car", (cx1, cy1-8),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,0,0), 2)

            with status_lock:
                current_status = {"slots": statuses}

            # === Kirim status ke ESP32 ===
            send_to_esp32(statuses)

        with output_lock:
            output_frame = annotated

        time.sleep(0.03)

    cap.release()

# =========================
# Flask
# =========================
app = Flask(__name__)

@app.route("/")
def index():
    return render_template("index.html")

def generate_mjpeg():
    global output_frame
    while True:
        with output_lock:
            if output_frame is None:
                frame = np.zeros((480,640,3), dtype=np.uint8)
            else:
                frame = output_frame.copy()
        ret, jpg = cv2.imencode(".jpg", frame)
        if not ret:
            continue
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + jpg.tobytes() + b'\r\n')
        time.sleep(0.03)

@app.route("/video_feed")
def video_feed():
    return Response(generate_mjpeg(),
                    mimetype="multipart/x-mixed-replace; boundary=frame")

@app.route("/status")
def status():
    with status_lock:
        return json.dumps(current_status)

if __name__ == "__main__":
    cam_thread = threading.Thread(target=camera_loop, daemon=True)
    cam_thread.start()
    app.run(host="0.0.0.0", port=5000, debug=True, threaded=True)
