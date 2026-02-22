from flask import Flask, render_template, Response, jsonify, request
from flask_cors import CORS
import cv2
import sqlite3
import pandas as pd
import os
import time
from agents.detection import FaceDetectionAgent
from agents.matcher import IdentityMatchingAgent
from agents.logger import AttendanceLoggingAgent
from agents.alerter import AlertAgent

app = Flask(__name__)
CORS(app)

# Global instances of agents and state
config = {
    "logger": {"cooldown_minutes": 1},
    "alerter": {"unknown_threshold": 3, "time_window_seconds": 30}
}

detector = FaceDetectionAgent()
matcher = IdentityMatchingAgent()
logger_agent = AttendanceLoggingAgent(config=config["logger"])
alerter = AlertAgent(config=config["alerter"])

camera_on = True
camera = None

def get_camera():
    global camera
    if camera is None:
        camera = cv2.VideoCapture(0)
    return camera

def generate_frames():
    global camera_on, camera
    while True:
        if not camera_on:
            # Send a black frame or just wait
            time.sleep(0.1)
            continue
            
        cap = get_camera()
        success, frame = cap.read()
        if not success:
            break
        else:
            # 1. Face Detection Agent
            faces = detector.run(frame)
            
            for face_data in faces:
                # 2. Identity Matching Agent
                match_result = matcher.run(face_data)
                
                # 3. Attendance Logging Agent
                if match_result["identity"] != "Unknown":
                    logger_agent.run(match_result)
                
                # 4. Alert Agent
                alerter.run(match_result)
                
                # Draw visual feedback
                x, y, w, h = match_result["box"]
                color = (0, 255, 0) if match_result["identity"] != "Unknown" else (0, 0, 255)
                cv2.rectangle(frame, (x, y), (x+w, y+h), color, 2)
                cv2.putText(frame, match_result["identity"], (x, y-10), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.9, color, 2)

            ret, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/api/toggle_camera', methods=['POST'])
def toggle_camera():
    global camera_on, camera
    camera_on = not camera_on
    if not camera_on and camera is not None:
        camera.release()
        camera = None
    return jsonify({"camera_on": camera_on})

@app.route('/api/users')
def get_users():
    try:
        # Get all IDs and metadatas from ChromaDB
        results = matcher.collection.get()
        users = []
        for i in range(len(results['ids'])):
            users.append({
                "id": results['ids'][i],
                "metadata": results['metadatas'][i] if results['metadatas'] else {}
            })
        return jsonify(users)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

import numpy as np
import base64
from deepface import DeepFace

@app.route('/api/update_user', methods=['POST'])
def update_user():
    try:
        data = request.json
        user_id = data.get('id')
        new_metadata = data.get('metadata', {})
        
        if not user_id:
            return jsonify({"error": "User ID is required"}), 400
            
        # Get existing metadata to merge
        existing = matcher.collection.get(ids=[user_id])
        if not existing['ids']:
            return jsonify({"error": "User not found"}), 404
            
        current_metadata = existing['metadatas'][0] if existing['metadatas'] else {}
        current_metadata.update(new_metadata)
        
        # Update in ChromaDB
        matcher.collection.update(
            ids=[user_id],
            metadatas=[current_metadata]
        )
        
        return jsonify({"status": "success", "message": f"User {user_id} updated"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/snapshot')
def get_snapshot():
    if not camera.isOpened():
        return jsonify({"error": "Camera is not active"}), 400
    
    success, frame = camera.read()
    if not success:
        return jsonify({"error": "Failed to capture frame"}), 500
        
    ret, buffer = cv2.imencode('.jpg', frame)
    if not ret:
        return jsonify({"error": "Failed to encode frame"}), 500
        
    # Return as base64 for easy handling in JS
    img_base64 = base64.b64encode(buffer).decode('utf-8')
    return jsonify({"image": f"data:image/jpeg;base64,{img_base64}"})

@app.route('/api/register_student', methods=['POST'])
def register_student():
    try:
        data = request.json
        name = data.get('name')
        dept = data.get('department')
        image_data = data.get('image') # Base64 string
        
        if not name or not image_data:
            return jsonify({"error": "Name and image are required"}), 400
            
        # Decode base64 image
        header, encoded = image_data.split(",", 1)
        binary_data = base64.b64decode(encoded)
        nparr = np.frombuffer(binary_data, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        # Temp save for DeepFace processing
        temp_path = f"data/temp_reg_{int(time.time())}.jpg"
        cv2.imwrite(temp_path, img)
        
        # Generate embedding
        embedding_objs = DeepFace.represent(
            img_path=temp_path, 
            model_name=matcher.model_name,
            enforce_detection=True
        )
        
        if os.path.exists(temp_path):
            os.remove(temp_path) # Cleanup
        
        if not embedding_objs:
            return jsonify({"error": "No face detected. Please try again."}), 400
            
        embedding = embedding_objs[0]["embedding"]
        
        # Prepare metadata
        metadata = {
            "name": name,
            "department": dept,
            "role": "Student",
            "source": "Web Capture",
            "registration_date": str(time.time())
        }
        
        # Add to ChromaDB
        matcher.collection.add(
            embeddings=[embedding],
            ids=[name],
            metadatas=[metadata]
        )
        
        return jsonify({"status": "success", "message": f"Student {name} registered successfully!"})
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/attendance')
def get_attendance():
    try:
        conn = sqlite3.connect('data/attendance.sqlite')
        query = "SELECT person_id, timestamp, confidence FROM attendance ORDER BY timestamp DESC LIMIT 20"
        df = pd.read_sql_query(query, conn)
        conn.close()
        return jsonify(df.to_dict(orient='records'))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/stats')
def get_stats():
    try:
        conn = sqlite3.connect('data/attendance.sqlite')
        cursor = conn.cursor()
        
        # Total logs today
        cursor.execute("SELECT COUNT(*) FROM attendance WHERE date(timestamp) = date('now')")
        today_count = cursor.fetchone()[0]
        
        # Unique people today
        cursor.execute("SELECT COUNT(DISTINCT person_id) FROM attendance WHERE date(timestamp) = date('now')")
        unique_today = cursor.fetchone()[0]
        
        conn.close()
        return jsonify({
            "today_total": today_count,
            "today_unique": unique_today
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    os.makedirs('data/reports', exist_ok=True)
    app.run(host='0.0.0.0', port=5000, debug=True, threaded=True)
