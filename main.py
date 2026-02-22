import cv2
import time
import threading
from agents.detection import FaceDetectionAgent
from agents.matcher import IdentityMatchingAgent
from agents.logger import AttendanceLoggingAgent
from agents.alerter import AlertAgent
from agents.reporter import ReportGenerationAgent

class AttendanceSystemOrchestrator:
    """
    Orchestrates the multi-agent face recognition attendance system.
    Runs an autonomous loop to monitor and process faces.
    """
    def __init__(self, config: dict = None):
        self.config = config or {}
        
        # Initialize Agents
        self.detector = FaceDetectionAgent(config=self.config.get("detector"))
        self.matcher = IdentityMatchingAgent(config=self.config.get("matcher"))
        self.logger_agent = AttendanceLoggingAgent(config=self.config.get("logger"))
        self.alerter = AlertAgent(config=self.config.get("alerter"))
        self.reporter = ReportGenerationAgent(config=self.config.get("reporter"))
        
        self.running = False
        self.last_report_time = 0
        self.report_interval = self.config.get("report_interval_seconds", 3600 * 24) # Default: Daily

    def start(self, camera_index=0):
        """Starts the autonomous loop."""
        self.running = True
        cap = cv2.VideoCapture(camera_index)
        
        print("Starting Agentic Attendance System...")
        print("Press 'q' to quit.")
        
        try:
            while self.running:
                ret, frame = cap.read()
                if not ret:
                    print("Failed to grab frame.")
                    break
                
                # 1. Face Detection Agent
                faces = self.detector.run(frame)
                
                for face_data in faces:
                    # 2. Identity Matching Agent
                    match_result = self.matcher.run(face_data)
                    
                    # 3. Attendance Logging Agent (Rule: Only if match found)
                    if match_result["identity"] != "Unknown":
                        self.logger_agent.run(match_result)
                    
                    # 4. Alert Agent (Rule: Monitor all attempts)
                    self.alerter.run(match_result)
                    
                    # Draw visual feedback on frame
                    x, y, w, h = match_result["box"]
                    color = (0, 255, 0) if match_result["identity"] != "Unknown" else (0, 0, 255)
                    cv2.rectangle(frame, (x, y), (x+w, y+h), color, 2)
                    cv2.putText(frame, match_result["identity"], (x, y-10), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.9, color, 2)

                # 5. Report Generation Agent (Rule: Daily or periodic)
                self._check_report_trigger()

                # Display the monitoring stream
                cv2.imshow('Agentic Face Recognition Attendance', frame)
                
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    self.running = False
                    
        finally:
            cap.release()
            cv2.destroyAllWindows()
            print("System stopped.")

    def _check_report_trigger(self):
        """Triggers report generation based on interval or time of day."""
        now = time.time()
        if now - self.last_report_time > self.report_interval:
            self.reporter.run()
            self.last_report_time = now

if __name__ == "__main__":
    # Custom config can be loaded from a JSON/YAML file
    config = {
        "logger": {"cooldown_minutes": 1},
        "alerter": {"unknown_threshold": 3, "time_window_seconds": 30}
    }
    
    orchestrator = AttendanceSystemOrchestrator(config=config)
    orchestrator.start()
