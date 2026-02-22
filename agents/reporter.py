import sqlite3
import pandas as pd
import datetime
import os
from agents.base import BaseAgent
from typing import Dict, Any

class ReportGenerationAgent(BaseAgent):
    """
    Agent responsible for generating attendance reports.
    Can be triggered manually or run on a schedule.
    """
    def __init__(self, name: str = "ReportGenerationAgent", config: dict = None):
        super().__init__(name, config)
        self.db_path = self.config.get("db_path", "data/attendance.sqlite")
        self.report_dir = self.config.get("report_dir", "data/reports")
        os.makedirs(self.report_dir, exist_ok=True)

    def run(self, date_str: str = None) -> Dict[str, Any]:
        """
        Generates a CSV report for a specific date (default: today).
        """
        try:
            if not date_str:
                date_str = datetime.datetime.now().strftime("%Y-%m-%d")
            
            conn = sqlite3.connect(self.db_path)
            query = f"""
                SELECT person_id, timestamp, confidence 
                FROM attendance 
                WHERE date(timestamp) = ?
                ORDER BY timestamp ASC
            """
            df = pd.read_sql_query(query, conn, params=(date_str,))
            conn.close()
            
            if df.empty:
                self.logger.info(f"No records found for {date_str}.")
                return {"status": "empty", "date": date_str}
            
            report_path = os.path.join(self.report_dir, f"attendance_report_{date_str}.csv")
            df.to_csv(report_path, index=False)
            
            self.logger.info(f"Report generated: {report_path}")
            return {
                "status": "success", 
                "report_path": report_path, 
                "record_count": len(df)
            }

        except Exception as e:
            return self.handle_error(e, "generating report")
