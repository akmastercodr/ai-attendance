import sqlite3
import datetime
from agents.base import BaseAgent
from typing import Dict, Any

class AttendanceLoggingAgent(BaseAgent):
    """
    Agent responsible for logging attendance into SQLite.
    Implements a cooldown period to avoid redundant logs.
    """
    def __init__(self, name: str = "AttendanceLoggingAgent", config: dict = None):
        super().__init__(name, config)
        self.db_path = self.config.get("db_path", "data/attendance.sqlite")
        self.cooldown_minutes = self.config.get("cooldown_minutes", 5)
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS attendance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                person_id TEXT NOT NULL,
                timestamp DATETIME NOT NULL,
                confidence REAL,
                action TEXT DEFAULT 'ENTRY'
            )
        ''')
        
        # Migration: Add action column if it doesn't exist
        cursor.execute("PRAGMA table_info(attendance)")
        columns = [info[1] for info in cursor.fetchall()]
        if 'action' not in columns:
            cursor.execute("ALTER TABLE attendance ADD COLUMN action TEXT DEFAULT 'ENTRY'")
            
        conn.commit()
        conn.close()

    def _is_on_cooldown(self, person_id: str) -> bool:
        """Checks if the person was logged recently."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Check last entry for this person
        cooldown_time = datetime.datetime.now() - datetime.timedelta(minutes=self.cooldown_minutes)
        cursor.execute('''
            SELECT timestamp FROM attendance 
            WHERE person_id = ? AND timestamp > ? 
            ORDER BY timestamp DESC LIMIT 1
        ''', (person_id, cooldown_time))
        
        result = cursor.fetchone()
        conn.close()
        return result is not None

    def run(self, match_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Processes match result and logs if valid.
        Input: {"identity": str, "confidence": float, "action": str, ...}
        """
        try:
            person_id = match_result.get("identity")
            confidence = match_result.get("confidence", 0)
            action = match_result.get("action", "ENTRY").upper()
            
            if action not in ["ENTRY", "EXIT"]:
                action = "ENTRY"
            
            if person_id == "Unknown" or not person_id:
                return {"status": "skipped", "reason": "Unknown identity"}

            if self._is_on_cooldown(person_id):
                # self.logger.info(f"Skipping log for {person_id} (cooldown).")
                return {"status": "skipped", "reason": "Cooldown"}

            # Log to DB
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            now = datetime.datetime.now()
            cursor.execute('''
                INSERT INTO attendance (person_id, timestamp, confidence, action)
                VALUES (?, ?, ?, ?)
            ''', (person_id, now, confidence, action))
            conn.commit()
            conn.close()
            
            self.logger.info(f"Attendance logged for: {person_id}")
            return {"status": "logged", "person_id": person_id, "timestamp": str(now)}

        except Exception as e:
            return self.handle_error(e, "logging attendance")
