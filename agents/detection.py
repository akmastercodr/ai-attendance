import cv2
import numpy as np
from agents.base import BaseAgent
from typing import List, Tuple, Any

class FaceDetectionAgent(BaseAgent):
    """
    Agent responsible for detecting faces in a video frame.
    Uses Haar Cascades by default for efficiency, but can be configured for others.
    """
    def __init__(self, name: str = "FaceDetectionAgent", config: dict = None):
        super().__init__(name, config)
        self.face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        )
        self.min_face_size = self.config.get("min_face_size", (60, 60))
        self.padding = self.config.get("padding", 20)

    def run(self, frame: np.ndarray) -> List[dict]:
        """
        Processes a frame and returns list of face data.
        Return format: [{"face_image": np.ndarray, "box": (x, y, w, h)}]
        """
        try:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = self.face_cascade.detectMultiScale(
                gray, 
                scaleFactor=1.1, 
                minNeighbors=5, 
                minSize=self.min_face_size
            )

            detected_faces = []
            for (x, y, w, h) in faces:
                # Add padding and crop
                y1 = max(0, y - self.padding)
                y2 = min(frame.shape[0], y + h + self.padding)
                x1 = max(0, x - self.padding)
                x2 = min(frame.shape[1], x + w + self.padding)
                
                face_img = frame[y1:y2, x1:x2]
                detected_faces.append({
                    "face_image": face_img,
                    "box": (x, y, w, h)
                })
            
            if detected_faces:
                self.logger.info(f"Detected {len(detected_faces)} faces.")
                
            return detected_faces
            
        except Exception as e:
            return self.handle_error(e, "detecting faces")
