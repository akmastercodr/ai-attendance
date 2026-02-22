import logging
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

class BaseAgent(ABC):
    """
    Base class for all agents in the Face Recognition Attendance System.
    Provides standard logging, error handling, and lifecycle methods.
    """
    def __init__(self, name: str, config: Optional[Dict[str, Any]] = None):
        self.name = name
        self.config = config or {}
        self.logger = self.get_logger()
        self.logger.info(f"Agent {self.name} initialized.")

    def get_logger(self):
        logger = logging.getLogger(self.name)
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        return logger

    @abstractmethod
    def run(self, input_data: Any) -> Any:
        """Main execution logic for the agent."""
        pass

    def handle_error(self, error: Exception, context: str = ""):
        """Standard error handling and logging."""
        self.logger.error(f"Error in {self.name} {context}: {str(error)}", exc_info=True)
        # In a real production system, this could trigger a recovery agent or alert
        return {"status": "error", "message": str(error)}
