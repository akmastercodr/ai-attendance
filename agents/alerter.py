import time
import collections
from agents.base import BaseAgent
from typing import Dict, Any

class AlertAgent(BaseAgent):
    """
    Agent responsible for detecting suspicious behavior.
    Flags alerts if multiple unknown faces are detected in a short time.
    """
    def __init__(self, name: str = "AlertAgent", config: dict = None):
        super().__init__(name, config)
        self.threshold = self.config.get("unknown_threshold", 3)
        self.time_window = self.config.get("time_window_seconds", 60)
        self.unknown_events = collections.deque() # Stores timestamps of unknown detections

    def run(self, match_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Monitors unknown detection frequency.
        """
        try:
            person_id = match_result.get("identity")
            
            if person_id != "Unknown":
                return {"status": "ok"}

            now = time.time()
            self.unknown_events.append(now)
            
            # Remove events older than the time window
            while self.unknown_events and self.unknown_events[0] < now - self.time_window:
                self.unknown_events.popleft()
            
            count = len(self.unknown_events)
            if count >= self.threshold:
                self.logger.warning(f"SUSPICIOUS BEHAVIOR DETECTED: {count} unknown faces in {self.time_window}s!")
                # Here you could trigger a system notification, email, or sound an alarm
                return {
                    "alert": "Suspicious Behavior", 
                    "unknown_count": count, 
                    "timestamp": str(now)
                }
            
            return {"status": "monitoring", "unknown_count": count}

        except Exception as e:
            return self.handle_error(e, "monitoring alerts")
