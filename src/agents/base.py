"""Base agent class for all invoice processing agents."""

import logging
from abc import ABC, abstractmethod
from typing import Any, Optional


class BaseAgent(ABC):
    """Abstract base class for all agents."""

    def __init__(self, name: str, logger: Optional[logging.Logger] = None):
        """
        Initialize the agent.

        Args:
            name: Human-readable name for the agent
            logger: Optional logger instance
        """
        self.name = name
        self.logger = logger or logging.getLogger(f"agent.{name.lower()}")

    @abstractmethod
    async def execute(self, input_data: Any) -> Any:
        """
        Execute the agent's main logic.

        Args:
            input_data: Input to process

        Returns:
            Output from the agent
        """
        pass

    def log_execution(self, message: str, level: str = "info") -> None:
        """Log agent execution."""
        log_fn = getattr(self.logger, level, self.logger.info)
        log_fn(f"[{self.name}] {message}")

    async def run(self, input_data: Any) -> Any:
        """
        Run the agent with logging.

        Args:
            input_data: Input to process

        Returns:
            Output from the agent
        """
        self.log_execution(f"Starting execution")
        try:
            result = await self.execute(input_data)
            self.log_execution(f"Completed successfully")
            return result
        except Exception as e:
            self.log_execution(f"Failed with error: {str(e)}", level="error")
            raise
