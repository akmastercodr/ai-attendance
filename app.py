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
from agents.reporter import ReportGenerationAgent
from dotenv import load_dotenv

load_dotenv() # Load environment variables from .env

app = Flask(__name__)
CORS(app)

# Global instances of agents and state
config = {
    "logger": {"cooldown_minutes": 1},
    "alerter": {"unknown_threshold": 3, "time_window_seconds": 30},
    "reporter": {"report_dir": "data/reports"}
}

detector = FaceDetectionAgent()
matcher = IdentityMatchingAgent()
logger_agent = AttendanceLoggingAgent(config=config["logger"])
alerter = AlertAgent(config=config["alerter"])
reporter = ReportGenerationAgent(config=config["reporter"])

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/process_frame', methods=['POST'])
def process_frame():
    try:
        data = request.json
        image_data = data.get('image') # Base64 string
        action = data.get('action', 'ENTRY')
        
        if not image_data:
            return jsonify({"error": "No image data"}), 400
            
        # Decode base64 image
        header, encoded = image_data.split(",", 1)
        binary_data = base64.b64decode(encoded)
        nparr = np.frombuffer(binary_data, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if frame is None:
            return jsonify({"error": "Failed to decode image"}), 400

        # 1. Face Detection Agent
        faces = detector.run(frame)
        
        results = []
        for face_data in faces:
            # 2. Identity Matching Agent
            match_result = matcher.run(face_data)
            match_result['action'] = action
            
            # 3. Attendance Logging Agent
            if match_result["identity"] != "Unknown":
                logger_agent.run(match_result)
            
            # 4. Alert Agent
            alerter.run(match_result)
            
            # Prepare result for frontend
            results.append({
                "identity": match_result["identity"],
                "box": match_result["box"], # [x, y, w, h]
                "confidence": float(match_result.get("confidence", 0))
            })

        return jsonify({"status": "success", "results": results})
        
    except Exception as e:
        print(f"Error processing frame: {e}")
        return jsonify({"error": str(e)}), 500

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

@app.route('/api/delete_user', methods=['DELETE'])
def delete_user():
    try:
        user_id = request.args.get('id')
        if not user_id:
            return jsonify({"error": "User ID is required"}), 400
            
        # Delete from ChromaDB
        matcher.collection.delete(ids=[user_id])
        
        return jsonify({"status": "success", "message": f"User {user_id} deleted successfully"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/send_report', methods=['POST'])
def send_report():
    try:
        data = request.json
        recipient = data.get('recipient')
        date_str = data.get('date') # Optional
        
        if not recipient:
            # Fallback to env var if not in request
            recipient = os.getenv("RECIPIENT_EMAIL")
        
        if not recipient:
            return jsonify({"error": "Recipient email is required"}), 400
            
        result = reporter.send_report_email(recipient, date_str)
        return jsonify(result)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

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
        
        if img is None:
            return jsonify({"error": "Failed to decode image"}), 400

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
        query = "SELECT person_id, timestamp, confidence, action FROM attendance ORDER BY timestamp DESC LIMIT 20"
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
