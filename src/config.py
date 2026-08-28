"""Configuration for invoice processing system."""

import os
from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # LLM Configuration
    llm_provider: str = "anthropic"  # or "xai" for Grok
    llm_model: str = "claude-3-5-sonnet-20241022"
    xai_api_key: str = ""
    anthropic_api_key: str = ""

    # System Configuration
    database_path: str = "inventory.db"
    invoices_dir: str = "data/invoices"
    logs_dir: str = "logs"

    # Agent Configuration
    approval_threshold: float = 10000.0  # Invoices over $10K need extra scrutiny
    max_retries: int = 2
    timeout_seconds: int = 30

    # Feature Flags
    enable_logging: bool = True
    enable_observability: bool = True
    debug_mode: bool = False

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

    @property
    def project_root(self) -> Path:
        """Get the project root directory."""
        return Path(__file__).parent.parent.parent

    @property
    def data_dir(self) -> Path:
        """Get the data directory."""
        return self.project_root / self.invoices_dir

    @property
    def db_path(self) -> Path:
        """Get the database path."""
        return self.project_root / self.database_path

    @property
    def logs_path(self) -> Path:
        """Get the logs directory."""
        return self.project_root / self.logs_dir


# Global settings instance
settings = Settings()
